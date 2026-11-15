"""Opt-in Ask endpoint for the authenticated manager's dashboard selection."""
import os
from collections import deque
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Response

from .business.employee_activity import business_specialists
from .dashboard_api import access
from .graph import run_analytics
from .graph_contracts import AskRequest, GraphRun
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
    if not take_request(membership.user_id):
        raise HTTPException(429, "Ask request budget exhausted", headers={"Retry-After": "60"})
    tools = PostgresAnalyticsTools(synthetic=config.synthetic, contexts=config.contexts)
    registry = ScopedToolRegistry(tools, membership.scope())
    response.headers["Cache-Control"] = "no-store"
    return run_analytics(request, registry, specialists=business_specialists())
