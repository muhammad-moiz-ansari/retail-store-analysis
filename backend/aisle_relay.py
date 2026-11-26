"""Aisle relay: two aisle cameras feed one watcher; an aisle with customers and no staff becomes a real dispatch.

Counts per aisle come from the live CV pipeline (backend.aisle_relay_cv: one YOLO pass per split-screen frame, the
detections split back into the two aisle feeds) or from a recorded trace.json. This module turns them into store
operations:

  AisleWatcher  counts per aisle -> "need" (customers, no employee, for need_hold_s) and "arrived" (an employee seen in
                that aisle for arrive_hold_s while it has an open request). Pure, no database.
  StoreBridge   "need" -> handle_event() (alert, dispatch decision, task for an employee, as any CV event);
                "arrived" -> the task completes and its alert resolves, with the camera named as the actor.
  RelayBase     one run in a background thread (watcher + bridge + the snapshot the page polls). Process-local, like
                the CV jobs in app.py. RelayRun replays a trace in real time; aisle_relay_cv.LiveRelayRun runs the CV.

Routes (manager only): POST /aisle-relay/start {"mode": "live" | "replay", "video"?, "stride"?, "realtime"?, "speed"?},
POST /aisle-relay/stop, GET /aisle-relay/status, GET /aisle-relay/stream (MJPEG while a live run plays),
GET /aisle-relay/video/{mp4|webm} (the run's recorded video once it has ended).
Local demo accounts: python -m backend.aisle_relay setup  (local databases only).
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACE = ROOT / "dummyoutputs" / "multirow" / "trace.json"
# Which store zone each camera half watches. Aisle 1 / Aisle 2 are z2 / z3 in the seeded store.
DEFAULT_ZONES = {"aisle-1": "z2", "aisle-2": "z3"}
ACTIVE = ("pending", "delivered", "acknowledged", "in_progress")
VIDEO_TYPES = {"webm": "video/webm", "mp4": "video/mp4"}  # webm first: VP9 plays in every current browser


def aisle_label(aisle: str) -> str:
    return aisle.replace("aisle-", "Aisle ")


# ---------------------------------------------------------------------------------------------------------------
# Watcher: counts in, signals out
# ---------------------------------------------------------------------------------------------------------------

@dataclass
class WatchPolicy:
    need_hold_s: float = 2.0  # customers with no employee in view for this long -> the aisle needs someone
    arrive_hold_s: float = 1.0  # an employee in view this long in an aisle with an open request -> they arrived


@dataclass
class _Aisle:
    uncovered_since: float | None = None
    covered_since: float | None = None
    requested: bool = False


@dataclass
class AisleWatcher:
    policy: WatchPolicy = field(default_factory=WatchPolicy)
    aisles: dict[str, _Aisle] = field(default_factory=dict)

    def observe(self, t: float, counts: dict[str, dict]) -> list[dict]:
        """counts: {aisle: {"customers": n, "employees": n}}. Returns the signals this sample raised, in order."""
        out: list[dict] = []
        for aisle, c in counts.items():
            st = self.aisles.setdefault(aisle, _Aisle())
            uncovered = c["customers"] > 0 and c["employees"] == 0
            if uncovered and st.uncovered_since is None:
                st.uncovered_since = t
                if not st.requested:
                    out.append(self._signal("observe", t, aisle, counts,
                                            f"{aisle_label(aisle)}: {c['customers']} customer(s), no employee in view"))
            elif not uncovered and st.uncovered_since is not None and not st.requested:
                out.append(self._signal("observe", t, aisle, counts, f"{aisle_label(aisle)}: covered again before the "
                                        f"{self.policy.need_hold_s:g} s hold" if c["employees"] else
                                        f"{aisle_label(aisle)}: customer left before help was needed"))
                st.uncovered_since = None
            elif not uncovered and not st.requested:
                st.uncovered_since = None
            st.covered_since = (st.covered_since if st.covered_since is not None else t) if c["employees"] else None

        for aisle, st in self.aisles.items():
            c = counts.get(aisle, {"customers": 0, "employees": 0})
            if not st.requested and st.uncovered_since is not None and t - st.uncovered_since >= self.policy.need_hold_s:
                st.requested = True
                source = self.spare_aisle(aisle, counts)
                waited = t - st.uncovered_since
                text = (f"{aisle_label(aisle)} uncovered for {waited:.1f} s with {c['customers']} customer(s); "
                        + (f"{aisle_label(source)} has {counts[source]['employees']} employee(s) and "
                           f"{counts[source]['customers']} customer(s), so one can move" if source else
                           "no other aisle shows a spare employee"))
                out.append(self._signal("need", t, aisle, counts, text, source=source, waited_s=round(waited, 2)))
            if st.requested and st.covered_since is not None and t - st.covered_since >= self.policy.arrive_hold_s:
                st.requested, st.uncovered_since = False, None
                out.append(self._signal("arrived", t, aisle, counts,
                                        f"Employee in {aisle_label(aisle)} for {self.policy.arrive_hold_s:g} s"))
        return out

    @staticmethod
    def spare_aisle(target: str, counts: dict[str, dict]) -> str | None:
        """The other aisle with the most employees beyond the one its own customers need."""
        best, best_spare = None, 0
        for aisle, c in counts.items():
            if aisle == target or not c["employees"]:
                continue
            spare = c["employees"] - (1 if c["customers"] else 0)
            if spare > best_spare:
                best, best_spare = aisle, spare
        return best

    @staticmethod
    def _signal(kind: str, t: float, aisle: str, counts: dict, text: str, **extra) -> dict:
        return {"t": round(t, 2), "kind": kind, "aisle": aisle, "text": text,
                "counts": {a: dict(c) for a, c in counts.items()}, **extra}


# ---------------------------------------------------------------------------------------------------------------
# Bridge: signals -> the store's real alerts, dispatch decisions and tasks
# ---------------------------------------------------------------------------------------------------------------

class StoreBridge:
    def __init__(self, connect: Callable[[], Any], run_id: str, zones: dict[str, str] | None = None):
        self.connect, self.run_id = connect, run_id
        self.zones = dict(zones or DEFAULT_ZONES)
        self.open: dict[str, dict] = {}  # aisle -> {"task_id", "alert_id"}
        with self.connect() as conn:
            rows = conn.execute("SELECT id, name FROM zones WHERE id = ANY(%s)", (list(self.zones.values()),)).fetchall()
        self.zone_names = {r["id"]: r["name"] for r in rows}
        missing = [z for z in self.zones.values() if z not in self.zone_names]
        if missing:
            raise LookupError(f"zones not configured in this store: {', '.join(missing)}")

    def handle(self, signal: dict) -> dict:
        if signal["kind"] == "need":
            return self.need(signal)
        if signal["kind"] == "arrived":
            return self.arrived(signal)
        return {}

    def need(self, s: dict) -> dict:
        from .dispatch import handle_event

        aisle, zone = s["aisle"], self.zones[s["aisle"]]
        source_zone = self.zones.get(s.get("source") or "")
        c = s["counts"][aisle]
        name = self.zone_names[zone]
        with self.connect() as conn:
            result = handle_event(conn, {
                "eventType": "unattended_customer", "source": "cv", "zoneId": zone, "sourceZoneId": source_zone,
                "severity": "high", "category": "Unattended Customers", "href": "/manager/aisle-relay",
                "title": f"{c['customers']} customer(s) in {name} with no staff in view",
                "context": f"The {aisle_label(aisle)} camera saw customers and no employee for {s['waited_s']:g} s.",
                "instruction": f"Go to {name}: {c['customers']} customer(s) waiting with no staff."
                               + (f" You were picked because {aisle_label(s['source'])} has staff to spare." if source_zone else ""),
                "dedupeKey": f"aisle-relay:{self.run_id}:{aisle}:{s['t']:.2f}",
                "evidence": {"relay": "aisle-relay", "runId": self.run_id, "aisle": aisle, "videoSeconds": s["t"],
                             "counts": s["counts"], "sourceAisle": s.get("source"), "zoneName": name,
                             "reason": s["text"]},
            })
            employee = None
            if result.get("selectedEmployeeId"):
                employee = conn.execute("SELECT name, email FROM users WHERE id = %s", (result["selectedEmployeeId"],)).fetchone()
            conn.commit()
        if result.get("taskId") and result["decision"] == "dispatched":
            self.open[aisle] = {"task_id": result["taskId"], "alert_id": result.get("alertId")}
        return {**result, "employeeName": employee["name"] if employee else None}

    def arrived(self, s: dict) -> dict:
        from .store_core import now_iso

        opened = self.open.pop(s["aisle"], None)
        if not opened:
            return {"decision": "no_open_task"}
        stamp = now_iso()
        with self.connect() as conn:
            row = conn.execute("SELECT state FROM tasks WHERE id = %s", (opened["task_id"],)).fetchone()
            if not row or row["state"] not in ACTIVE:
                return {"decision": "already_closed", "taskId": opened["task_id"], "state": row and row["state"]}
            conn.execute("UPDATE tasks SET state = 'completed', updated_at = %s WHERE id = %s", (stamp, opened["task_id"]))
            conn.execute("INSERT INTO task_events(id, task_id, state, note, created_at) VALUES (%s, %s, 'completed', %s, %s)",
                         (uuid.uuid4().hex, opened["task_id"], f"Camera saw an employee arrive in {aisle_label(s['aisle'])}", stamp))
            if opened.get("alert_id"):
                conn.execute("UPDATE alerts SET status = 'resolved', resolved_at = %s WHERE id = %s AND status = 'active'",
                             (stamp, opened["alert_id"]))
            conn.commit()
        return {"decision": "completed", "taskId": opened["task_id"]}


# ---------------------------------------------------------------------------------------------------------------
# Real-time replay of a CV trace
# ---------------------------------------------------------------------------------------------------------------

def load_trace(path: Path) -> dict:
    trace = json.loads(Path(path).read_text())
    if not trace.get("samples"):
        raise ValueError(f"{path} has no samples; run scripts/aisle_relay_demo.py first")
    return trace


def sample_counts(sample: dict) -> dict[str, dict]:
    return {a: {"customers": v["customers"], "employees": v["employees"]} for a, v in sample["aisles"].items()}


class RelayBase:
    """One relay run: aisle counts in (from a recorded trace or the live CV pipeline), watcher signals and store
    operations out. Runs in a background thread; snapshot() is what the manager page polls."""

    mode = "replay"

    def __init__(self, connect: Callable[[], Any] | None, zones: dict[str, str] | None = None,
                 policy: WatchPolicy | None = None, speed: float = 1.0):
        self.id = uuid.uuid4().hex[:12]
        self.zones = dict(zones or DEFAULT_ZONES)
        self.bridge = StoreBridge(connect, self.id, self.zones) if connect else None  # None: watch only, no dispatch
        self.watcher = AisleWatcher(policy or WatchPolicy())
        self.speed = speed
        self.state, self.error = "starting", None
        self.started_at: float | None = None
        self.t = 0.0
        self.counts: dict[str, dict] = {}
        self.steps: list[dict] = []
        self.job: dict | None = None  # the app's CV job entry, when the run counts against the job limit
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._guarded, name=f"aisle-relay-{self.id}", daemon=True)

    @property
    def duration(self) -> float:
        raise NotImplementedError

    def start(self) -> "RelayBase":
        self.started_at = time.time()
        self.state = "running"
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()

    @property
    def active(self) -> bool:
        return self._thread.is_alive()

    def join(self, timeout: float | None = None) -> None:
        self._thread.join(timeout)

    def _guarded(self) -> None:
        try:
            self._run()
            if self.state == "running":
                self.state = "stopped" if self._stop.is_set() else "finished"
        except Exception as exc:  # shown on the manager page
            self.state, self.error = "failed", f"{type(exc).__name__}: {exc}"
        finally:
            if self.job is not None:
                self.job.update(status="failed" if self.state == "failed" else "completed", error=self.error)

    def _run(self) -> None:
        raise NotImplementedError

    def step(self, t: float, counts: dict[str, dict]) -> list[dict]:
        self.t, self.counts = t, counts
        produced = []
        for signal in self.watcher.observe(t, counts):
            outcome = self.bridge.handle(signal) if self.bridge else {}
            produced.append({**{k: v for k, v in signal.items() if k != "counts"}, "outcome": outcome})
        self.steps.extend(produced)
        return produced

    def requested(self) -> list[str]:
        return [a for a, st in self.watcher.aisles.items() if st.requested]

    def source_info(self) -> dict:
        return {}

    def snapshot(self) -> dict:
        names = self.bridge.zone_names if self.bridge else {}
        open_tasks = self.bridge.open if self.bridge else {}
        aisles = {}
        for aisle, zone in self.zones.items():
            c = self.counts.get(aisle, {"customers": 0, "employees": 0})
            requested = self.watcher.aisles.get(aisle) and self.watcher.aisles[aisle].requested
            state = ("help_sent" if aisle in open_tasks else "waiting_for_staff" if requested else
                     "uncovered" if c["customers"] and not c["employees"] else "covered" if c["employees"] else "empty")
            aisles[aisle] = {"label": aisle_label(aisle), "zoneId": zone, "zoneName": names.get(zone), **c, "state": state}
        return {"id": self.id, "mode": self.mode, "state": self.state, "error": self.error, "t": round(self.t, 2),
                "duration": self.duration, "startedAt": self.started_at, "speed": self.speed,
                "policy": asdict(self.watcher.policy), "trace": self.source_info(), "aisles": aisles, "steps": self.steps}


class RelayRun(RelayBase):
    """Replays a recorded CV trace (scripts/aisle_relay_demo.py) in real time."""

    mode = "replay"

    def __init__(self, trace_path: Path, connect: Callable[[], Any] | None, zones: dict[str, str] | None = None,
                 speed: float = 1.0, policy: WatchPolicy | None = None):
        self.trace_path = Path(trace_path)
        self.trace = load_trace(self.trace_path)
        super().__init__(connect, zones, policy, speed)

    @property
    def duration(self) -> float:
        return float(self.trace.get("duration_s") or self.trace["samples"][-1]["t"])

    def _run(self) -> None:
        for sample in self.trace["samples"]:
            due = self.started_at + sample["t"] / self.speed
            if self._stop.wait(max(0.0, due - time.time())):
                return
            self.step(sample["t"], sample_counts(sample))

    def source_info(self) -> dict:
        return {"video": self.trace.get("video"), "models": self.trace.get("models"),
                "processingSeconds": self.trace.get("processing_s"), "split": self.trace.get("split")}

    def video_dir(self) -> Path:
        return self.trace_path.parent


# ---------------------------------------------------------------------------------------------------------------
# API (mounted by app.py)
# ---------------------------------------------------------------------------------------------------------------

def build_router(require_manager, connect_db, jobs: dict | None = None, output_dir: Path | None = None):
    """jobs: the app's CV job table; a live run takes one of its slots (job_limits.admit_job) while it analyses."""
    from fastapi import APIRouter, Depends, HTTPException
    from fastapi.responses import FileResponse, StreamingResponse

    router = APIRouter(prefix="/aisle-relay", dependencies=[Depends(require_manager)])
    lock = threading.Lock()
    current: dict[str, RelayBase | None] = {"run": None}
    out_root = Path(output_dir or ROOT / "backend" / "output") / "aisle-relay"

    def trace_path() -> Path:
        return Path(os.getenv("RETAILPULSE_AISLE_RELAY_TRACE") or DEFAULT_TRACE)

    def run_tasks(run_id: str) -> list[dict]:
        with connect_db() as conn:
            rows = conn.execute(
                """SELECT tasks.id, tasks.state, tasks.instruction, tasks.target_zone_id, tasks.source_zone_id, tasks.created_at,
                          tasks.updated_at, tasks.ack_seconds, users.name AS employee_name, users.email AS employee_email,
                          target.name AS target_zone_name, source.name AS source_zone_name
                   FROM tasks JOIN users ON users.id = tasks.employee_id
                   LEFT JOIN zones target ON target.id = tasks.target_zone_id
                   LEFT JOIN zones source ON source.id = tasks.source_zone_id
                   WHERE tasks.evidence_json::jsonb ->> 'runId' = %s ORDER BY tasks.created_at""", (run_id,)).fetchall()
        return [dict(r) for r in rows]

    def video_dir() -> Path | None:
        """Where the page's recorded video lives: the replay's trace folder, or a live run's folder once it has ended."""
        run = current["run"]
        if run is None or isinstance(run, RelayRun):
            return trace_path().parent
        return None if run.active else run.video_dir()

    def live_run(body: dict, speed: float) -> RelayBase:
        from .aisle_relay_cv import DEFAULT_VIDEO, LiveRelayRun
        from .camera_service import resolve_video

        video = resolve_video(body["video"], "video") if body.get("video") else DEFAULT_VIDEO
        if not video.is_file():
            raise HTTPException(status_code=404, detail=f"No video at {video.name}; pass a split-screen clip as video")
        stride = int(body.get("stride") or 4)
        if not 1 <= stride <= 30:
            raise HTTPException(status_code=400, detail="stride must be between 1 and 30")
        run = LiveRelayRun(video, connect_db, out_root / uuid.uuid4().hex[:12], stride=stride,
                           realtime=body.get("realtime", True) is not False, speed=speed)
        if jobs is not None:
            from .job_limits import admit_job

            admit_job(jobs)
            run.job = jobs[run.id] = {"id": run.id, "kind": "aisle-relay", "status": "running", "logs": [], "result": None}
        return run

    @router.post("/start")
    def start(body: dict | None = None) -> dict:
        body = body or {}
        mode = body.get("mode") or "live"
        if mode not in {"live", "replay"}:
            raise HTTPException(status_code=400, detail="mode must be 'live' or 'replay'")
        try:
            speed = float(body.get("speed") or 1.0)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="speed must be a number") from None
        if not 0.25 <= speed <= 8:
            raise HTTPException(status_code=400, detail="speed must be between 0.25 and 8")
        with lock:
            if current["run"] and current["run"].active:
                raise HTTPException(status_code=409, detail="A relay run is already playing; stop it first")
            try:
                run = live_run(body, speed) if mode == "live" else RelayRun(trace_path(), connect_db, speed=speed)
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail=f"No CV trace at {trace_path().name}; run the CV pass first") from None
            except (LookupError, ValueError) as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from None
            cancelled = cancel_open_relay_tasks(connect_db)
            current["run"] = run.start()
        return {"run": run.snapshot(), "tasks": [], "cancelledEarlierTasks": cancelled}

    @router.post("/stop")
    def stop() -> dict:
        run = current["run"]
        if run:
            run.stop()
        return status()

    @router.get("/status")
    def status() -> dict:
        run = current["run"]
        folder = video_dir()
        videos = [fmt for fmt in VIDEO_TYPES if folder and (folder / f"annotated.{fmt}").exists()]
        return {"run": run.snapshot() if run else None, "tasks": run_tasks(run.id) if run else [], "videos": videos}

    @router.get("/video/{fmt}")
    def video(fmt: str) -> FileResponse:
        if fmt not in VIDEO_TYPES:
            raise HTTPException(status_code=404, detail="Video format must be mp4 or webm")
        folder = video_dir()
        path = folder / f"annotated.{fmt}" if folder else None
        if not path or not path.exists():
            raise HTTPException(status_code=404, detail=f"No annotated.{fmt} for this run")
        return FileResponse(path, media_type=VIDEO_TYPES[fmt], headers={"Cache-Control": "private, no-store"})

    @router.get("/stream")
    async def stream() -> StreamingResponse:
        """MJPEG of the live run's annotated frames; an <img> plays it and it ends with the run."""
        import asyncio

        run = current["run"]
        if run is None or run.mode != "live":
            raise HTTPException(status_code=404, detail="No live relay run")

        async def frames():
            sent = None
            while True:
                jpeg, seq = run.preview, run.preview_seq
                if jpeg is not None and seq != sent:
                    sent = seq
                    yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n"
                if not run.active:
                    return
                await asyncio.sleep(1 / 30)

        return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame",
                                 headers={"Cache-Control": "no-store"})

    return router


