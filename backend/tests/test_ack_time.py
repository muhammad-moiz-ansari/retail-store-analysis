"""C3: acknowledgement time is logged once per task and summarised on System Status."""

from fastapi.testclient import TestClient

from backend import app as app_module
from backend.dispatch import handle_event
from backend.store_core import seed_defaults


def test_ack_seconds_set_once_and_reported(postgres_connection, postgres_dsn, monkeypatch):
    seed_defaults(postgres_connection)
    task_id = handle_event(postgres_connection, {"eventType": "unattended_customer", "zoneId": "z2"})["taskId"]
    postgres_connection.execute("UPDATE tasks SET created_at = '2026-11-13T09:00:00+00:00' WHERE id = %s", (task_id,))
    postgres_connection.commit()
    monkeypatch.setenv("DATABASE_URL", postgres_dsn)
    client = TestClient(app_module.app)
    employee = {"x-retailpulse-internal-secret": app_module.INTERNAL_SECRET, "x-retailpulse-role": "Employee", "x-retailpulse-user-id": "u_employee"}
    assert client.post(f"/tasks/{task_id}/transition", json={"state": "acknowledged"}, headers=employee).status_code == 200
    first = postgres_connection.execute("SELECT ack_seconds FROM tasks WHERE id = %s", (task_id,)).fetchone()["ack_seconds"]
    assert first > 0
    client.post(f"/tasks/{task_id}/transition", json={"state": "acknowledged"}, headers=employee)  # a repeat keeps the first time
    assert postgres_connection.execute("SELECT ack_seconds FROM tasks WHERE id = %s", (task_id,)).fetchone()["ack_seconds"] == first
    status = client.get("/system-status", headers={**employee, "x-retailpulse-role": "Manager"}).json()
    assert status["acknowledgement"]["tasks"] == 1 and status["acknowledgement"]["medianSeconds"] == first
