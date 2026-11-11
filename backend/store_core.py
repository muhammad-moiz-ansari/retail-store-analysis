from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from psycopg import Connection

from .database import connect
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def seed_defaults(conn: Connection) -> None:
    timestamp = now_iso()
    zones = [
        ("z1", "Entrance Lobby", "Entry/Exit", 15, 1),
        ("z2", "Aisle 1 - Snacks", "Aisle", 10, 1),
        ("z3", "Aisle 2 - Beverages", "Aisle", 10, 1),
        ("z4", "Aisle 3 - Household", "Aisle", 12, 1),
        ("z5", "Promo Display", "Display", 8, 0),
        ("z6", "Checkout Counter", "Checkout", 20, 2),
    ]
    conn.cursor().executemany(
        """
        INSERT INTO zones(id, name, type, capacity, min_staff, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
        """,
        [(zone_id, name, kind, capacity, min_staff, timestamp, timestamp) for zone_id, name, kind, capacity, min_staff in zones],
    )
    cameras = [
        ("c1", "CAM 01 - ENTRANCE", "z1", "entrance", 1),
        ("c2", "CAM 02 - AISLE 1", "z2", "floor", 1),
        ("c3", "CAM 03 - CHECKOUT", "z6", "checkout", 1),
    ]
    conn.cursor().executemany(
        """
        INSERT INTO cameras(id, name, zone_id, role, online, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
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
    conn.cursor().executemany(
        """
        INSERT INTO users(id, name, email, role, password_hash, active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, 1, %s, %s) ON CONFLICT DO NOTHING
        """,
        [(user_id, name, email.lower(), role, hash_password(password), timestamp, timestamp) for user_id, name, email, role, password in seed_users],
    )
    conn.execute(
        """
        INSERT INTO rosters(id, user_id, zone_id, shift, available, created_at, updated_at)
        VALUES ('r_employee', 'u_employee', 'z2', '9 AM - 1 PM', 1, %s, %s) ON CONFLICT DO NOTHING
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
            "INSERT INTO settings(key, value_json, updated_at) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (key, json.dumps(value), timestamp),
        )
    conn.execute(
        """
        INSERT INTO alerts(id, category, severity, title, context, href, status, evidence_json, created_at)
        VALUES (
          'a_seed_unstaffed',
          'Unstaffed Zones',
          'high',
          'Aisle 2 - Beverages needs coverage',
          'The orchestrator has not received enough staffed-zone evidence for the sustained alert window.',
          '/employee-info',
          'active',
          '{"policy":"minimum-zone-staffing"}',
          %s
        ) ON CONFLICT DO NOTHING
        """,
        (timestamp,),
    )


def row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return dict(row)


def get_setting(conn: Connection, key: str) -> Any:
    row = conn.execute("SELECT value_json FROM settings WHERE key = %s", (key,)).fetchone()
    return json.loads(row["value_json"]) if row else None


def set_setting(conn: Connection, key: str, value: Any) -> Any:
    conn.execute(
        """
        INSERT INTO settings(key, value_json, updated_at) VALUES (%s, %s, %s)
        ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at
        """,
        (key, json.dumps(value), now_iso()),
    )
    conn.commit()
    return value


def public_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "active": bool(row["active"]),
    }


def authenticate(conn: Connection, email: str, password: str, role: str | None = None) -> dict[str, Any]:
    user = conn.execute("SELECT * FROM users WHERE lower(email) = lower(%s)", (email.strip(),)).fetchone()
    if not user or not user["active"] or not verify_password(password, user["password_hash"]):
        raise ValueError("Invalid email or password")
    if role and user["role"] != role:
        raise ValueError(f"Account is not a {role}")
    return public_user(user)


def create_invitation(conn: Connection, email: str, role: str, created_by: str | None) -> dict[str, Any]:
    token = secrets.token_urlsafe(24)
    timestamp = now_iso()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    invitation_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO invitations(id, email, role, token, expires_at, created_by, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (invitation_id, email.lower(), role, token, expires_at, created_by, timestamp),
    )
    conn.commit()
    return {"id": invitation_id, "email": email.lower(), "role": role, "token": token, "expiresAt": expires_at}


def accept_invitation(conn: Connection, token: str, name: str, password: str) -> dict[str, Any]:
    invitation = conn.execute("SELECT * FROM invitations WHERE token = %s FOR UPDATE", (token,)).fetchone()
    if not invitation or invitation["accepted_at"]:
        raise ValueError("Invite token is invalid or already used")
    if datetime.fromisoformat(invitation["expires_at"]) < datetime.now(timezone.utc):
        raise ValueError("Invite token has expired")
    timestamp = now_iso()
    user_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO users(id, name, email, role, password_hash, active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, 1, %s, %s)
        """,
        (user_id, name.strip(), invitation["email"], invitation["role"], hash_password(password), timestamp, timestamp),
    )
    conn.execute("UPDATE invitations SET accepted_at = %s WHERE id = %s", (timestamp, invitation["id"]))
    conn.commit()
    return public_user(conn.execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone())


def settings_snapshot(conn: Connection) -> dict[str, Any]:
    zones = [row_to_dict(row) for row in conn.execute('SELECT id, name, type, capacity, min_staff AS "minStaff" FROM zones ORDER BY name')]
    zone_names = {zone["id"]: zone["name"] for zone in zones}
    cameras = []
    for row in conn.execute('SELECT id, name, zone_id AS "zoneId", role, source_type AS "sourceType", online FROM cameras ORDER BY name'):
        item = row_to_dict(row)
        item["online"] = bool(item["online"])
        item["zone"] = zone_names.get(item["zoneId"], "")
        cameras.append(item)
    staff = []
    for row in conn.execute(
        """
        SELECT rosters.id, users.id AS "userId", users.name AS label, zones.name AS zone, zones.id AS "zoneId",
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