def cancel_open_relay_tasks(connect_db) -> int:
    """A new run starts clean: open tasks from earlier relay runs are cancelled, so their employees are free again."""
    from .store_core import now_iso

    stamp = now_iso()
    with connect_db() as conn:
        rows = conn.execute("SELECT id FROM tasks WHERE state = ANY(%s) AND evidence_json::jsonb ->> 'relay' = 'aisle-relay'",
                            (list(ACTIVE),)).fetchall()
        for row in rows:
            conn.execute("UPDATE tasks SET state = 'cancelled', updated_at = %s WHERE id = %s", (stamp, row["id"]))
            conn.execute("INSERT INTO task_events(id, task_id, state, note, created_at) VALUES (%s, %s, 'cancelled', %s, %s)",
                         (uuid.uuid4().hex, row["id"], "Superseded by a new aisle relay run", stamp))
        conn.commit()
    return len(rows)


# ---------------------------------------------------------------------------------------------------------------
# Local demo setup
# ---------------------------------------------------------------------------------------------------------------

SECOND_EMPLOYEE = ("u_employee_2", "Second Employee", "employee2@retailpulse.local")


def setup_demo(conn) -> list[str]:
    """Two employees rostered in Aisle 1 (the camera sees two there, and Aisle 1 keeps one for its minimum) and a
    camera row per aisle. Local databases only; uses the seeded demo password."""
    from .store_core import DEMO_PASSWORD, hash_password, is_local_database, now_iso, seed_defaults

    if not is_local_database(conn):
        raise SystemExit("Refusing: aisle relay demo accounts are for a local database only.")
    seed_defaults(conn)
    stamp = now_iso()
    user_id, name, email = SECOND_EMPLOYEE
    conn.execute("""INSERT INTO users(id, name, email, role, password_hash, active, created_at, updated_at)
                    VALUES (%s, %s, %s, 'Employee', %s, 1, %s, %s) ON CONFLICT DO NOTHING""",
                 (user_id, name, email, hash_password(DEMO_PASSWORD), stamp, stamp))
    conn.execute("""INSERT INTO rosters(id, user_id, zone_id, shift, available, created_at, updated_at)
                    VALUES ('r_employee_2', %s, 'z2', '9 AM - 1 PM', 1, %s, %s) ON CONFLICT DO NOTHING""", (user_id, stamp, stamp))
    conn.execute("""INSERT INTO cameras(id, name, zone_id, role, online, created_at, updated_at)
                    VALUES ('c4', 'CAM 04 - AISLE 2', 'z3', 'floor', 1, %s, %s) ON CONFLICT DO NOTHING""", (stamp, stamp))
    conn.commit()
    return ["manager@retailpulse.local", "employee@retailpulse.local", email]


def main() -> None:
    import argparse

    from .database import connect, initialize
    from .store_core import DEMO_PASSWORD

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="create the schema, demo accounts, roster and cameras (local database only)")
    rp = sub.add_parser("replay", help="replay a trace into the store from the command line, no web page needed\n"
                        "(the live CV pass is python -m backend.aisle_relay_cv)")
    rp.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    rp.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args()
    if a.cmd == "setup":
        with connect() as conn:
            initialize(conn)
            accounts = setup_demo(conn)
        print("Aisle relay demo ready. Sign in with password", DEMO_PASSWORD, "as:", ", ".join(accounts))
        return
    cancel_open_relay_tasks(connect)
    run = RelayRun(a.trace, connect, speed=a.speed).start()
    seen = 0
    while run.active:
        time.sleep(0.2)
        for s in run.steps[seen:]:
            o = s.get("outcome") or {}
            extra = f"  -> {o.get('decision')}" + (f": {o.get('reason')}" if o.get("reason") else "")
            print(f"{s['t']:6.2f}s {s['kind']:8} {s['text']}{extra if o else ''}", flush=True)
        seen = len(run.steps)
    print("run", run.state, run.error or "")


if __name__ == "__main__":
    main()
