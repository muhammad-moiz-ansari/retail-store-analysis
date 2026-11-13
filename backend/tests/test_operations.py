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
