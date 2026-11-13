"""Unified local backend entry point for POS, camera and store operations."""

from __future__ import annotations

import asyncio
import json
import os
import re
from psycopg import IntegrityError
import subprocess
import sys
import time
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from .agents.dashboard_api import router as dashboard_router

from .camera_service import REPO_ROOT, resolve_video
from .camera_service import app as camera_app
from .dispatch import create_task_for_employee, handle_event, select_dispatch_employee
from .pos_service import app as pos_app
from .runtime_secrets import internal_secret, matches
from .store_core import (
    accept_invitation,
    authenticate,
    connect,
    create_invitation,
    get_setting,
    now_iso,
    row_to_dict,
    set_setting,
    settings_snapshot,
)
from .voice_agent import generate_voice_script, integration_status, synthesize_voice

app = FastAPI(title="RetailPulse Backend", version="0.1.0")
app.mount("/camera", camera_app)
app.mount("/pos", pos_app)

# Read-only analytics remain unavailable until explicit server membership/source configuration.
app.include_router(dashboard_router)

INTERNAL_SECRET = internal_secret("RETAILPULSE_INTERNAL_SECRET", "POS_INTERNAL_SECRET")


def require_internal(x_retailpulse_internal_secret: Annotated[str | None, Header()] = None) -> None:
    if not matches(x_retailpulse_internal_secret, INTERNAL_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized service request")


def actor(
    _: Annotated[None, Depends(require_internal)],
    x_retailpulse_role: Annotated[str | None, Header()] = None,
    x_retailpulse_user_id: Annotated[str | None, Header()] = None,
    x_retailpulse_email: Annotated[str | None, Header()] = None,
) -> dict[str, str | None]:
    return {"role": x_retailpulse_role, "user_id": x_retailpulse_user_id, "email": x_retailpulse_email}


def require_manager(current: Annotated[dict[str, str | None], Depends(actor)]) -> dict[str, str | None]:
    if current.get("role") != "Manager":
        raise HTTPException(status_code=403, detail="Manager role required")
    return current


def require_employee_or_manager(current: Annotated[dict[str, str | None], Depends(actor)]) -> dict[str, str | None]:
    if current.get("role") not in {"Manager", "Employee"}:
        raise HTTPException(status_code=403, detail="Authenticated role required")
    return current


def parse_json(value: str | None) -> Any:
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def store_context(conn) -> dict[str, Any]:
    active_alerts = conn.execute("SELECT count(*) AS total FROM alerts WHERE status = 'active'").fetchone()["total"]
    active_tasks = conn.execute(
        "SELECT count(*) AS total FROM tasks WHERE state IN ('pending', 'delivered', 'acknowledged', 'in_progress')"
    ).fetchone()["total"]
    zones = [row_to_dict(row) for row in conn.execute("SELECT id, name, type, capacity FROM zones ORDER BY name")]
    return {"activeAlerts": active_alerts, "activeTasks": active_tasks, "zones": zones}


OUTPUT_DIR = REPO_ROOT / "backend" / "output"
_jobs: dict[str, dict[str, Any]] = {}


def run_script(job_id: str, args: list[str], read_result) -> None:
    """Run one CV script to completion, streaming its output into the job log (polled by the page)."""
    job = _jobs[job_id]
    job["status"] = "running"
    try:
        process = subprocess.Popen(
            [sys.executable, "-u", *args],
            cwd=REPO_ROOT,
            env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONPATH": str(REPO_ROOT)},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        for line in process.stdout:
            job["logs"].append(line.rstrip())
        if process.wait() != 0:
            raise RuntimeError(job["logs"][-1] if job["logs"] else f"Exited with code {process.returncode}")
        job.update(status="completed", result=read_result())
    except Exception as exc:  # surfaced through the job API, never leaked as a traceback
        job.update(status="failed", error=str(exc))


MAX_RUNNING_JOBS, MAX_KEPT_JOBS = 2, 50  # S8


def start_job(args: list[str], read_result) -> dict[str, str]:
    if sum(job["status"] in {"queued", "running"} for job in _jobs.values()) >= MAX_RUNNING_JOBS:
        raise HTTPException(status_code=429, detail=f"{MAX_RUNNING_JOBS} CV jobs are already running; wait for one to finish")
    for old in [k for k, job in _jobs.items() if job["status"] not in {"queued", "running"}][:-MAX_KEPT_JOBS or None]:
        del _jobs[old]  # dicts keep insertion order, so this drops the oldest finished jobs
    job_id = uuid.uuid4().hex
    _jobs[job_id] = {"id": job_id, "status": "queued", "logs": [], "result": None}
    asyncio.get_running_loop().run_in_executor(None, run_script, job_id, args, read_result)
    return {"id": job_id, "status": "queued"}


def int_field(body: dict, key: str, default: int, low: int, high: int) -> int:
    try:
        value = int(body.get(key, default))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{key} must be an integer") from exc
    if not low <= value <= high:
        raise HTTPException(status_code=400, detail=f"{key} must be between {low} and {high}")
    return value


@app.post("/compare-people", dependencies=[Depends(require_manager)])
async def compare_people(body: dict) -> dict[str, str]:
    video1 = resolve_video(body.get("video1"), "video1")
    video2 = resolve_video(body.get("video2"), "video2")
    interval = int_field(body, "frame_interval", 30, 1, 10_000)
    # shortcut: the script always writes one fixed file, so concurrent comparisons overwrite each other; pass an output path if that matters.
    output = OUTPUT_DIR / "people_comparison.json"
    script = str(REPO_ROOT / "backend" / "compare_people.py")
    return start_job([script, str(video1), str(video2), str(interval)], lambda: json.loads(output.read_text(encoding="utf-8")))


@app.post("/interaction/runs", dependencies=[Depends(require_manager)])
async def start_interaction_run(body: dict) -> dict[str, str]:
    video = resolve_video(body.get("video"), "video")
    judge = body.get("judge", "pose")
    if judge not in {"pose", "off"}:
        raise HTTPException(status_code=400, detail="judge must be 'pose' or 'off'")
    every = int_field(body, "every", 1, 1, 100)
    track_every = int_field(body, "track_every", 1, 1, 100)
    output = OUTPUT_DIR / "interaction-runs" / uuid.uuid4().hex / f"{video.stem}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    args = ["-m", "backend.interaction.cli", str(video), "--output", str(output), "--judge", judge,
            "--every", str(every), "--track-every", str(track_every)] + event_args(body)
    return start_job(args, lambda: interaction_result(output, str(video.relative_to(REPO_ROOT))))


def event_args(body: dict) -> list[str]:
    """--camera for the CLI when the request names a configured camera, so the run lands in the event store."""
    camera = body.get("camera")
    if not camera:
        return []
    with connect() as conn:
        known = conn.execute("SELECT 1 FROM cameras WHERE id = %s AND zone_id IS NOT NULL", (str(camera),)).fetchone()
    if not known:
        raise HTTPException(status_code=400, detail="camera must be a configured camera with a zone")
    return ["--camera", str(camera)]


def interaction_result(output, source: str) -> dict[str, Any]:
    people = json.loads(output.with_suffix(".people.json").read_text(encoding="utf-8"))
    return {
        "video": source,
        "output": str(output.relative_to(REPO_ROOT)),
        "interactions": json.loads(output.with_suffix(".interactions.json").read_text(encoding="utf-8")),
        "people": people["people"],
    }


_live_runs: dict[str, Any] = {}  # job id -> output path of a live DroidCam run


@app.post("/interaction/live", dependencies=[Depends(require_manager)])
async def start_live_run(body: dict) -> dict[str, str]:
    """Live DroidCam feed over Wi-Fi (WSL has no webcams, but reaches the phone's stream)."""
    host = str(body.get("host") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", host):
        raise HTTPException(status_code=400, detail="host must be the phone IP or hostname shown in DroidCam")
    port = int_field(body, "port", 4747, 1, 65535)
    judge = body.get("judge", "pose")
    if judge not in {"pose", "off"}:
        raise HTTPException(status_code=400, detail="judge must be 'pose' or 'off'")
    every = int_field(body, "every", 3, 1, 100)
    resolution = body.get("resolution") or ""
    # DroidCam serves the requested size itself (/video?640x480), cutting Wi-Fi traffic and decode time.
    # It has no square sizes, so a square is the centre crop of the 4:3 size with the same height.
    streams = {"": "", "1280x720": "1280x720", "640x480": "640x480", "320x240": "320x240",
               "480x480": "640x480", "240x240": "320x240"}
    if resolution not in streams:
        raise HTTPException(status_code=400, detail=f"resolution must be one of {', '.join(sorted(r for r in streams if r))}")
    square, resolution = resolution in {"480x480", "240x240"}, streams[resolution]
    output = OUTPUT_DIR / "interaction-runs" / f"live-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}" / "live.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    source = f"http://{host}:{port}/video" + (f"?{resolution}" if resolution else "")
    args = ["-m", "backend.interaction.cli", "--live", "phone", "--phone-cam", source, "--output", str(output),
            "--judge", judge, "--every", str(every), "--track-every", "1", "--stop-file", str(output.with_suffix(".stop"))] + (["--square"] if square else []) + event_args(body)
    started = start_job(args, lambda: interaction_result(output, source))
    _live_runs[started["id"]] = output
    return started


def live_output(job_id: str):
    if job_id not in _live_runs:
        raise HTTPException(status_code=404, detail="Live run not found")
    return _live_runs[job_id]


@app.post("/interaction/live/{job_id}/stop", dependencies=[Depends(require_manager)])
def stop_live_run(job_id: str) -> dict[str, str]:
    live_output(job_id).with_suffix(".stop").touch()
    return {"id": job_id, "status": "stopping"}


@app.get("/interaction/live/{job_id}/stream", dependencies=[Depends(require_manager)])
async def live_stream(job_id: str) -> StreamingResponse:
    """MJPEG of the run's preview frames; an <img> plays it directly and it ends when the run does."""
    preview = live_output(job_id).with_suffix(".preview.jpg")

    async def frames():
        sent = None
        while _jobs[job_id]["status"] in {"queued", "running"}:
            try:
                stamp = preview.stat().st_mtime_ns
                if stamp != sent:
                    jpeg = preview.read_bytes()
                    sent = stamp
                    yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n"
            except FileNotFoundError:  # no frame yet, or replaced mid-read
                pass
            await asyncio.sleep(1 / 30)

    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame",
                             headers={"Cache-Control": "no-store"})


@app.post("/analyze-frame", dependencies=[Depends(require_manager)])
def analyze_frame(body: dict) -> dict[str, Any]:
    frame = body.get("image_base64")
    if not isinstance(frame, str) or not frame or len(frame) > 20_000_000:
        raise HTTPException(status_code=400, detail="image_base64 is required (max ~15 MB image)")
    from .analyze_frame import analyze  # lazy: ultralytics is heavy; the model then stays loaded in this process

    try:
        return analyze(frame, str(body.get("aisle") or "aisle")[:64])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/jobs/{job_id}", dependencies=[Depends(require_manager)])
def job_status(job_id: str) -> dict[str, Any]:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


MIN_PASSWORD_LENGTH = 8  # S6
LOGIN_MAX_FAILURES, LOGIN_WINDOW_S = 5, 15 * 60  # S3, per account
# shortcut: in-memory and per process; move to the database if the backend ever runs more than one worker.
_failed_logins: dict[str, list[float]] = {}


@app.post("/auth/login", dependencies=[Depends(require_internal)])
def login(body: dict) -> dict:
    email = str(body.get("email") or "").strip()
    password = str(body.get("password") or "")
    role = str(body.get("role") or "").strip() or None
    if role not in {None, "Manager", "Employee"}:
        raise HTTPException(status_code=400, detail="role must be Manager or Employee")
    key = email.lower()
    now = time.monotonic()
    recent = [t for t in _failed_logins.get(key, []) if now - t < LOGIN_WINDOW_S]
    if len(recent) >= LOGIN_MAX_FAILURES:
        raise HTTPException(status_code=429, detail="Too many failed sign-ins for this account; try again in 15 minutes")
    with connect() as conn:
        try:
            user = authenticate(conn, email, password, role)
        except ValueError as exc:
            _failed_logins[key] = recent + [now]
            raise HTTPException(status_code=401, detail=str(exc)) from None
    _failed_logins.pop(key, None)
    return {"authenticated": True, "user": user}


@app.post("/auth/invitations/accept", dependencies=[Depends(require_internal)])
def signup(body: dict) -> dict:
    token = str(body.get("token") or "").strip()
    name = str(body.get("name") or "").strip()
    password = str(body.get("password") or "")
    if not token or not name or len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail=f"Invite token, name and a {MIN_PASSWORD_LENGTH}+ character password are required")
    with connect() as conn:
        try:
            return {"authenticated": True, "user": accept_invitation(conn, token, name, password)}
        except (IntegrityError, ValueError) as exc:  # type: ignore[name-defined]
            raise HTTPException(status_code=400, detail=str(exc)) from None


