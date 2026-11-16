"""Advisory routes over the manager's dashboard selection: anomaly evidence for one alert, a next-day staffing
proposal with a recorded manager decision, and the store digest. All are partial by design and say what they lack.
Nothing here dispatches or edits a roster; the only write is the manager's approve/reject record.

Alert ownership: app alerts carry no store column. An alert is investigated only when it came from an orchestration
event of this single-store backend (RETAILPULSE_STORE_ID equals the manager's store) whose zone is inside the
manager's membership. Anything else is reported as not found.
"""
import json
import os
from datetime import datetime, timedelta, timezone

from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from psycopg import Error
from pydantic import BaseModel

from ..database import DatabaseNotConfigured, connect, read_only
from .anomaly import InvestigationContext, investigate
from .business.employee_activity import business_specialists
from .business.narration import build_digest
from .business.signal_policy import SignalPolicy, evaluate_zone
from .contracts import Identifier
from .dashboard import footfall_total
from .dashboard_api import access
from .graph import run_analytics
from .graph_contracts import AskRequest
from .staffing_plan import ShiftInputs, propose_next_day
from .tools.contextual import PostgresAnalyticsTools
from .tools.registry import ScopedToolRegistry

router = APIRouter(prefix="/agents", tags=["analytics agents"])
# Demo defaults, not tuned on store data; they are returned with every answer so the reader can see them.
MIN_FPS, MAX_QUEUE_LENGTH, CUSTOMERS_PER_EMPLOYEE = 0.5, 3, 10
DIGEST_QUESTIONS = ("Summarise customers today", "Where are the staffing gaps?")  # the two A4 acceptance questions


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


def _proposal(config, membership):
    """Tomorrow's (UTC day) advisory staff counts per zone, built from the selected window. Reads only."""
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
    return {**proposal.model_dump(mode="json"), "for_date": tomorrow.date().isoformat(), "synthetic": config.synthetic,
            "customers_per_employee": CUSTOMERS_PER_EMPLOYEE,
            "forecast_basis": "entries observed in the dashboard's selected window, repeated unchanged",
            "limitations": ["No demand forecast model exists: tomorrow is assumed to repeat the selected window's entrance count.",
                            "Roster counts are staff marked available per zone; shift times are free text and are not checked.",
                            "Customers per employee is a demonstration default, not agreed store policy.",
                            "A proposal is advice for a manager to approve; approving records the decision and schedules nothing."]}


def _decision(conn, store_id, for_date):
    row = conn.execute("""SELECT staffing_decisions.id, decision, decided_at, users.name AS decided_by FROM staffing_decisions
                          LEFT JOIN users ON users.id = staffing_decisions.decided_by
                          WHERE store_id = %s AND for_date = %s ORDER BY decided_at DESC LIMIT 1""", (store_id, for_date)).fetchone()
    return dict(row) if row else None


@router.get("/staffing/next-day")
def staffing_next_day(response: Response, authorized=Depends(access)):
    """Advisory staff counts per zone for tomorrow, with the manager's latest decision on it, if any."""
    config, membership = authorized
    _own_store(membership)
    proposal = _proposal(config, membership)
    try:
        with read_only() as conn:
            proposal["decision"] = _decision(conn, membership.store_id, proposal["for_date"])
    except (Error, DatabaseNotConfigured):
        raise HTTPException(503, "Decision store unavailable") from None
    response.headers["Cache-Control"] = "no-store"
    return proposal


class StaffingDecision(BaseModel):
    decision: Literal["approved", "rejected"]


@router.post("/staffing/next-day/decision")
def decide_staffing(body: StaffingDecision, response: Response, authorized=Depends(access)):
    """Record the manager's decision against the proposal as the server computes it now. No roster or task changes."""
    config, membership = authorized
    _own_store(membership)
    proposal = _proposal(config, membership)
    try:
        with connect() as conn:
            conn.execute("""INSERT INTO staffing_decisions(id, store_id, for_date, decision, proposal_json, decided_by, decided_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                         (uuid4().hex, membership.store_id, proposal["for_date"], body.decision, json.dumps(proposal),
                          membership.user_id, datetime.now(timezone.utc).isoformat()))
            recorded = _decision(conn, membership.store_id, proposal["for_date"])
    except (Error, DatabaseNotConfigured):
        raise HTTPException(503, "Decision store unavailable") from None
    response.headers["Cache-Control"] = "no-store"
    return {**proposal, "decision": recorded}


@router.get("/digest")
def store_digest(response: Response, authorized=Depends(access)):
    """The store digest for the selected window: the two standard questions through the business agents, plus the
    signal policy's decisions per zone (evaluated only; nothing is dispatched)."""
    config, membership = authorized
    registry, selection = _registry(config, membership), membership.default_request
    runs = [run_analytics(AskRequest(question=question, window=selection.window, filters=selection.filters.event_filters()),
                          registry, specialists=business_specialists()) for question in DIGEST_QUESTIONS]
    now = datetime.now(timezone.utc)
    decisions = tuple(d for zone_id in membership.zone_ids for d in evaluate_zone(registry, zone_id, selection.window, now))
    digest = build_digest(runs, decisions=decisions)
    response.headers["Cache-Control"] = "no-store"
    return {**digest.model_dump(mode="json"), "text": digest.text()}
