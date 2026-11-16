"""Read-only advisory routes over the manager's dashboard selection: anomaly evidence for one alert, and a next-day
staffing proposal. Both are partial by design and say what they lack; neither dispatches, edits a roster or approves anything.

Alert ownership: app alerts carry no store column. An alert is investigated only when it came from an orchestration
event of this single-store backend (RETAILPULSE_STORE_ID equals the manager's store) whose zone is inside the
manager's membership. Anything else is reported as not found.
"""
import json
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from psycopg import Error

from ..database import DatabaseNotConfigured, read_only
from .anomaly import InvestigationContext, investigate
from .business.signal_policy import SignalPolicy
from .contracts import Identifier
from .dashboard import footfall_total
from .dashboard_api import access
from .staffing_plan import ShiftInputs, propose_next_day
from .tools.contextual import PostgresAnalyticsTools
from .tools.registry import ScopedToolRegistry

router = APIRouter(prefix="/agents", tags=["analytics agents"])
# Demo defaults, not tuned on store data; they are returned with every answer so the reader can see them.
MIN_FPS, MAX_QUEUE_LENGTH, CUSTOMERS_PER_EMPLOYEE = 0.5, 3, 10


def _registry(config, membership):
    tools = PostgresAnalyticsTools(synthetic=config.synthetic, contexts=config.contexts,
                                   verified_unattended_runs=config.verified_unattended_runs)
    return ScopedToolRegistry(tools, membership.scope())


def _arguments(membership, zone_id):
    selection = membership.default_request
    filters = selection.filters.event_filters().model_copy(update={"zone_id": zone_id})
    return {"window": selection.window.model_dump(mode="json"), "filters": filters.model_dump(exclude_none=True), "limit": 1000}


def _own_store(membership):
    if os.getenv("RETAILPULSE_STORE_ID", "store-1") != membership.store_id:
        raise HTTPException(403, "This backend does not serve the manager's store")


@router.post("/alerts/{alert_id}/investigate")
def investigate_alert(alert_id: Identifier, response: Response, authorized=Depends(access)):
    """Candidate explanations for one alert, each with cited rows: a camera problem, low staffed coverage, a long queue."""
    config, membership = authorized
    _own_store(membership)
    try:
        with read_only() as conn:
            alert = conn.execute("SELECT evidence_json FROM alerts WHERE id = %s", (alert_id,)).fetchone()
            try:
                event_id = json.loads(alert["evidence_json"]).get("eventId") if alert else None
            except (ValueError, AttributeError):
                event_id = None
            event = conn.execute("SELECT zone_id FROM orchestration_events WHERE id = %s", (event_id,)).fetchone() if event_id else None
    except (Error, DatabaseNotConfigured):
        raise HTTPException(503, "Alert store unavailable") from None
    zone_id = event["zone_id"] if event else None
    if not zone_id or zone_id not in membership.zone_ids:
        raise HTTPException(404, "Alert not found")  # includes alerts with no trusted zone: nothing is guessed

    registry, arguments = _registry(config, membership), _arguments(membership, zone_id)
    context = InvestigationContext(alert_id=alert_id, zone_id=zone_id, scope=membership.scope(), window=membership.default_request.window,
                                   synthetic=config.synthetic, min_fps=MIN_FPS, max_queue_length=MAX_QUEUE_LENGTH,
                                   min_staffed_ratio=SignalPolicy().min_staffed_ratio)
    result = investigate(context, coverage=registry.invoke("get_coverage", arguments), queue=registry.invoke("get_queue", arguments),
                         health=registry.invoke("get_pipeline_health", arguments))
    response.headers["Cache-Control"] = "no-store"
    return {**result.model_dump(mode="json"), "zone_id": zone_id, "window": arguments["window"], "synthetic": config.synthetic,
            "thresholds": {"min_fps": MIN_FPS, "max_queue_length": MAX_QUEUE_LENGTH, "min_staffed_ratio": context.min_staffed_ratio},
            "limitations": ["Evidence is read over the dashboard's selected window, not the alert's own time.",
                            "Candidates are signals that co-occur with the alert; none is a confirmed cause.",
                            "Thresholds are demonstration defaults, not agreed store policy."]}


@router.get("/staffing/next-day")
def staffing_next_day(response: Response, authorized=Depends(access)):
    """Advisory staff counts per zone for tomorrow (UTC day). Always approval_required; changes no roster."""
    config, membership = authorized
    _own_store(membership)
    try:
        with read_only() as conn:
            minimum = {r["id"]: r["min_staff"] for r in conn.execute("SELECT id, min_staff FROM zones")}
            rostered = {r["zone_id"]: r["n"] for r in conn.execute(
                """SELECT rosters.zone_id, COUNT(*) AS n FROM rosters JOIN users ON users.id = rosters.user_id
                   WHERE rosters.available = 1 AND users.active = 1 AND users.role = 'Employee' AND rosters.zone_id IS NOT NULL
                   GROUP BY rosters.zone_id""")}
    except (Error, DatabaseNotConfigured):
        raise HTTPException(503, "Roster store unavailable") from None

    registry = _registry(config, membership)
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    shifts = []
    for zone_id in membership.zone_ids:
        arguments = _arguments(membership, zone_id)
        entries = footfall_total(registry.invoke("get_footfall", arguments | {"granularity": "day"}), "entries")
        zone = next((z for z in registry.invoke("get_coverage", arguments).zones if z.zone_id == zone_id), None)
        ratio = zone.staffed_open_ratio if zone else None
        shifts.append(ShiftInputs(
            zone_id=zone_id, shift_id="day", window={"start": tomorrow, "end": tomorrow + timedelta(days=1)},
            forecast_customers=entries.value, forecast_evidence=entries.evidence[:10],
            historical_staffed_ratio=ratio.value if ratio else None, coverage_evidence=ratio.evidence[:10] if ratio else (),
            rostered_staff=rostered.get(zone_id, 0) if zone_id in minimum else None, minimum_staff=minimum.get(zone_id, 0)))
    proposal = propose_next_day(membership.scope(), tuple(shifts), as_of=now, timezone_name="UTC",
                                customers_per_employee=CUSTOMERS_PER_EMPLOYEE)
    response.headers["Cache-Control"] = "no-store"
    return {**proposal.model_dump(mode="json"), "synthetic": config.synthetic, "customers_per_employee": CUSTOMERS_PER_EMPLOYEE,
            "forecast_basis": "entries observed in the dashboard's selected window, repeated unchanged",
            "limitations": ["No demand forecast model exists: tomorrow is assumed to repeat the selected window's entrance count.",
                            "Roster counts are staff marked available per zone; shift times are free text and are not checked.",
                            "Customers per employee is a demonstration default, not agreed store policy.",
                            "A proposal is advice for a manager to approve; nothing is scheduled."]}
