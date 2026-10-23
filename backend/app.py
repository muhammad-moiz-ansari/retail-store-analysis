"""Unified local backend entry point for camera and store operations."""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from .camera_service import REPO_ROOT, resolve_video
from .camera_service import app as camera_app
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

INTERNAL_SECRET = os.getenv("RETAILPULSE_INTERNAL_SECRET", os.getenv("POS_INTERNAL_SECRET", "local-dev-pos-secret"))


def require_internal(x_retailpulse_internal_secret: Annotated[str | None, Header()] = None) -> None:
    if x_retailpulse_internal_secret != INTERNAL_SECRET:
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


def select_dispatch_employee(conn, target_zone_id: str | None):
    return conn.execute(
        """
        SELECT users.id
        FROM users
        LEFT JOIN tasks ON tasks.employee_id = users.id AND tasks.state IN ('pending', 'delivered', 'acknowledged', 'in_progress')
        LEFT JOIN rosters ON rosters.user_id = users.id
        WHERE users.role = 'Employee' AND users.active = 1 AND tasks.id IS NULL AND coalesce(rosters.available, 1) = 1
        ORDER BY CASE WHEN rosters.zone_id = ? THEN 0 ELSE 1 END, users.name
        LIMIT 1
        """,
        (target_zone_id,),
    ).fetchone()


def create_task_for_employee(
    conn,
    employee_id: str,
    instruction: str,
    target_zone_id: str | None,
    source_zone_id: str | None,
    alert_id: str | None,
    evidence: dict,
) -> str:
    task_id = uuid.uuid4().hex
    timestamp = now_iso()
    due_at = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
    conn.execute(
        """
        INSERT INTO tasks(id, employee_id, target_zone_id, source_zone_id, instruction, state, trigger_alert_id, evidence_json, created_at, updated_at, due_at)
        VALUES (?, ?, ?, ?, ?, 'delivered', ?, ?, ?, ?, ?)
        """,
        (task_id, employee_id, target_zone_id, source_zone_id, instruction, alert_id, json.dumps(evidence), timestamp, timestamp, due_at),
    )
    conn.execute(
        "INSERT INTO task_events(id, task_id, state, note, created_at) VALUES (?, ?, 'delivered', 'Automatic dispatch', ?)",
        (uuid.uuid4().hex, task_id, timestamp),
    )
    return task_id


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


def start_job(args: list[str], read_result) -> dict[str, str]:
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

    def read_result() -> dict[str, Any]:
        people = json.loads(output.with_suffix(".people.json").read_text(encoding="utf-8"))
        return {
            "video": str(video.relative_to(REPO_ROOT)),
            "output": str(output.relative_to(REPO_ROOT)),
            "interactions": json.loads(output.with_suffix(".interactions.json").read_text(encoding="utf-8")),
            "people": people["people"],
        }

    args = ["-m", "backend.interaction.cli", str(video), "--output", str(output), "--judge", judge,
            "--every", str(every), "--track-every", str(track_every)]
    return start_job(args, read_result)