@app.get("/settings", dependencies=[Depends(require_manager)])
def get_settings() -> dict:
    with connect() as conn:
        return settings_snapshot(conn)


@app.post("/settings/zones", dependencies=[Depends(require_manager)])
def add_zone(body: dict) -> dict:
    zone_id = uuid.uuid4().hex
    timestamp = now_iso()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO zones(id, name, type, capacity, min_staff, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                zone_id,
                str(body.get("name") or "").strip(),
                str(body.get("type") or "Aisle"),
                int(body.get("capacity") or 10),
                int(body.get("minStaff") or 0),
                timestamp,
                timestamp,
            ),
        )
        conn.commit()
        return settings_snapshot(conn)


@app.patch("/settings/zones/{zone_id}", dependencies=[Depends(require_manager)])
def update_zone(zone_id: str, body: dict) -> dict:
    fields: dict[str, Any] = {}
    for incoming, column in {"name": "name", "type": "type", "capacity": "capacity", "minStaff": "min_staff"}.items():
        if incoming in body:
            fields[column] = body[incoming]
    if not fields:
        raise HTTPException(status_code=400, detail="No zone fields supplied")
    assignments = ", ".join(f"{field} = %s" for field in fields)
    with connect() as conn:
        conn.execute(f"UPDATE zones SET {assignments}, updated_at = %s WHERE id = %s", (*fields.values(), now_iso(), zone_id))
        conn.commit()
        return settings_snapshot(conn)


