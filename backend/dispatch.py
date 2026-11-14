"""Direct aisle dispatch: pick an eligible employee for an operational event and send the task.

No manager approval step. Used by the manager endpoints in app.py, by CV runs (each unattended episode
becomes an event, dispatch_unattended) and by Moiz's OperationalDispatchAdapter (make_dispatch_handler).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from .store_core import get_setting, now_iso

ACTIVE_TASK_STATES = ("pending", "delivered", "acknowledged", "in_progress")
AUTO_DISPATCH_EVENTS = {"unattended_customer", "unstaffed_zone", "crowding"}
DEFAULT_INSTRUCTION = "Please assist customers in the requested zone."
STORE_ID = os.getenv("RETAILPULSE_STORE_ID", "store-1")  # the one store this backend serves (event store default)


class IdempotencyConflict(ValueError):
    """The same idempotency key arrived with a different event: reconcile, never dispatch twice."""


def select_dispatch_employee(conn, target_zone_id: str | None):
    """First eligible employee: active, rostered and available, no open task, and taking them does not drop
    their own rostered zone below its min_staff (unless that zone is the target). Ranked: staff of the target zone, then
    floaters, then the zone with the most spare staff above its minimum. Adjacency and "mid-interaction" are not inputs yet:
    there is no store map (MAP-2) and no link from CV tracks to employee accounts.
    shortcut: the roster's shift text ('9 AM - 1 PM') is not checked against the clock; parse it once shifts are structured."""
    return conn.execute(
        """
        WITH busy AS (SELECT DISTINCT employee_id FROM tasks WHERE state = ANY(%(active)s)),
        free AS (
          SELECT users.id, users.name, rosters.zone_id
          FROM users JOIN rosters ON rosters.user_id = users.id
          WHERE users.role = 'Employee' AND users.active = 1 AND rosters.available = 1
            AND users.id NOT IN (SELECT employee_id FROM busy)
        ),
        free_per_zone AS (SELECT zone_id, count(DISTINCT id) AS n FROM free GROUP BY zone_id)
        SELECT free.id, free.name, free.zone_id, free_per_zone.n - coalesce(zones.min_staff, 0) AS spare
        FROM free
        LEFT JOIN zones ON zones.id = free.zone_id
        LEFT JOIN free_per_zone ON free_per_zone.zone_id = free.zone_id
        WHERE free.zone_id IS NULL OR free.zone_id = %(zone)s OR free_per_zone.n > coalesce(zones.min_staff, 0)
        ORDER BY CASE WHEN free.zone_id = %(zone)s THEN 0 WHEN free.zone_id IS NULL THEN 1 ELSE 2 END,
                 free_per_zone.n - coalesce(zones.min_staff, 0) DESC, free.name
        LIMIT 1
        """,
        {"active": list(ACTIVE_TASK_STATES), "zone": target_zone_id},
    ).fetchone()


