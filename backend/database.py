"""PostgreSQL connections and explicit schema setup for RetailPulse."""

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row


class DatabaseNotConfigured(RuntimeError):
    pass


def connect(dsn: str | None = None) -> psycopg.Connection:
    dsn = dsn if dsn is not None else os.environ.get("DATABASE_URL")
    if not dsn:
        raise DatabaseNotConfigured("Set DATABASE_URL in the Python backend environment.")
    return psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5, prepare_threshold=None)


@contextmanager
def read_only(dsn: str | None = None):
    with connect(dsn) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        yield conn


ROOT = Path(__file__).resolve().parent
SCHEMAS = (ROOT / "store_schema.sql", ROOT / "events" / "schema.sql", ROOT / "interaction" / "schema.sql")


# Columns added after a table first shipped; CREATE TABLE IF NOT EXISTS leaves existing tables unchanged.
# Run before the schema files so their indexes on the new columns succeed.
UPGRADES = ("ALTER TABLE IF EXISTS orchestration_events ADD COLUMN IF NOT EXISTS dedupe_key TEXT",
            "ALTER TABLE IF EXISTS tasks ADD COLUMN IF NOT EXISTS ack_seconds DOUBLE PRECISION")


def initialize(conn, schemas=SCHEMAS):
    for statement in UPGRADES:
        conn.execute(statement)
    for schema in schemas:
        conn.execute(schema.read_text(encoding="utf-8"))


def bootstrap_manager(conn, *, email, password, name):
    from .store_core import hash_password, now_iso

    stamp = now_iso()
    conn.execute(
        """INSERT INTO users (id, name, email, role, password_hash, active, created_at, updated_at)
           VALUES (%s, %s, %s, 'Manager', %s, 1, %s, %s)""",
        (uuid4().hex, name, email.strip().lower(), hash_password(password), stamp, stamp),
    )


def main():
    parser = argparse.ArgumentParser(description="Initialize the RetailPulse PostgreSQL schema.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--seed-demo", action="store_true", help="Add the existing demo accounts and settings.")
    mode.add_argument("--bootstrap-manager", action="store_true", help="Create a manager from the bootstrap environment variables.")
    args = parser.parse_args()
    email = os.getenv("RETAILPULSE_BOOTSTRAP_MANAGER_EMAIL", "").strip()
    password = os.getenv("RETAILPULSE_BOOTSTRAP_MANAGER_PASSWORD", "")
    if args.bootstrap_manager and (not email or not password):
        parser.error("Set RETAILPULSE_BOOTSTRAP_MANAGER_EMAIL and RETAILPULSE_BOOTSTRAP_MANAGER_PASSWORD.")
    with connect() as conn:
        initialize(conn)
        if args.seed_demo:
            from .store_core import seed_defaults

            seed_defaults(conn)
        if args.bootstrap_manager:
            bootstrap_manager(conn, email=email, password=password,
                              name=os.getenv("RETAILPULSE_BOOTSTRAP_MANAGER_NAME", "Manager"))
    print("RetailPulse PostgreSQL schema initialized.")


if __name__ == "__main__":
    main()