@app.post("/settings/cameras", dependencies=[Depends(require_manager)])
def add_camera(body: dict) -> dict:
    camera_id = uuid.uuid4().hex
    timestamp = now_iso()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO cameras(id, name, zone_id, role, source_type, source_url, online, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s)
            """,
            (
                camera_id,
                str(body.get("name") or "").strip(),
                body.get("zoneId") or None,
                str(body.get("role") or "floor"),
                str(body.get("sourceType") or "recording"),
                body.get("sourceUrl") or None,
                timestamp,
                timestamp,
            ),
        )
        conn.commit()
        return settings_snapshot(conn)


@app.delete("/settings/cameras/{camera_id}", dependencies=[Depends(require_manager)])
def delete_camera(camera_id: str) -> dict:
    with connect() as conn:
        conn.execute("DELETE FROM cameras WHERE id = %s", (camera_id,))
        conn.commit()
        return settings_snapshot(conn)


@app.patch("/settings/rosters/{roster_id}", dependencies=[Depends(require_manager)])
def update_roster(roster_id: str, body: dict) -> dict:
    fields: dict[str, Any] = {}
    if "zoneId" in body:
        fields["zone_id"] = body["zoneId"] or None
    if "shift" in body:
        fields["shift"] = body["shift"]
    if "available" in body:
        fields["available"] = 1 if body["available"] else 0
    if not fields:
        raise HTTPException(status_code=400, detail="No roster fields supplied")
    assignments = ", ".join(f"{field} = %s" for field in fields)
    with connect() as conn:
        conn.execute(f"UPDATE rosters SET {assignments}, updated_at = %s WHERE id = %s", (*fields.values(), now_iso(), roster_id))
        conn.commit()
        return settings_snapshot(conn)


@app.post("/settings/rosters", dependencies=[Depends(require_manager)])
def add_roster(body: dict) -> dict:
    roster_id = uuid.uuid4().hex
    timestamp = now_iso()
    with connect() as conn:
        employee = conn.execute("SELECT id FROM users WHERE role = 'Employee' AND active = 1 ORDER BY name LIMIT 1").fetchone()
        if not employee:
            raise HTTPException(status_code=400, detail="Create an active employee account first")
        conn.execute(
            """
            INSERT INTO rosters(id, user_id, zone_id, shift, available, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 1, %s, %s)
            """,
            (roster_id, employee["id"], body.get("zoneId") or None, str(body.get("shift") or ""), timestamp, timestamp),
        )
        conn.commit()
        return settings_snapshot(conn)


@app.put("/settings/thresholds", dependencies=[Depends(require_manager)])
def update_thresholds(body: dict) -> dict:
    with connect() as conn:
        current = get_setting(conn, "thresholds") or {}
        current.update(body)
        set_setting(conn, "thresholds", current)
        return settings_snapshot(conn)


@app.put("/settings/privacy", dependencies=[Depends(require_manager)])
def update_privacy(body: dict) -> dict:
    with connect() as conn:
        current = get_setting(conn, "privacy") or {}
        current.update(body)
        set_setting(conn, "privacy", current)
        return settings_snapshot(conn)


@app.post("/accounts/invitations", dependencies=[Depends(require_manager)])
def invite_user(body: dict, current: Annotated[dict[str, str | None], Depends(actor)]) -> dict:
    email = str(body.get("email") or "").strip()
    role = str(body.get("role") or "Employee")
    if role not in {"Manager", "Employee"} or not email:
        raise HTTPException(status_code=400, detail="Valid email and role are required")
    with connect() as conn:
        invitation = create_invitation(conn, email, role, current.get("user_id"))
        snapshot = settings_snapshot(conn)
        return {"invitation": invitation, **snapshot}


@app.patch("/accounts/{user_id}", dependencies=[Depends(require_manager)])
def update_account(user_id: str, body: dict) -> dict:
    with connect() as conn:
        if "active" not in body:
            raise HTTPException(status_code=400, detail="Only active status can be updated here")
        conn.execute("UPDATE users SET active = %s, updated_at = %s WHERE id = %s", (1 if body["active"] else 0, now_iso(), user_id))
        conn.commit()
        return settings_snapshot(conn)


@app.get("/alerts", dependencies=[Depends(require_manager)])
def list_alerts(status: str = Query(default="all")) -> dict:
    where = "" if status == "all" else "WHERE status = %s"
    params = () if status == "all" else (status,)
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT alerts.*, users.name AS "resolvedBy"
            FROM alerts
            LEFT JOIN users ON users.id = alerts.resolved_by
            {where}
            ORDER BY created_at DESC
            """,
            params,
        ).fetchall()
        alerts = []
        for index, row in enumerate(rows):
            item = row_to_dict(row)
            item["evidence"] = parse_json(item.pop("evidence_json"))
            item["order"] = len(rows) - index
            alerts.append(item)
        return {"alerts": alerts}