def choice_reason(employee, target_zone_id: str | None) -> str:
    """One line for the manager and the decision log."""
    if employee["zone_id"] == target_zone_id:
        return f"{employee['name']}: rostered in this zone, free and available."
    if employee["zone_id"] is None:
        return f"{employee['name']}: free floater with no rostered zone."
    return f"{employee['name']}: free; zone {employee['zone_id']} keeps {employee['spare'] - 1} above its minimum staff."


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
        VALUES (%s, %s, %s, %s, %s, 'delivered', %s, %s, %s, %s, %s)
        """,
        (task_id, employee_id, target_zone_id, source_zone_id, instruction, alert_id, json.dumps(evidence), timestamp, timestamp, due_at),
    )
    conn.execute(
        "INSERT INTO task_events(id, task_id, state, note, created_at) VALUES (%s, %s, 'delivered', 'Automatic dispatch', %s)",
        (uuid.uuid4().hex, task_id, timestamp),
    )
    return task_id


def handle_event(conn, body: dict) -> dict:
    """Record one orchestration event and its dispatch decision. The caller commits.

    Repeats never make a second task. An event whose dedupeKey was already stored returns the earlier result
    (decision 'duplicate'); the insert is atomic, so concurrent repeats are safe. A known key with a different
    eventId raises IdempotencyConflict. While a task for the zone is still open the event is 'already_assigned'."""
    dedupe_key = body.get("dedupeKey") or None
    event_id = str(body.get("eventId") or uuid.uuid4().hex)
    timestamp = now_iso()
    event_type = str(body.get("eventType") or "manual_event")
    zone_id = body.get("zoneId") or None
    severity = str(body.get("severity") or "medium")
    if severity not in {"high", "medium", "low"}:
        severity = "medium"
    title = str(body.get("title") or "RetailPulse orchestration event")
    evidence = body.get("evidence") or {}
    inserted = conn.execute(
        """
        INSERT INTO orchestration_events(id, event_type, source, zone_id, severity, title, evidence_json, source_timestamp, created_at, dedupe_key)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (dedupe_key) DO NOTHING RETURNING id
        """,
        (event_id, event_type, str(body.get("source") or "manager"), zone_id, severity, title, json.dumps(evidence),
         body.get("sourceTimestamp") or None, timestamp, dedupe_key),
    ).fetchone()
    if not inserted:
        seen = conn.execute(
            """
            SELECT e.id AS event_id, d.alert_id, d.task_id, d.selected_employee_id, d.decision FROM orchestration_events e
            LEFT JOIN dispatch_decisions d ON d.event_id = e.id WHERE e.dedupe_key = %s
            """,
            (dedupe_key,),
        ).fetchone()
        if body.get("eventId") and seen["event_id"] != event_id:
            raise IdempotencyConflict(f"key {dedupe_key} belongs to event {seen['event_id']}, not {event_id}")
        return {"eventId": seen["event_id"], "alertId": seen["alert_id"], "taskId": seen["task_id"],
                "selectedEmployeeId": seen["selected_employee_id"], "decision": "duplicate",
                "reason": f"Event {dedupe_key} was already handled ({seen['decision']})."}

    thresholds = get_setting(conn, "thresholds") or {}
    should_dispatch = bool(body.get("dispatch", event_type in AUTO_DISPATCH_EVENTS))
    open_task = zone_id and conn.execute(
        "SELECT id, employee_id FROM tasks WHERE target_zone_id = %s AND state = ANY(%s) LIMIT 1",
        (zone_id, list(ACTIVE_TASK_STATES)),
    ).fetchone()

    alert_id = task_id = employee_id = None
    if should_dispatch and open_task:
        task_id, employee_id = open_task["id"], open_task["employee_id"]
        decision, reason = "already_assigned", "An employee already has an open task for this zone."
    else:
        alert_id = uuid.uuid4().hex
        conn.execute(
            """
            INSERT INTO alerts(id, category, severity, title, context, href, status, source, evidence_json, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'active', %s, %s, %s)
            """,
            (alert_id, str(body.get("category") or "System"), severity, title,
             str(body.get("context") or "The orchestrator received a sustained operational event."), str(body.get("href") or "/alerts"),
             str(body.get("source") or "manager"), json.dumps({"eventId": event_id, **evidence}), timestamp),
        )
        if thresholds.get("dispatchPaused"):
            decision, reason = "paused", "Automatic dispatch is paused in settings."
        elif not should_dispatch:
            decision, reason = "alert_only", "Dispatch was not requested for this event."
        elif employee := select_dispatch_employee(conn, zone_id):
            employee_id = employee["id"]
            task_id = create_task_for_employee(conn, employee_id, str(body.get("instruction") or DEFAULT_INSTRUCTION), zone_id,
                                               body.get("sourceZoneId") or None, alert_id, evidence)
            decision, reason = "dispatched", choice_reason(employee, zone_id)
        else:
            decision, reason = "no_eligible_employee", "No rostered, available employee could be sent without breaking zone minimum staffing."

    conn.execute(
        """
        INSERT INTO dispatch_decisions(id, event_id, alert_id, task_id, selected_employee_id, decision, reason, policy_json, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (uuid.uuid4().hex, event_id, alert_id, task_id if decision == "dispatched" else None,
         employee_id if decision == "dispatched" else None, decision, reason,
         json.dumps({"thresholds": thresholds, "requestedDispatch": should_dispatch}), timestamp),
    )
    return {"eventId": event_id, "alertId": alert_id, "taskId": task_id, "selectedEmployeeId": employee_id,
            "decision": decision, "reason": reason}


