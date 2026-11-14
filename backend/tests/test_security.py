"""Backend fixes from docs/fyp2-plan/SECURITY_REVIEW.md (S1-S3, S5-S8)."""

import hashlib

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend import app as app_module
from backend.runtime_secrets import DEV_DEFAULT, internal_secret, matches
from backend.store_core import authenticate, create_invitation, accept_invitation, hash_password, now_iso, seed_defaults, verify_password

INTERNAL = {"x-retailpulse-internal-secret": app_module.INTERNAL_SECRET}


def test_secrets_fail_closed_outside_dev(monkeypatch):
    monkeypatch.delenv("RETAILPULSE_DEV_DEFAULTS", raising=False)
    monkeypatch.delenv("X_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        internal_secret("X_SECRET")
    monkeypatch.setenv("X_SECRET", DEV_DEFAULT)
    with pytest.raises(RuntimeError):
        internal_secret("X_SECRET")
    monkeypatch.setenv("X_SECRET", "a-real-long-random-value")
    assert internal_secret("X_SECRET") == "a-real-long-random-value"
    monkeypatch.delenv("X_SECRET")
    monkeypatch.setenv("RETAILPULSE_DEV_DEFAULTS", "1")
    assert internal_secret("X_SECRET") == DEV_DEFAULT
    assert matches("abc", "abc") and not matches(None, "abc") and not matches("abd", "abc")


def test_legacy_hash_still_verifies_and_new_hashes_use_600k():
    salt = "s1"
    legacy = f"pbkdf2_sha256${salt}${hashlib.pbkdf2_hmac('sha256', b'pw123456', salt.encode(), 120_000).hex()}"
    assert verify_password("pw123456", legacy) and not verify_password("wrong", legacy)
    assert hash_password("pw123456").split("$")[1] == "600000"


@pytest.fixture
def db(postgres_connection, postgres_dsn, monkeypatch):
    seed_defaults(postgres_connection)
    postgres_connection.commit()
    monkeypatch.setenv("DATABASE_URL", postgres_dsn)
    return postgres_connection


def test_login_upgrades_a_legacy_hash(db):
    salt = "s2"
    legacy = f"pbkdf2_sha256${salt}${hashlib.pbkdf2_hmac('sha256', b'pw123456', salt.encode(), 120_000).hex()}"
    db.execute("UPDATE users SET password_hash = %s WHERE id = 'u_employee'", (legacy,))
    authenticate(db, "employee@retailpulse.local", "pw123456")
    stored = db.execute("SELECT password_hash FROM users WHERE id = 'u_employee'").fetchone()["password_hash"]
    assert stored.split("$")[1] == "600000" and verify_password("pw123456", stored)


def test_invitation_token_is_stored_hashed(db):
    invite = create_invitation(db, "new@test", "Employee", None)
    stored = db.execute("SELECT token FROM invitations WHERE id = %s", (invite["id"],)).fetchone()["token"]
    assert stored != invite["token"] and stored == hashlib.sha256(invite["token"].encode()).hexdigest()
    assert accept_invitation(db, invite["token"], "New", "longenough1")["email"] == "new@test"
    with pytest.raises(ValueError):
        accept_invitation(db, invite["token"], "New", "longenough1")  # single use
    with pytest.raises(ValueError):
        accept_invitation(db, stored, "Attacker", "longenough1")  # the stored hash is not a usable token


def test_login_locks_an_account_after_repeated_failures(db, monkeypatch):
    monkeypatch.setattr(app_module, "_failed_logins", {})
    client = TestClient(app_module.app)
    body = {"email": "employee@retailpulse.local", "password": "wrong-password"}
    assert [client.post("/auth/login", json=body, headers=INTERNAL).status_code for _ in range(5)] == [401] * 5
    good = {**body, "password": "password123"}
    assert client.post("/auth/login", json=good, headers=INTERNAL).status_code == 429  # locked even with the right password
    monkeypatch.setattr(app_module, "_failed_logins", {})
    assert client.post("/auth/login", json=good, headers=INTERNAL).status_code == 200


def test_signup_needs_eight_characters(db):
    client = TestClient(app_module.app)
    reply = client.post("/auth/invitations/accept", json={"token": "t", "name": "n", "password": "1234567"}, headers=INTERNAL)
    assert reply.status_code == 400 and "8+" in reply.json()["detail"]


def test_cv_jobs_are_capped_and_old_ones_expire(monkeypatch):
    jobs = {f"done{i}": {"status": "done"} for i in range(60)} | {"r1": {"status": "running"}, "r2": {"status": "queued"}}
    monkeypatch.setattr(app_module, "_jobs", jobs)
    with pytest.raises(HTTPException) as busy:
        app_module.start_job(["-c", "pass"], lambda: None)
    assert busy.value.status_code == 429
    jobs["r2"]["status"] = "done"
    monkeypatch.setattr(app_module.asyncio, "get_running_loop", lambda: type("L", (), {"run_in_executor": lambda *a: None})())
    app_module.start_job(["-c", "pass"], lambda: None)
    assert sum(j["status"] == "done" for j in jobs.values()) == app_module.MAX_KEPT_JOBS