@app.post("/alerts/{alert_id}/resolve", dependencies=[Depends(require_manager)])
def resolve_alert(alert_id: str, current: Annotated[dict[str, str | None], Depends(actor)]) -> dict:
    with connect() as conn:
        conn.execute(
            "UPDATE alerts SET status = 'resolved', resolved_at = %s, resolved_by = %s WHERE id = %s",
            (now_iso(), current.get("user_id"), alert_id),
        )
        conn.commit()
        return list_alerts("all")


@app.get("/tasks/me", dependencies=[Depends(require_employee_or_manager)])
def my_tasks(current: Annotated[dict[str, str | None], Depends(actor)]) -> dict:
    with connect() as conn:
        user_id = current.get("user_id")
        if current.get("role") == "Manager":
            rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 100").fetchall()
        else:
            rows = conn.execute("SELECT * FROM tasks WHERE employee_id = %s ORDER BY created_at DESC LIMIT 50", (user_id,)).fetchall()
        tasks = []
        for row in rows:
            item = row_to_dict(row)
            item["evidence"] = parse_json(item.pop("evidence_json"))
            tasks.append(item)
        return {"tasks": tasks}


@app.post("/tasks/dispatch", dependencies=[Depends(require_manager)])
def dispatch_task(body: dict) -> dict:
    timestamp = now_iso()
    target_zone_id = body.get("targetZoneId") or None
    with connect() as conn:
        employee = select_dispatch_employee(conn, target_zone_id)
        if not employee:
            alert_id = uuid.uuid4().hex
            conn.execute(
                """
                INSERT INTO alerts(id, category, severity, title, context, href, status, evidence_json, created_at)
                VALUES (%s, 'Unstaffed Zones', 'high', 'No eligible employee for dispatch', %s, '/alerts', 'active', %s, %s)
                """,
                (alert_id, "All on-shift employees are busy, unavailable or inactive.", json.dumps(body.get("evidence") or {}), timestamp),
            )
            conn.commit()
            raise HTTPException(status_code=409, detail="No eligible employee is available")
        instruction = str(body.get("instruction") or "Please assist customers in the requested zone.")
        create_task_for_employee(
            conn,
            employee["id"],
            instruction,
            target_zone_id,
            body.get("sourceZoneId") or None,
            body.get("alertId") or None,
            body.get("evidence") or {},
        )
        conn.commit()
        return my_tasks({"role": "Manager", "user_id": None, "email": None})