@app.post("/analyze-frame", dependencies=[Depends(require_manager)])
def analyze_frame(body: dict) -> dict[str, Any]:
    frame = body.get("image_base64")
    if not isinstance(frame, str) or not frame or len(frame) > 20_000_000:
        raise HTTPException(status_code=400, detail="image_base64 is required (max ~15 MB image)")
    aisle = str(body.get("aisle") or "aisle")[:64]
    try:
        done = subprocess.run(
            [sys.executable, "-u", str(REPO_ROOT / "backend" / "analyze_frame.py"), aisle],
            input=frame, capture_output=True, text=True, cwd=REPO_ROOT, timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Frame analysis timed out") from exc
    try:
        result = json.loads(done.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        result = {"error": done.stderr.strip().splitlines()[-1] if done.stderr.strip() else "Frame analysis failed"}
    if done.returncode != 0 or "error" in result:
        raise HTTPException(status_code=400 if done.returncode == 1 else 500, detail=result.get("error", "Frame analysis failed"))
    return result


@app.get("/jobs/{job_id}", dependencies=[Depends(require_manager)])
def job_status(job_id: str) -> dict[str, Any]:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/auth/login", dependencies=[Depends(require_internal)])
def login(body: dict) -> dict:
    email = str(body.get("email") or "").strip()
    password = str(body.get("password") or "")
    role = str(body.get("role") or "").strip() or None
    if role not in {None, "Manager", "Employee"}:
        raise HTTPException(status_code=400, detail="role must be Manager or Employee")
    with connect() as conn:
        try:
            return {"authenticated": True, "user": authenticate(conn, email, password, role)}
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from None


@app.post("/auth/invitations/accept", dependencies=[Depends(require_internal)])
def signup(body: dict) -> dict:
    token = str(body.get("token") or "").strip()
    name = str(body.get("name") or "").strip()
    password = str(body.get("password") or "")
    if not token or not name or len(password) < 6:
        raise HTTPException(status_code=400, detail="Invite token, name and a 6+ character password are required")
    with connect() as conn:
        try:
            return {"authenticated": True, "user": accept_invitation(conn, token, name, password)}
        except (sqlite3.IntegrityError, ValueError) as exc:  # type: ignore[name-defined]
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
            VALUES (?, ?, ?, ?, ?, ?, ?)
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
    assignments = ", ".join(f"{field} = ?" for field in fields)
    with connect() as conn:
        conn.execute(f"UPDATE zones SET {assignments}, updated_at = ? WHERE id = ?", (*fields.values(), now_iso(), zone_id))
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
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
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
        conn.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
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
    assignments = ", ".join(f"{field} = ?" for field in fields)
    with connect() as conn:
        conn.execute(f"UPDATE rosters SET {assignments}, updated_at = ? WHERE id = ?", (*fields.values(), now_iso(), roster_id))
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
            VALUES (?, ?, ?, ?, 1, ?, ?)
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
        conn.execute("UPDATE users SET active = ?, updated_at = ? WHERE id = ?", (1 if body["active"] else 0, now_iso(), user_id))
        conn.commit()
        return settings_snapshot(conn)


@app.get("/alerts", dependencies=[Depends(require_manager)])
def list_alerts(status: str = Query(default="all")) -> dict:
    where = "" if status == "all" else "WHERE status = ?"
    params = () if status == "all" else (status,)
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT alerts.*, users.name AS resolvedBy
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
            "UPDATE alerts SET status = 'resolved', resolved_at = ?, resolved_by = ? WHERE id = ?",
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
            rows = conn.execute("SELECT * FROM tasks WHERE employee_id = ? ORDER BY created_at DESC LIMIT 50", (user_id,)).fetchall()
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
                VALUES (?, 'Unstaffed Zones', 'high', 'No eligible employee for dispatch', ?, '/alerts', 'active', ?, ?)
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
    event_id = uuid.uuid4().hex
    timestamp = now_iso()
    event_type = str(body.get("eventType") or "manual_event")
    source = str(body.get("source") or "manager")
    zone_id = body.get("zoneId") or None
    severity = str(body.get("severity") or "medium")
    if severity not in {"high", "medium", "low"}:
        severity = "medium"
    title = str(body.get("title") or "RetailPulse orchestration event")
    evidence = body.get("evidence") or {}

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO orchestration_events(id, event_type, source, zone_id, severity, title, evidence_json, source_timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, event_type, source, zone_id, severity, title, json.dumps(evidence), body.get("sourceTimestamp") or None, timestamp),
        )
        thresholds = get_setting(conn, "thresholds") or {}
        dispatch_paused = bool(thresholds.get("dispatchPaused"))
        should_dispatch = bool(body.get("dispatch", event_type in {"unattended_customer", "unstaffed_zone", "crowding"}))
        alert_id = uuid.uuid4().hex
        context = str(body.get("context") or "The orchestrator received a sustained operational event.")
        href = str(body.get("href") or "/alerts")
        conn.execute(
            """
            INSERT INTO alerts(id, category, severity, title, context, href, status, source, evidence_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
            """,
            (
                alert_id,
                str(body.get("category") or "System"),
                severity,
                title,
                context,
                href,
                source,
                json.dumps({"eventId": event_id, **evidence}),
                timestamp,
            ),
        )

        decision = "alert_only"
        reason = "Dispatch was not requested for this event."
        task_id = None
        employee_id = None
        if dispatch_paused:
            decision = "paused"
            reason = "Automatic dispatch is paused in settings."
        elif should_dispatch:
            employee = select_dispatch_employee(conn, zone_id)
            if employee:
                employee_id = employee["id"]
                instruction = str(body.get("instruction") or "Please assist customers in the requested zone.")
                task_id = create_task_for_employee(conn, employee_id, instruction, zone_id, body.get("sourceZoneId") or None, alert_id, evidence)
                decision = "dispatched"
                reason = "Selected an available employee with no active task."
            else:
                decision = "no_eligible_employee"
                reason = "No active employee was available without an existing task."

        conn.execute(
            """
            INSERT INTO dispatch_decisions(id, event_id, alert_id, task_id, selected_employee_id, decision, reason, policy_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                event_id,
                alert_id,
                task_id,
                employee_id,
                decision,
                reason,
                json.dumps({"thresholds": thresholds, "requestedDispatch": should_dispatch}),
                timestamp,
            ),
        )
        voice_agent = None
        if body.get("voiceAgent"):
            zone_name = None
            if zone_id:
                zone = conn.execute("SELECT name FROM zones WHERE id = ?", (zone_id,)).fetchone()
                zone_name = zone["name"] if zone else None
            voice_agent = generate_voice_script(
                {
                    "eventType": event_type,
                    "title": title,
                    "severity": severity,
                    "zoneId": zone_id,
                    "zoneName": zone_name,
                    "category": body.get("category") or "System",
                    "context": context,
                    "instruction": body.get("instruction") or "Please assist customers in the requested zone.",
                    "decision": decision,
                    "evidence": evidence,
                },
                store_context(conn),
            )

        conn.commit()
        result = {"eventId": event_id, "alertId": alert_id, "taskId": task_id, "decision": decision, "reason": reason}
        if voice_agent:
            result["voiceAgent"] = voice_agent
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
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if current.get("role") == "Employee" and task["employee_id"] != current.get("user_id"):
            raise HTTPException(status_code=403, detail="Employees can only update their own tasks")
        timestamp = now_iso()
        conn.execute("UPDATE tasks SET state = ?, updated_at = ? WHERE id = ?", (state, timestamp, task_id))
        conn.execute(
            "INSERT INTO task_events(id, task_id, state, actor_id, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
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
        return {
            "ok": True,
            "workers": {"orchestrator": "idle", "cv": "not_configured", "pos": "available"},
            "activeAlerts": active_alerts,
            "activeTasks": active_tasks,
            "cameras": {"total": cameras["total"], "online": cameras["online"] or 0},
        }
