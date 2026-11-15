"""The whole operational chain: signal policy -> adapter -> real dispatch handler, on Ruhab's fixture tools."""

from backend.agents.business.test_signal_policy import DAY, NOW, registry
from backend.agents.operational import OperationalDispatchAdapter
from backend.dispatch import make_dispatch_handler
from backend.operations import run_cycle
from backend.store_core import seed_defaults


def test_cycle_dispatches_once_and_keeps_fixture_data_off_real_tasks(postgres_connection, postgres_dsn):
    seed_defaults(postgres_connection)
    postgres_connection.commit()
    adapter = OperationalDispatchAdapter(make_dispatch_handler(postgres_dsn))
    tasks = lambda: postgres_connection.execute("SELECT count(*) AS n FROM tasks").fetchone()["n"]

    guarded = run_cycle(registry(), ["z2"], DAY, NOW, adapter=adapter)
    assert not guarded["receipts"] and {s["reason"] for s in guarded["suppressed"]} == {"synthetic_not_dispatched"}
    assert tasks() == 0

    demo = run_cycle(registry(), ["z2", "z1"], DAY, NOW, adapter=adapter, allow_synthetic=True)
    decisions = sorted((r.event_id.split("-")[0], r.zone_id, r.decision) for r in demo["receipts"])
    assert ("evt", "z2", "dispatched") in decisions
    assert all(r.reason_code == "handler_reported" for r in demo["receipts"])
    assert tasks() == 1  # z2's second event (unstaffed) is covered by the open task, z1 is staffed enough

    again = run_cycle(registry(), ["z2", "z1"], DAY, NOW, adapter=adapter, allow_synthetic=True)
    assert {r.decision for r in again["receipts"]} == {"duplicate"} and tasks() == 1


def _config(store_id="store-1", zones=("z2", "z3")):
    from backend.agents.dashboard import DashboardConfig

    window = {"start": "2026-11-03T09:00:00Z", "end": "2026-11-03T10:00:00Z"}
    return DashboardConfig.model_validate({
        "version": 1, "synthetic": True,
        "memberships": [{"user_id": "u1", "store_id": store_id, "run_ids": ["r1"], "camera_ids": ["c1"], "zone_ids": list(zones),
                         "default_request": {"storeId": store_id, "window": window, "filters": {"runId": "r1", "zoneId": zones[0]}}}]})


def test_config_cycle_refuses_scopes_it_was_not_configured_for(monkeypatch):
    import pytest
    from datetime import datetime, timezone

    import backend.operations as operations

    now = datetime(2026, 11, 3, 11, tzinfo=timezone.utc)
    run = lambda config, **kw: operations.cycle_from_config(config, kw.pop("user_id", "u1"), kw.pop("zones", None), None, now,
                                                            dry_run=True, allow_synthetic=False)
    monkeypatch.setattr(operations, "STORE_ID", "store-1")
    with pytest.raises(SystemExit, match="RETAILPULSE_STORE_ID"):
        run(_config(store_id="store-2"))  # the handler would refuse this store anyway; fail before any read
    with pytest.raises(SystemExit, match="outside"):
        run(_config(), zones=["z9"])
    with pytest.raises(SystemExit, match="--user-id"):
        run(_config(), user_id="someone-else")


def test_prepare_demo_writes_a_valid_configuration_for_an_ingested_run(postgres_connection):
    from backend.agents.dashboard import DashboardConfig
    from backend.events.fixtures import RUN_ID, generate
    from backend.prepare_demo import build_config, describe_run

    generate(postgres_connection)
    postgres_connection.commit()
    run = describe_run(postgres_connection, RUN_ID)
    config = build_config(run, RUN_ID, "manager-1", footfall_validated=False, attest_fixed_derivation=True)
    parsed = DashboardConfig.model_validate(config)  # the same validation the backend applies
    assert parsed.synthetic is False and parsed.memberships[0].default_request.filters.runId == RUN_ID
    assert all("footfall" not in c.available_sources for c in parsed.contexts)  # not declared until validated
    assert {v.run_id for v in parsed.verified_unattended_runs} == {RUN_ID}
