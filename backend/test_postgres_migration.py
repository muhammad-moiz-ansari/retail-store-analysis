"""Exercise legacy data import and normal PostgreSQL application entry points."""

from contextlib import closing
from datetime import datetime, timezone
import sqlite3

from fastapi.testclient import TestClient
import pytest

from .database import SCHEMAS, connect
from .import_sqlite import import_files
from .interaction.storage import Store
from .store_core import authenticate, hash_password, seed_defaults


def legacy_files(tmp_path):
    application, events, identities = (tmp_path / name for name in ("app.sqlite3", "events.sqlite3", "identity.sqlite3"))
    with closing(sqlite3.connect(application)) as db, db:
        db.executescript(SCHEMAS[0].read_text(encoding="utf-8"))
        db.execute(
            "INSERT INTO users VALUES (?, 'Legacy Manager', 'legacy@test.invalid', 'Manager', ?, 1, '', '')",
            ("legacy-manager", hash_password("migration-test-password")),
        )
    with closing(sqlite3.connect(events)) as db, db:
        db.executescript(SCHEMAS[1].read_text(encoding="utf-8"))
        db.execute(
            "INSERT INTO footfall VALUES ('f1', 'run', 'store', 'cam', 'zone', ?, ?, 1, 'in')",
            ("2026-11-03T14:00:00+05:00", "2026-11-03T14:00:00+05:00"),
        )
    with closing(sqlite3.connect(identities)) as db, db:
        db.execute("CREATE TABLE documents (kind TEXT, store_id TEXT, id TEXT, data TEXT, PRIMARY KEY(kind, store_id, id))")
        db.executemany("INSERT INTO documents VALUES ('person', 'store', ?, ?)", [
            ("a", '{"id":"a"}'), ("b", '{"id":"b"}'),
        ])
    return {"application": application, "events": events, "identities": identities}


def test_import_all_stores_and_refuse_overwrites(tmp_path, postgres_dsn):
    sources = legacy_files(tmp_path)
    originals = {key: path.read_bytes() for key, path in sources.items()}
    with connect(postgres_dsn) as db:
        counts = import_files(db, **sources)
        assert (counts["users"], counts["footfall"], counts["documents"]) == (1, 1, 2)
        assert authenticate(db, "legacy@test.invalid", "migration-test-password")["id"] == "legacy-manager"
        assert db.execute("SELECT ts_start FROM footfall").fetchone()["ts_start"] == datetime(
            2026, 11, 3, 9, tzinfo=timezone.utc
        )
    assert Store(postgres_dsn).list("person", "store") == [{"id": "b"}, {"id": "a"}]
    with connect(postgres_dsn) as db, pytest.raises(ValueError, match="already has records"):
        import_files(db, **sources)
    assert {key: path.read_bytes() for key, path in sources.items()} == originals


def test_import_rolls_back_when_a_later_source_fails(tmp_path, postgres_dsn):
    sources = legacy_files(tmp_path)
    with closing(sqlite3.connect(sources["events"])) as db, db:
        db.execute("UPDATE footfall SET ts_start = '2026-11-03T14:00:00'")
    with connect(postgres_dsn) as db:
        with pytest.raises(ValueError, match="without a UTC offset"):
            import_files(db, **sources)
        assert db.execute("SELECT count(*) FROM users").fetchone()["count"] == 0
        assert db.execute("SELECT count(*) FROM footfall").fetchone()["count"] == 0


def test_unified_app_login_and_settings_on_postgres(postgres_dsn, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_dsn)
    monkeypatch.setenv("RETAILPULSE_BOOTSTRAP_MANAGER_EMAIL", "migration@test.invalid")
    monkeypatch.setenv("RETAILPULSE_BOOTSTRAP_MANAGER_PASSWORD", "migration-test-password")
    from . import app

    with connect(postgres_dsn) as db:
        seed_defaults(db)
    client = TestClient(app.app)
    headers = {"x-retailpulse-internal-secret": app.INTERNAL_SECRET}
    login = client.post("/auth/login", headers=headers, json={
        "email": "migration@test.invalid", "password": "migration-test-password", "role": "Manager",
    })
    assert login.status_code == 200
    assert login.json()["user"]["id"] == "u_manager"
    headers |= {"x-retailpulse-role": "Manager", "x-retailpulse-user-id": "u_manager"}
    settings = client.get("/settings", headers=headers)
    assert settings.status_code == 200
    assert "minStaff" in settings.json()["zones"][0]