def dispatch_unattended(store, events, run_id: str) -> list[dict]:
    """Send every unattended episode of a CV run to dispatch, oldest first. Idempotent: the episode's event_id is the key."""
    zone_names = {row["id"]: row["name"] for row in store.execute("SELECT id, name FROM zones")}
    results = []
    for ep in events.execute("SELECT * FROM unattended_episodes WHERE run_id = %s ORDER BY ts_start", (run_id,)).fetchall():
        zone_id = ep["zone_id"] if ep["zone_id"] in zone_names else None
        minutes, seconds = divmod(round(ep["waited_s"]), 60)
        results.append(handle_event(store, {
            "eventType": "unattended_customer",
            "source": "cv",
            "zoneId": zone_id,
            "severity": "high",
            "category": "Unattended Customers",
            "title": f"Customer waited {minutes}m {seconds:02d}s unattended at {zone_names.get(zone_id, ep['camera_id'])}",
            "context": "A customer waited past the unattended threshold without a staff interaction.",
            "href": "/customer-info",
            "sourceTimestamp": str(ep["ts_start"]),
            "dedupeKey": ep["event_id"],
            "evidence": {"episodeId": ep["event_id"], "runId": run_id, "cameraId": ep["camera_id"], "customerTrackId": ep["customer_track_id"],
                         "waitedS": ep["waited_s"], "helped": bool(ep["helped"]), "tsStart": str(ep["ts_start"]), "tsEnd": str(ep["ts_end"])},
        }))
    return results


# Moiz's adapter decisions: the zone's open task covers a repeat; paused / alert-only mean no dispatch was possible.
_ADAPTER_DECISION = {"dispatched": "dispatched", "no_eligible_employee": "no_eligible_employee", "duplicate": "duplicate",
                     "already_assigned": "duplicate", "paused": "unavailable", "alert_only": "unavailable"}


def make_dispatch_handler(dsn: str | None = None):
    """The trusted DispatchHandler for backend.agents.operational.OperationalDispatchAdapter (S-OPERATIONS-INTEGRATION).
    Binds the event to this store and its configured zones, dispatches in one transaction, echoes the event identity."""
    from .agents.operational import DispatchOutcome
    from .database import connect

    def handler(*, event, scope) -> DispatchOutcome:
        if event.store_id != STORE_ID or scope.store_id != STORE_ID:
            raise PermissionError(f"event store {event.store_id!r} is not this backend's store {STORE_ID!r}")
        with connect(dsn) as conn:
            if not conn.execute("SELECT 1 FROM zones WHERE id = %s", (event.zone_id,)).fetchone():
                raise PermissionError(f"zone {event.zone_id!r} is not configured")
            result = handle_event(conn, {
                "eventId": event.event_id, "dedupeKey": event.idempotency_key, "eventType": event.event_type,
                "source": event.source, "zoneId": event.zone_id, "severity": event.severity,
                "sourceTimestamp": event.source_timestamp.isoformat(),
                "category": "Unattended Customers" if event.event_type == "unattended_customer" else "Unstaffed Zones",
                "title": f"{event.event_type.replace('_', ' ').capitalize()} in {event.zone_id}",
                "evidence": event.evidence.model_dump(mode="json", by_alias=True),
            })
            conn.commit()
        decision = _ADAPTER_DECISION[result["decision"]]
        assigned = decision in ("dispatched", "duplicate") and result["taskId"] is not None
        return DispatchOutcome(eventId=event.event_id, idempotencyKey=event.idempotency_key, storeId=event.store_id,
                               zoneId=event.zone_id, decision=decision, alertId=result["alertId"],
                               taskId=result["taskId"] if assigned else None,
                               selectedEmployeeId=result["selectedEmployeeId"] if assigned else None)

    return handler
