"""C3: the assigned employee can fetch their task's spoken instruction; nobody else's."""

from fastapi.testclient import TestClient

from backend import app as app_module
from backend.dispatch import handle_event
from backend.store_core import seed_defaults


def test_voice_for_own_task_only(postgres_connection, postgres_dsn, monkeypatch):
    seed_defaults(postgres_connection)
    task_id = handle_event(postgres_connection, {"eventType": "unattended_customer", "zoneId": "z2"})["taskId"]
    postgres_connection.commit()
    monkeypatch.setenv("DATABASE_URL", postgres_dsn)
    for key in ("HF_TOKEN", "ELEVENLABS_API_KEY"):
        monkeypatch.delenv(key, raising=False)  # offline: template script, no audio
    client = TestClient(app_module.app)
    base = {"x-retailpulse-internal-secret": app_module.INTERNAL_SECRET, "x-retailpulse-role": "Employee"}
    mine = client.post(f"/tasks/{task_id}/voice", headers={**base, "x-retailpulse-user-id": "u_employee"})
    assert mine.status_code == 200
    body = mine.json()
    assert body["script"]["script"] and body["script"]["fallback"] and body["audio"]["audioBase64"] is None
    assert client.post(f"/tasks/{task_id}/voice", headers={**base, "x-retailpulse-user-id": "someone-else"}).status_code == 403
    assert client.post("/tasks/missing/voice", headers={**base, "x-retailpulse-user-id": "u_employee"}).status_code == 404
