"""Direct dispatch with no manager step: CV episodes and Moiz's operational adapter reach the same handler.
Covers duplicates, key conflicts, eligibility, coverage and store/zone binding."""

import pytest

from backend.agents.operational import OperationalDispatchAdapter
from backend.agents.test_operational import event, operational_scope, payload
from backend.agents.operational import OperationalEvent
from backend.dispatch import IdempotencyConflict, dispatch_unattended, handle_event, make_dispatch_handler
from backend.store_core import now_iso, seed_defaults


@pytest.fixture
def store(postgres_connection):
    seed_defaults(postgres_connection)
    postgres_connection.commit()
    return postgres_connection


def add_episode(conn, run_id, track, zone="z2", waited=200.0):
    conn.execute(
        "INSERT INTO unattended_episodes(event_id, run_id, store_id, camera_id, zone_id, ts_start, ts_end, customer_track_id, waited_s, helped)"
        " VALUES (%s, %s, 'store-1', 'c2', %s, %s, %s, %s, %s, 0)",
        (f"{run_id}:unattended:c2:{track}", run_id, zone, f"2026-11-03T09:0{track}:00+00:00", f"2026-11-03T09:0{track}:59+00:00", track, waited),
    )


def add_employee(conn, user_id, zone, available=1, rostered=True):
    ts = now_iso()
    conn.execute("INSERT INTO users(id, name, email, role, password_hash, active, created_at, updated_at) VALUES (%s, %s, %s, 'Employee', 'x', 1, %s, %s)",
                 (user_id, user_id, f"{user_id}@test", ts, ts))
    if rostered:
        conn.execute("INSERT INTO rosters(id, user_id, zone_id, shift, available, created_at, updated_at) VALUES (%s, %s, %s, 'all day', %s, %s, %s)",
                     (f"r_{user_id}", user_id, zone, available, ts, ts))


def count(conn, table):
    return conn.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]


def test_episodes_dispatch_once_and_repeats_make_no_new_task(store):
    add_episode(store, "run1", 1)
    add_episode(store, "run1", 2)
    first = dispatch_unattended(store, store, "run1")
    assert [r["decision"] for r in first] == ["dispatched", "already_assigned"]
    task = store.execute("SELECT * FROM tasks").fetchone()
    assert (task["employee_id"], task["target_zone_id"], task["state"]) == ("u_employee", "z2", "delivered")

    again = dispatch_unattended(store, store, "run1")  # the same run dispatched a second time
    assert [r["decision"] for r in again] == ["duplicate", "duplicate"]
    assert again[0]["taskId"] == first[0]["taskId"]
    assert count(store, "tasks") == 1 and count(store, "orchestration_events") == 2

    store.execute("UPDATE tasks SET state = 'completed'")  # once the zone's task is done, new demand dispatches again
    add_episode(store, "run1", 3)
    assert dispatch_unattended(store, store, "run1")[-1]["decision"] == "dispatched"


def test_no_task_when_no_employee_is_eligible(store):
    store.execute("UPDATE rosters SET available = 0")
    add_employee(store, "u_unrostered", None, rostered=False)
    add_episode(store, "run1", 1)
    [result] = dispatch_unattended(store, store, "run1")
    assert result["decision"] == "no_eligible_employee" and result["taskId"] is None
    assert count(store, "tasks") == 0
    assert store.execute("SELECT category FROM alerts WHERE id = %s", (result["alertId"],)).fetchone()["category"] == "Unattended Customers"


def test_coverage_keeps_zone_minimum_staff(store):
    # z2 needs 1 person; its only employee cannot be pulled to z3
    assert handle_event(store, {"eventType": "unattended_customer", "zoneId": "z3"})["decision"] == "no_eligible_employee"
    add_employee(store, "u_second", "z2")  # z2 now has 2 free for min_staff 1, so one may go
    assert handle_event(store, {"eventType": "unattended_customer", "zoneId": "z3"})["decision"] == "dispatched"
    add_employee(store, "u_floater", None)  # no rostered zone: always eligible
    assert handle_event(store, {"eventType": "unattended_customer", "zoneId": "z4"})["decision"] == "dispatched"


