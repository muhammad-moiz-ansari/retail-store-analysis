from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(os.getenv("RETAILPULSE_DB_PATH", "backend/retailpulse.sqlite3"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    initialize(conn)
    return conn


def initialize(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', '1');

        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          email TEXT NOT NULL UNIQUE,
          role TEXT NOT NULL CHECK (role IN ('Manager', 'Employee')),
          password_hash TEXT NOT NULL,
          active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS invitations (
          id TEXT PRIMARY KEY,
          email TEXT NOT NULL,
          role TEXT NOT NULL CHECK (role IN ('Manager', 'Employee')),
          token TEXT NOT NULL UNIQUE,
          expires_at TEXT NOT NULL,
          accepted_at TEXT,
          created_by TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY(created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS zones (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          type TEXT NOT NULL,
          capacity INTEGER NOT NULL,
          min_staff INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cameras (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          zone_id TEXT,
          role TEXT NOT NULL DEFAULT 'floor',
          source_type TEXT NOT NULL DEFAULT 'recording',
          source_url TEXT,
          online INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(zone_id) REFERENCES zones(id)
        );

        CREATE TABLE IF NOT EXISTS rosters (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          zone_id TEXT,
          shift TEXT NOT NULL,
          available INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id),
          FOREIGN KEY(zone_id) REFERENCES zones(id)
        );

        CREATE TABLE IF NOT EXISTS settings (
          key TEXT PRIMARY KEY,
          value_json TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alerts (
          id TEXT PRIMARY KEY,
          category TEXT NOT NULL,
          severity TEXT NOT NULL CHECK (severity IN ('high', 'medium', 'low')),
          title TEXT NOT NULL,
          context TEXT NOT NULL,
          href TEXT NOT NULL DEFAULT '/alerts',
          status TEXT NOT NULL CHECK (status IN ('active', 'resolved')) DEFAULT 'active',
          source TEXT NOT NULL DEFAULT 'orchestrator',
          evidence_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          resolved_at TEXT,
          resolved_by TEXT,
          FOREIGN KEY(resolved_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS orchestration_events (
          id TEXT PRIMARY KEY,
          event_type TEXT NOT NULL,
          source TEXT NOT NULL,
          zone_id TEXT,
          severity TEXT NOT NULL DEFAULT 'medium',
          title TEXT NOT NULL,
          evidence_json TEXT NOT NULL DEFAULT '{}',
          source_timestamp TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY(zone_id) REFERENCES zones(id)
        );

        CREATE TABLE IF NOT EXISTS dispatch_decisions (
          id TEXT PRIMARY KEY,
          event_id TEXT NOT NULL,
          alert_id TEXT,
          task_id TEXT,
          selected_employee_id TEXT,
          decision TEXT NOT NULL,
          reason TEXT NOT NULL,
          policy_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          FOREIGN KEY(event_id) REFERENCES orchestration_events(id),
          FOREIGN KEY(alert_id) REFERENCES alerts(id),
          FOREIGN KEY(task_id) REFERENCES tasks(id),
          FOREIGN KEY(selected_employee_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS tasks (
          id TEXT PRIMARY KEY,
          employee_id TEXT NOT NULL,
          target_zone_id TEXT,
          source_zone_id TEXT,
          instruction TEXT NOT NULL,
          state TEXT NOT NULL,
          trigger_alert_id TEXT,
          evidence_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          due_at TEXT,
          FOREIGN KEY(employee_id) REFERENCES users(id),
          FOREIGN KEY(target_zone_id) REFERENCES zones(id),
          FOREIGN KEY(source_zone_id) REFERENCES zones(id),
          FOREIGN KEY(trigger_alert_id) REFERENCES alerts(id)
        );

        CREATE TABLE IF NOT EXISTS task_events (
          id TEXT PRIMARY KEY,
          task_id TEXT NOT NULL,
          state TEXT NOT NULL,
          actor_id TEXT,
          note TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY(task_id) REFERENCES tasks(id),
          FOREIGN KEY(actor_id) REFERENCES users(id)
        );
        """
    )
    seed_defaults(conn)
    conn.commit()


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt, digest = stored.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


def seed_defaults(conn: sqlite3.Connection) -> None:
    timestamp = now_iso()
    zones = [
        ("z1", "Entrance Lobby", "Entry/Exit", 15, 1),
        ("z2", "Aisle 1 - Snacks", "Aisle", 10, 1),
        ("z3", "Aisle 2 - Beverages", "Aisle", 10, 1),
        ("z4", "Aisle 3 - Household", "Aisle", 12, 1),
        ("z5", "Promo Display", "Display", 8, 0),
        ("z6", "Checkout Counter", "Checkout", 20, 2),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO zones(id, name, type, capacity, min_staff, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [(zone_id, name, kind, capacity, min_staff, timestamp, timestamp) for zone_id, name, kind, capacity, min_staff in zones],
    )
    cameras = [
        ("c1", "CAM 01 - ENTRANCE", "z1", "entrance", 1),
        ("c2", "CAM 02 - AISLE 1", "z2", "floor", 1),
        ("c3", "CAM 03 - CHECKOUT", "z6", "checkout", 1),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO cameras(id, name, zone_id, role, online, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [(camera_id, name, zone_id, role, online, timestamp, timestamp) for camera_id, name, zone_id, role, online in cameras],
    )
    seed_users = [
        (
            "u_manager",
            os.getenv("RETAILPULSE_BOOTSTRAP_MANAGER_NAME", "Demo Manager"),
            os.getenv("RETAILPULSE_BOOTSTRAP_MANAGER_EMAIL", "manager@retailpulse.local"),
            "Manager",
            os.getenv("RETAILPULSE_BOOTSTRAP_MANAGER_PASSWORD", "password123"),
        ),
        ("u_employee", "Demo Employee", "employee@retailpulse.local", "Employee", "password123"),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO users(id, name, email, role, password_hash, active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """,
        [(user_id, name, email.lower(), role, hash_password(password), timestamp, timestamp) for user_id, name, email, role, password in seed_users],
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO rosters(id, user_id, zone_id, shift, available, created_at, updated_at)
        VALUES ('r_employee', 'u_employee', 'z2', '9 AM - 1 PM', 1, ?, ?)
        """,
        (timestamp, timestamp),
    )
    defaults = {
        "thresholds": {
            "responseTimeMinutes": 2,
            "unattendedWaitMinutes": 3,
            "crowdDensityPercent": 85,
            "notifyMode": "any",
            "sustainedAlertSeconds": 60,
            "duplicateCooldownMinutes": 5,
            "ackDeadlineSeconds": 30,
            "arrivalDeadlineMinutes": 2,
            "dispatchPaused": False,
        },
        "privacy": {"retentionDays": 60},
    }
    for key, value in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings(key, value_json, updated_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), timestamp),
        )
    conn.execute(
        """
        INSERT OR IGNORE INTO alerts(id, category, severity, title, context, href, status, evidence_json, created_at)
        VALUES (
          'a_seed_unstaffed',
          'Unstaffed Zones',
          'high',
          'Aisle 2 - Beverages needs coverage',
          'The orchestrator has not received enough staffed-zone evidence for the sustained alert window.',
          '/employee-info',
          'active',
          '{"policy":"minimum-zone-staffing"}',
          ?
        )
        """,
        (timestamp,),
    )


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def get_setting(conn: sqlite3.Connection, key: str) -> Any:
    row = conn.execute("SELECT value_json FROM settings WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value_json"]) if row else None


def set_setting(conn: sqlite3.Connection, key: str, value: Any) -> Any:
    conn.execute(
        """
        INSERT INTO settings(key, value_json, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at
        """,
        (key, json.dumps(value), now_iso()),
    )
    conn.commit()
    return value


def public_user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "active": bool(row["active"]),
    }


def authenticate(conn: sqlite3.Connection, email: str, password: str, role: str | None = None) -> dict[str, Any]:
    user = conn.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (email.strip(),)).fetchone()
    if not user or not user["active"] or not verify_password(password, user["password_hash"]):
        raise ValueError("Invalid email or password")
    if role and user["role"] != role:
        raise ValueError(f"Account is not a {role}")
    return public_user(user)


def create_invitation(conn: sqlite3.Connection, email: str, role: str, created_by: str | None) -> dict[str, Any]:
    token = secrets.token_urlsafe(24)
    timestamp = now_iso()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    invitation_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO invitations(id, email, role, token, expires_at, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (invitation_id, email.lower(), role, token, expires_at, created_by, timestamp),
    )
    conn.commit()
    return {"id": invitation_id, "email": email.lower(), "role": role, "token": token, "expiresAt": expires_at}


def accept_invitation(conn: sqlite3.Connection, token: str, name: str, password: str) -> dict[str, Any]:
    invitation = conn.execute("SELECT * FROM invitations WHERE token = ?", (token,)).fetchone()
    if not invitation or invitation["accepted_at"]:
        raise ValueError("Invite token is invalid or already used")
    if datetime.fromisoformat(invitation["expires_at"]) < datetime.now(timezone.utc):
        raise ValueError("Invite token has expired")
    timestamp = now_iso()
    user_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO users(id, name, email, role, password_hash, active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (user_id, name.strip(), invitation["email"], invitation["role"], hash_password(password), timestamp, timestamp),
    )
    conn.execute("UPDATE invitations SET accepted_at = ? WHERE id = ?", (timestamp, invitation["id"]))
    conn.commit()
    return public_user(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())


def settings_snapshot(conn: sqlite3.Connection) -> dict[str, Any]:
    zones = [row_to_dict(row) for row in conn.execute("SELECT id, name, type, capacity, min_staff AS minStaff FROM zones ORDER BY name")]
    zone_names = {zone["id"]: zone["name"] for zone in zones}
    cameras = []
    for row in conn.execute("SELECT id, name, zone_id AS zoneId, role, source_type AS sourceType, online FROM cameras ORDER BY name"):
        item = row_to_dict(row)
        item["online"] = bool(item["online"])
        item["zone"] = zone_names.get(item["zoneId"], "")
        cameras.append(item)
    staff = []
    for row in conn.execute(
        """
        SELECT rosters.id, users.id AS userId, users.name AS label, zones.name AS zone, zones.id AS zoneId,
               rosters.shift, rosters.available
        FROM rosters
        JOIN users ON users.id = rosters.user_id
        LEFT JOIN zones ON zones.id = rosters.zone_id
        WHERE users.role = 'Employee' AND users.active = 1
        ORDER BY users.name
        """
    ):
        item = row_to_dict(row)
        item["available"] = bool(item["available"])
        staff.append(item)
    accounts = [public_user(row) for row in conn.execute("SELECT * FROM users ORDER BY role, name")]
    return {
        "zones": zones,
        "cameras": cameras,
        "staff": staff,
        "accounts": accounts,
        "thresholds": get_setting(conn, "thresholds"),
        "privacy": get_setting(conn, "privacy"),
    }
