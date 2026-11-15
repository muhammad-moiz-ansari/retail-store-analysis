from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response

from . import ask_api
from .graph_contracts import AskRequest


def test_ask_uses_only_authorized_selection_and_scope(monkeypatch):
    request = AskRequest(question="How many customers?", window={
        "start": "2026-11-03T09:00:00Z", "end": "2026-11-03T10:00:00Z",
    }, filters={"zone_id": "z1"})
    scope = object()
    membership = SimpleNamespace(user_id="manager-1", scope=lambda: scope, default_request=SimpleNamespace(
        window=request.window, filters=SimpleNamespace(event_filters=lambda: request.filters)))
    authorized = SimpleNamespace(synthetic=True, contexts=()), membership
    monkeypatch.setattr(ask_api, "_requests", {})
    monkeypatch.setattr(ask_api, "ScopedToolRegistry", lambda tools, actual_scope: actual_scope)
    def run(actual_request, registry, *, specialists):
        assert actual_request == request and registry is scope
        assert set(specialists) == {"customer_behavior", "employee_activity"}
        return "scoped"
    monkeypatch.setattr(ask_api, "run_analytics", run)
    response = Response()
    with pytest.raises(HTTPException) as denied:
        ask_api.ask(request.model_copy(update={"filters": request.filters.model_copy(update={"zone_id": "z2"})}),
                    response, authorized)
    assert denied.value.status_code == 403
    for _ in range(10):
        assert ask_api.ask(request, response, authorized) == "scoped"
    assert response.headers["cache-control"] == "no-store"
    with pytest.raises(HTTPException) as throttled:
        ask_api.ask(request, response, authorized)
    assert throttled.value.status_code == 429
    assert ask_api.take_request("another-manager")


def test_ask_requires_opt_in_and_budget_expires(monkeypatch):
    monkeypatch.delenv("RETAILPULSE_ASK_ENABLED", raising=False)
    with pytest.raises(HTTPException) as disabled:
        ask_api.ask_enabled()
    assert disabled.value.status_code == 503
    monkeypatch.setenv("RETAILPULSE_ASK_ENABLED", "1")
    assert ask_api.ask_enabled() is None
    monkeypatch.setattr(ask_api, "_requests", {})
    monkeypatch.setattr(ask_api, "monotonic", lambda: 100)
    assert all(ask_api.take_request("manager") for _ in range(10))
    assert not ask_api.take_request("manager")
    monkeypatch.setattr(ask_api, "monotonic", lambda: 160)
    assert ask_api.take_request("manager")