def test_paused_dispatch_and_alert_only(store):
    assert handle_event(store, {"eventType": "manual_event", "zoneId": "z2"})["decision"] == "alert_only"
    store.execute("UPDATE settings SET value_json = %s WHERE key = 'thresholds'", ('{"dispatchPaused": true}',))
    assert handle_event(store, {"eventType": "unattended_customer", "zoneId": "z2"})["decision"] == "paused"
    assert count(store, "tasks") == 0


def test_same_key_with_another_event_is_a_conflict(store):
    handle_event(store, {"eventId": "e1", "dedupeKey": "k1", "eventType": "unattended_customer", "zoneId": "z2"})
    assert handle_event(store, {"eventId": "e1", "dedupeKey": "k1", "eventType": "unattended_customer", "zoneId": "z2"})["decision"] == "duplicate"
    with pytest.raises(IdempotencyConflict):
        handle_event(store, {"eventId": "e2", "dedupeKey": "k1", "eventType": "unattended_customer", "zoneId": "z2"})


def test_adapter_with_the_real_handler(store, postgres_dsn):
    store.commit()
    adapter = OperationalDispatchAdapter(make_dispatch_handler(postgres_dsn))
    scope = operational_scope()
    # z1 has nobody rostered and z2's only employee is its minimum staff: nothing is sent
    assert adapter.handle(event(), scope=scope).decision == "no_eligible_employee"

    add_employee(store, "u_z1", "z1")
    store.commit()
    second = OperationalEvent.model_validate(payload() | {"eventId": "synthetic-event-2", "idempotencyKey": "synthetic-idempotency-2"})
    sent = adapter.handle(second, scope=scope)
    assert (sent.decision, sent.selected_employee_id, sent.reason_code) == ("dispatched", "u_z1", "handler_reported")
    repeat = adapter.handle(second, scope=scope)
    assert (repeat.decision, repeat.task_id) == ("duplicate", sent.task_id)

    conflict = OperationalEvent.model_validate(payload() | {"eventId": "synthetic-event-3", "idempotencyKey": "synthetic-idempotency-2"})
    assert adapter.handle(conflict, scope=scope).reason_code == "handler_error"
    store.rollback()
    assert count(store, "tasks") == 1


def test_handler_refuses_another_store_or_unknown_zone(store, postgres_dsn, monkeypatch):
    store.commit()
    handler = make_dispatch_handler(postgres_dsn)
    monkeypatch.setattr("backend.dispatch.STORE_ID", "store-9")
    with pytest.raises(PermissionError):
        handler(event=event(), scope=operational_scope())
    monkeypatch.setattr("backend.dispatch.STORE_ID", "store-1")
    store.execute("DELETE FROM cameras WHERE zone_id = 'z1'")
    store.execute("DELETE FROM zones WHERE id = 'z1'")
    store.commit()
    with pytest.raises(PermissionError):
        handler(event=event(), scope=operational_scope())


def test_ranking_and_scenario_harness():
    import json, os
    from backend.dispatch_eval import DEFAULT, evaluate
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL database")
    scenarios = {s["id"]: s for s in json.loads(DEFAULT.read_text())["scenarios"]}
    picked = [dict(s, rater_choice=r) for s, r in ((scenarios["S11"], "f"), (scenarios["S12"], "c"), (scenarios["S08"], "none"))]
    report = evaluate(picked, os.environ["TEST_DATABASE_URL"])
    assert [r["system"] for r in report["scenarios"]] == ["f", "c", "none"] and report["agreement"] == 1.0
    assert "keeps 1 above" in report["scenarios"][1]["reason"]  # z6 had the most spare staff
