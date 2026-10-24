"""Durable local store. Each operation owns its connection and transaction."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("INTERACTION_DB_PATH", Path(__file__).resolve().parents[1] / "interaction.sqlite3"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    kind TEXT NOT NULL, store_id TEXT NOT NULL, id TEXT NOT NULL,
                    data TEXT NOT NULL, PRIMARY KEY(kind, store_id, id)
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def put(self, kind, store_id, identifier, data):
        with self.connect() as db:
            db.execute("INSERT INTO documents VALUES (?,?,?,?) ON CONFLICT(kind,store_id,id) DO UPDATE SET data=excluded.data",
                       (kind, store_id, identifier, json.dumps(data, allow_nan=False)))
        return data

    def get(self, kind, store_id, identifier):
        with self.connect() as db:
            row = db.execute("SELECT data FROM documents WHERE kind=? AND store_id=? AND id=?", (kind, store_id, identifier)).fetchone()
        if not row:
            raise KeyError(identifier)
        return json.loads(row["data"])

    def list(self, kind, store_id):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT data FROM documents WHERE kind=? AND store_id=? ORDER BY rowid DESC", (kind, store_id))]
