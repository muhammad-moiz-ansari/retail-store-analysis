"""Aisle relay: watcher rules, the bridge into real dispatch, source-aisle ranking, the replay, the live split-feed CV run
(with a stand-in detector, so no YOLO weights are needed), the task stream and access."""

import json
import shutil
import time

import cv2
import numpy as np

import pytest
from fastapi.testclient import TestClient

from backend import app as app_module
from backend import aisle_relay_cv
from backend.aisle_relay import AisleWatcher, RelayRun, StoreBridge, WatchPolicy, setup_demo
from backend.aisle_relay_cv import LiveRelayRun, find_split, split_people
from backend.database import connect
from backend.dispatch import handle_event
from backend.store_core import now_iso, seed_defaults

INTERNAL = {"x-retailpulse-internal-secret": app_module.INTERNAL_SECRET}
MANAGER = {**INTERNAL, "x-retailpulse-role": "Manager", "x-retailpulse-user-id": "u_manager"}
EMPLOYEE = {**INTERNAL, "x-retailpulse-role": "Employee", "x-retailpulse-user-id": "u_employee"}


def counts(c1, e1, c2, e2):
    return {"aisle-1": {"customers": c1, "employees": e1}, "aisle-2": {"customers": c2, "employees": e2}}


def feed(watcher, timeline, step=0.5):
    """timeline: [(seconds, counts)]; each counts holds for its seconds, sampled every `step`."""
    out, t = [], 0.0
    for seconds, c in timeline:
        end = t + seconds
        while t < end - 1e-9:
            out += watcher.observe(t, c)
            t += step
    return out


def test_need_waits_for_the_hold_and_names_the_spare_aisle():
    signals = feed(AisleWatcher(WatchPolicy(need_hold_s=2.0)), [(3, counts(1, 2, 1, 0))])
    need = [s for s in signals if s["kind"] == "need"]
    assert len(need) == 1 and need[0]["aisle"] == "aisle-2" and need[0]["source"] == "aisle-1"
    assert need[0]["t"] == 2.0 and need[0]["waited_s"] == 2.0


def test_covered_before_the_hold_is_not_a_need():
    signals = feed(AisleWatcher(), [(1.5, counts(0, 1, 1, 0)), (2, counts(0, 1, 1, 1))])
    assert [s["kind"] for s in signals] == ["observe", "observe"]


def test_no_spare_when_the_only_employee_has_customers():
    need = [s for s in feed(AisleWatcher(), [(3, counts(1, 1, 1, 0))]) if s["kind"] == "need"]
    assert need[0]["source"] is None


def test_arrival_closes_the_request_once():
    w = AisleWatcher(WatchPolicy(need_hold_s=1.0, arrive_hold_s=1.0))
    signals = feed(w, [(2, counts(0, 2, 1, 0)), (3, counts(0, 1, 1, 1)), (3, counts(1, 1, 0, 0))])
    kinds = [s["kind"] for s in signals if s["kind"] != "observe"]
    assert kinds == ["need", "arrived"]


@pytest.fixture
def store(postgres_connection, postgres_dsn, monkeypatch):
    seed_defaults(postgres_connection)
    postgres_connection.commit()
    monkeypatch.setenv("DATABASE_URL", postgres_dsn)
    return postgres_connection


def add_employee(conn, user_id, name, zone):
    ts = now_iso()
    conn.execute("INSERT INTO users(id, name, email, role, password_hash, active, created_at, updated_at) VALUES (%s, %s, %s, 'Employee', 'x', 1, %s, %s)",
                 (user_id, name, f"{user_id}@test", ts, ts))
    conn.execute("INSERT INTO rosters(id, user_id, zone_id, shift, available, created_at, updated_at) VALUES (%s, %s, %s, 'all day', 1, %s, %s)",
                 (f"r_{user_id}", user_id, zone, ts, ts))
    conn.commit()


def test_source_zone_ranks_ahead_of_floaters(store):
    add_employee(store, "u_second", "Second", "z2")
    add_employee(store, "u_floater", "Floater", None)
    plain = handle_event(store, {"eventType": "unattended_customer", "zoneId": "z3", "dedupeKey": "a"})
    assert plain["selectedEmployeeId"] == "u_floater"  # no camera hint: floaters first, as before
    store.execute("UPDATE tasks SET state = 'completed'")
    hinted = handle_event(store, {"eventType": "unattended_customer", "zoneId": "z4", "sourceZoneId": "z2", "dedupeKey": "b"})
    assert hinted["selectedEmployeeId"] in {"u_employee", "u_second"}
    assert "cameras see spare staff" in hinted["reason"]