@app.post("/orchestrator/events", dependencies=[Depends(require_manager)])
def ingest_orchestration_event(body: dict) -> dict:
    with connect() as conn:
        result = handle_event(conn, body)
        if body.get("voiceAgent") and result["decision"] != "duplicate":
            zone_id = body.get("zoneId") or None
            zone = conn.execute("SELECT name FROM zones WHERE id = %s", (zone_id,)).fetchone() if zone_id else None
            result["voiceAgent"] = generate_voice_script(
                {
                    "eventType": str(body.get("eventType") or "manual_event"),
                    "title": str(body.get("title") or "RetailPulse orchestration event"),
                    "severity": body.get("severity") or "medium",
                    "zoneId": zone_id,
                    "zoneName": zone["name"] if zone else None,
                    "category": body.get("category") or "System",
                    "context": str(body.get("context") or "The orchestrator received a sustained operational event."),
                    "instruction": body.get("instruction") or "Please assist customers in the requested zone.",
                    "decision": result["decision"],
                    "evidence": body.get("evidence") or {},
                },
                store_context(conn),
            )
        conn.commit()
        return result


@app.get("/voice-agent/status", dependencies=[Depends(require_manager)])
def voice_agent_status() -> dict:
    return integration_status()


@app.post("/voice-agent/script", dependencies=[Depends(require_manager)])
def create_voice_script(body: dict) -> dict:
    with connect() as conn:
        event = body.get("event") if isinstance(body.get("event"), dict) else body
        return generate_voice_script(event, store_context(conn))


