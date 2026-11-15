"""Opt-in Ask endpoint for the authenticated manager's dashboard selection."""
import os
from collections import deque
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Response
from psycopg import Error

from ..database import DatabaseNotConfigured
from .ask_budget import take_shared_request
from .business.employee_activity import business_specialists
from .dashboard_api import access
from .graph import run_analytics
from .contracts import Identifier
from .graph_contracts import AskRequest, GraphRun
from .postgres_traces import PostgresTraceStore
from .service import AnalyticsService
from .specialists import operations_registration
from .tools.contextual import PostgresAnalyticsTools
from .tools.registry import ScopedToolRegistry

router = APIRouter(prefix="/agents", tags=["analytics agents"])
_requests = {}
_lock = Lock()


def take_request(user_id):
    with _lock:
        now = monotonic()
        for key, timestamps in list(_requests.items()):
            while timestamps and now - timestamps[0] >= 60:
                timestamps.popleft()
            if not timestamps:
                del _requests[key]
        if user_id not in _requests and len(_requests) >= 1000:
            return False
        timestamps = _requests.setdefault(user_id, deque())
        if len(timestamps) >= 10:
            return False
        timestamps.append(now)
        return True


def ask_enabled():
    if os.getenv("RETAILPULSE_ASK_ENABLED") != "1":
        raise HTTPException(503, "Ask RetailPulse is disabled")


@router.post("/ask", response_model=GraphRun, dependencies=[Depends(ask_enabled)])
def ask(request: AskRequest, response: Response, authorized=Depends(access)):
    config, membership = authorized
    selection = membership.default_request
    if request.window != selection.window or request.filters != selection.filters.event_filters():
        raise HTTPException(403, "Ask selection must match the configured dashboard selection")
    try:
        allowed = (take_shared_request(membership.user_id, membership.store_id)
                   if os.getenv("RETAILPULSE_ASK_SHARED_BUDGET") == "1" else take_request(membership.user_id))
    except (Error, DatabaseNotConfigured):
        raise HTTPException(503, "Shared Ask budget unavailable") from None
    if not allowed:
        raise HTTPException(429, "Ask request budget exhausted", headers={"Retry-After": "60"})
    tools = PostgresAnalyticsTools(synthetic=config.synthetic, contexts=config.contexts,
                                  verified_unattended_runs=config.verified_unattended_runs)
    scope = membership.scope()
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-RetailPulse-Analytics-Source"] = "synthetic" if config.synthetic else "recorded"
    specialists = business_specialists() | {"operations": operations_registration()}
    if os.getenv("RETAILPULSE_ASK_TRACE_ENABLED") == "1":
        return AnalyticsService(tools, specialists=specialists, traces=PostgresTraceStore()).ask(request, scope=scope)
    return run_analytics(request, ScopedToolRegistry(tools, scope), specialists=specialists)


@router.get("/runs/{run_id}", response_model=GraphRun, dependencies=[Depends(ask_enabled)])
def get_run(run_id: Identifier, response: Response, authorized=Depends(access)):
    _, membership = authorized
    try:
        if os.getenv("RETAILPULSE_ASK_TRACE_ENABLED") != "1":
            raise KeyError(run_id)
        run = PostgresTraceStore().get(run_id, membership.scope())
        selection = membership.default_request
        if run.request.window != selection.window or run.request.filters != selection.filters.event_filters():
            raise KeyError(run_id)
    except KeyError:
        raise HTTPException(404, "Analytics run not found") from None
    except RuntimeError:
        raise HTTPException(503, "Ask trace storage unavailable") from None
    response.headers["Cache-Control"] = "no-store"
    return run