def test_bridge_dispatches_then_completes_on_arrival(store, postgres_dsn):
    setup_demo(store)
    bridge = StoreBridge(lambda: connect(postgres_dsn), "run1")
    w = AisleWatcher()
    outcomes = [bridge.handle(s) for s in feed(w, [(3, counts(1, 2, 1, 0)), (2, counts(0, 1, 1, 1))])]
    need, done = [o for o in outcomes if o.get("decision") == "dispatched"], [o for o in outcomes if o.get("decision") == "completed"]
    assert len(need) == 1 and len(done) == 1 and need[0]["taskId"] == done[0]["taskId"]
    task = store.execute("SELECT * FROM tasks WHERE id = %s", (need[0]["taskId"],)).fetchone()
    assert (task["target_zone_id"], task["source_zone_id"], task["state"]) == ("z3", "z2", "completed")
    assert json.loads(task["evidence_json"])["runId"] == "run1"
    assert store.execute("SELECT status FROM alerts WHERE id = %s", (need[0]["alertId"],)).fetchone()["status"] == "resolved"
    assert need[0]["employeeName"] in {"Demo Employee", "Second Employee"}


def test_bridge_refuses_unknown_zones(store, postgres_dsn):
    with pytest.raises(LookupError):
        StoreBridge(lambda: connect(postgres_dsn), "run1", {"aisle-1": "z2", "aisle-2": "nope"})


def test_replay_runs_a_trace_into_the_store(store, postgres_dsn, tmp_path):
    setup_demo(store)
    samples = [{"t": i * 0.25, "aisles": counts(1, 2, 1, 0) if i < 12 else counts(0, 1, 1, 1)} for i in range(24)]
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps({"duration_s": 6, "samples": samples}))
    run = RelayRun(trace, lambda: connect(postgres_dsn), speed=8).start()
    for _ in range(100):
        if run.state != "running":
            break
        time.sleep(0.05)
    snap = run.snapshot()
    assert snap["state"] == "finished", snap["error"]
    assert [s["kind"] for s in snap["steps"] if s["kind"] != "observe"] == ["need", "arrived"]
    assert snap["steps"][-1]["outcome"]["decision"] == "completed"


def test_task_stream_fingerprint_is_per_employee(store):
    from backend.app import task_fingerprint

    me, other = {"role": "Employee", "user_id": "u_employee"}, {"role": "Employee", "user_id": "u_someone"}
    before = task_fingerprint(store, me), task_fingerprint(store, other)
    handle_event(store, {"eventType": "unattended_customer", "zoneId": "z2"})
    store.commit()
    assert task_fingerprint(store, me) != before[0]
    assert task_fingerprint(store, other) == before[1]


def test_relay_routes_are_manager_only(store, tmp_path, monkeypatch):
    monkeypatch.setenv("RETAILPULSE_AISLE_RELAY_TRACE", str(tmp_path / "missing.json"))
    client = TestClient(app_module.app)
    assert client.get("/aisle-relay/status", headers=EMPLOYEE).status_code == 403
    status = client.get("/aisle-relay/status", headers=MANAGER).json()
    assert status["run"] is None and status["videos"] == []
    assert client.post("/aisle-relay/start", headers=MANAGER, json={"mode": "replay"}).status_code == 404  # no CV trace yet
    assert client.post("/aisle-relay/start", headers=MANAGER, json={"mode": "nope"}).status_code == 400
    assert client.get("/aisle-relay/video/webm", headers=EMPLOYEE).status_code == 403
    assert client.get("/aisle-relay/video/avi", headers=MANAGER).status_code == 404
    (tmp_path / "annotated.webm").write_bytes(b"\x1aE\xdf\xa3")
    assert client.get("/aisle-relay/status", headers=MANAGER).json()["videos"] == ["webm"]
    served = client.get("/aisle-relay/video/webm", headers=MANAGER)
    assert served.status_code == 200 and served.headers["content-type"] == "video/webm"


# ---------------------------------------------------------------------------------------------------------------
# Live split-feed CV
# ---------------------------------------------------------------------------------------------------------------

W, H, GUTTER = 320, 120, (150, 170)


def split_clip(path, seconds=6, fps=10):
    """A side-by-side clip: two dark feeds with a white gutter between them."""
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    for _ in range(seconds * fps):
        frame = np.full((H, W, 3), 40, np.uint8)
        frame[:, GUTTER[0]:GUTTER[1]] = 255
        out.write(frame)
    out.release()
    return path


def person(track, x, role):
    return {"track": track, "box": [x, 20, x + 30, 110], "conf": 0.9, "role": role, "score": 0.5, "yolo_role": None}


class StandIn:
    """One call per whole frame, like the YOLO pass: Aisle 1 has two employees throughout; Aisle 2 has a customer
    alone until 3 s, when an employee walks in. Records each call so the test can check one pass per frame."""

    description = {"person_tracker": "stand-in"}

    def __init__(self, split=None):
        self.split, self.calls = split, []

    def __call__(self, frame, t):
        self.calls.append((frame.shape, t))
        people = [person(1, 10, "employee"), person(2, 80, "employee"), person(3, 200, "customer"),
                  person(9, 145, "customer")]  # 9 sits over the gutter: in neither feed
        return people + ([person(4, 260, "employee")] if t >= 3 else [])


def test_find_split_locates_the_gutter_and_falls_back_to_halves():
    frame = np.full((H, W, 3), 40, np.uint8)
    frame[:, GUTTER[0]:GUTTER[1]] = 255
    assert find_split(frame) == {"gutter": [150, 170], "crops": {"aisle-1": [0, 150], "aisle-2": [170, 320]}}
    assert find_split(np.zeros((H, W, 3), np.uint8))["crops"] == {"aisle-1": [0, 160], "aisle-2": [160, 320]}