@app.post("/voice-agent/speech", dependencies=[Depends(require_manager)])
def create_voice_speech(body: dict) -> dict:
    script = str(body.get("script") or "").strip()
    if not script:
        raise HTTPException(status_code=400, detail="script is required")
    return synthesize_voice(script)


@app.post("/voice-agent/generate", dependencies=[Depends(require_manager)])
def generate_voice_agent_message(body: dict) -> dict:
    event = body.get("event") if isinstance(body.get("event"), dict) else body
    include_audio = bool(body.get("includeAudio", True))
    with connect() as conn:
        script_result = generate_voice_script(event, store_context(conn))
    audio_result = synthesize_voice(script_result["script"]) if include_audio else None
    return {"script": script_result, "audio": audio_result}


@app.post("/tasks/{task_id}/transition", dependencies=[Depends(require_employee_or_manager)])
def transition_task(task_id: str, body: dict, current: Annotated[dict[str, str | None], Depends(actor)]) -> dict:
    state = str(body.get("state") or "")
    allowed = {"acknowledged", "in_progress", "completed", "declined", "expired", "cancelled"}
    if state not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported task state")
    with connect() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if current.get("role") == "Employee" and task["employee_id"] != current.get("user_id"):
            raise HTTPException(status_code=403, detail="Employees can only update their own tasks")
        timestamp = now_iso()
        conn.execute("UPDATE tasks SET state = %s, updated_at = %s WHERE id = %s", (state, timestamp, task_id))
        if state == "acknowledged" and task["ack_seconds"] is None:
            ack = (datetime.fromisoformat(timestamp) - datetime.fromisoformat(task["created_at"])).total_seconds()
            conn.execute("UPDATE tasks SET ack_seconds = %s WHERE id = %s", (round(ack, 3), task_id))
        conn.execute(
            "INSERT INTO task_events(id, task_id, state, actor_id, note, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (uuid.uuid4().hex, task_id, state, current.get("user_id"), body.get("note") or None, timestamp),
        )
        conn.commit()
        return my_tasks(current)


@app.get("/tasks/events", dependencies=[Depends(require_employee_or_manager)])
def task_events() -> StreamingResponse:
    async def stream():
        yield "event: ready\ndata: {\"ok\": true}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/system-status", dependencies=[Depends(require_manager)])
def system_status() -> dict:
    with connect() as conn:
        active_alerts = conn.execute("SELECT count(*) AS total FROM alerts WHERE status = 'active'").fetchone()["total"]
        active_tasks = conn.execute(
            "SELECT count(*) AS total FROM tasks WHERE state IN ('pending', 'delivered', 'acknowledged', 'in_progress')"
        ).fetchone()["total"]
        cameras = conn.execute("SELECT count(*) AS total, sum(online) AS online FROM cameras").fetchone()
        ack = conn.execute(
            "SELECT count(ack_seconds) AS n, avg(ack_seconds) AS mean, percentile_cont(0.5) WITHIN GROUP (ORDER BY ack_seconds) AS median FROM tasks"
        ).fetchone()
        return {
            "acknowledgement": {"tasks": ack["n"], "meanSeconds": ack["mean"], "medianSeconds": ack["median"]},
            "ok": True,
            "workers": {"orchestrator": "idle", "cv": "not_configured", "pos": "available"},
            "activeAlerts": active_alerts,
            "activeTasks": active_tasks,
            "cameras": {"total": cameras["total"], "online": cameras["online"] or 0},
        }
