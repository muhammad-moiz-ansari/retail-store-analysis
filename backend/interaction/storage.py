"""Durable local store. Each operation owns its connection and transaction."""

import json
from datetime import datetime, timezone
from backend.database import connect


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, dsn=None):
        self.dsn = dsn

    def connect(self):
        return connect(self.dsn)

    def put(self, kind, store_id, identifier, data):
        with self.connect() as db:
            db.execute("INSERT INTO documents (kind, store_id, id, data) VALUES (%s,%s,%s,%s) ON CONFLICT(kind,store_id,id) DO UPDATE SET data=excluded.data",
                       (kind, store_id, identifier, json.dumps(data, allow_nan=False)))
        return data

    def get(self, kind, store_id, identifier):
        with self.connect() as db:
            row = db.execute("SELECT data FROM documents WHERE kind=%s AND store_id=%s AND id=%s", (kind, store_id, identifier)).fetchone()
        if not row:
            raise KeyError(identifier)
        return json.loads(row["data"])

    def list(self, kind, store_id):
        with self.connect() as db:
            return [json.loads(row["data"]) for row in db.execute("SELECT data FROM documents WHERE kind=%s AND store_id=%s ORDER BY ordinal DESC", (kind, store_id))]