def test_split_people_assigns_by_box_centre_and_drops_the_gutter():
    crops = {"aisle-1": [0, 150], "aisle-2": [170, 320]}
    feeds = split_people([person(1, 10, "employee"), person(3, 200, "customer"), person(9, 145, "customer"),
                          person(5, 125, "customer")], crops)
    assert (feeds["aisle-1"]["employees"], feeds["aisle-1"]["customers"]) == (1, 1)
    assert (feeds["aisle-2"]["employees"], feeds["aisle-2"]["customers"]) == (0, 1)
    assert [p["id"] for p in feeds["aisle-2"]["people"]] == ["2-3"]
    assert feeds["aisle-1"]["people"][1]["box"][2] == 150  # clipped to its own half


def test_live_run_watches_without_a_database(tmp_path):
    detector = StandIn()
    run = LiveRelayRun(split_clip(tmp_path / "clip.mp4"), None, tmp_path / "out", stride=2, realtime=False,
                       detector=lambda split: detector).start()
    run.join(30)
    assert run.state == "finished", run.error
    assert all(shape == (H, W, 3) for shape, _ in detector.calls)  # the whole frame, once per sample
    assert len(detector.calls) == len(run.samples) == 30
    assert [s["kind"] for s in run.steps if s["kind"] != "observe"] == ["need", "arrived"]
    need = next(s for s in run.steps if s["kind"] == "need")
    assert (need["aisle"], need["source"], need["outcome"]) == ("aisle-2", "aisle-1", {})
    trace = json.loads((tmp_path / "out" / "trace.json").read_text())
    assert trace["split"]["gutter"] == [150, 170] and len(trace["samples"]) == 30
    assert {"1-1", "1-2", "2-3", "2-4"} == set(trace["tracks"])
    assert run.video_path and run.video_path.exists() and run.preview


def test_live_run_dispatches_into_the_store(store, postgres_dsn, tmp_path):
    setup_demo(store)
    run = LiveRelayRun(split_clip(tmp_path / "clip.mp4"), lambda: connect(postgres_dsn), tmp_path / "out", stride=2,
                       realtime=False, write_video=False, detector=StandIn).start()
    run.join(30)
    assert run.state == "finished", run.error
    outcomes = [s["outcome"] for s in run.steps if s["kind"] != "observe"]
    assert [o["decision"] for o in outcomes] == ["dispatched", "completed"]
    task = store.execute("SELECT * FROM tasks WHERE id = %s", (outcomes[0]["taskId"],)).fetchone()
    assert (task["target_zone_id"], task["source_zone_id"], task["state"]) == ("z3", "z2", "completed")


def test_realtime_run_drops_frames_it_cannot_keep_up_with(tmp_path):
    class Slow(StandIn):
        def __call__(self, frame, t):
            time.sleep(0.25)
            return super().__call__(frame, t)

    run = LiveRelayRun(split_clip(tmp_path / "clip.mp4", seconds=3), None, tmp_path / "out", stride=1, realtime=True,
                       speed=4, write_video=False, detector=Slow).start()
    run.join(30)
    assert run.state == "finished", run.error
    assert run.dropped > 0 and len(run.samples) + run.dropped <= 30


def test_live_route_starts_streams_and_counts_as_a_cv_job(store, tmp_path, monkeypatch):
    setup_demo(store)
    monkeypatch.setattr(aisle_relay_cv, "SplitFeedDetector", StandIn)
    clip = split_clip(app_module.REPO_ROOT / "backend" / "output" / f"relay-test-{time.time_ns()}.mp4")
    try:
        client = TestClient(app_module.app)
        started = client.post("/aisle-relay/start", headers=MANAGER,
                              json={"mode": "live", "video": str(clip.relative_to(app_module.REPO_ROOT)), "realtime": False})
        assert started.status_code == 200, started.text
        run_id = started.json()["run"]["id"]
        assert app_module._jobs[run_id]["kind"] == "aisle-relay"
        for _ in range(200):
            status = client.get("/aisle-relay/status", headers=MANAGER).json()
            if status["run"]["state"] not in {"starting", "loading models", "running"}:
                break
            time.sleep(0.05)
        assert status["run"]["state"] == "finished", status["run"]["error"]
        assert status["run"]["mode"] == "live" and [t["state"] for t in status["tasks"]] == ["completed"]
        assert app_module._jobs[run_id]["status"] == "completed"
        assert status["videos"] and client.get(f"/aisle-relay/video/{status['videos'][0]}", headers=MANAGER).status_code == 200
        assert client.get("/aisle-relay/stream", headers=EMPLOYEE).status_code == 403
        assert client.post("/aisle-relay/start", headers=MANAGER, json={"video": "../etc/passwd.mp4"}).status_code == 400
    finally:
        clip.unlink(missing_ok=True)
        if "run_id" in locals():
            shutil.rmtree(app_module.OUTPUT_DIR / "aisle-relay" / run_id, ignore_errors=True)
