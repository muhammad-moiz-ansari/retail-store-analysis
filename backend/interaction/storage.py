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
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, store_id TEXT NOT NULL, status TEXT NOT NULL,
                    created_at TEXT NOT NULL, data TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS job_store ON jobs(store_id, created_at);
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

    def create_job(self, job):
        with self.connect() as db:
            db.execute("INSERT INTO jobs VALUES (?,?,?,?,?)", (job["id"], job["store_id"], "queued", now(), json.dumps(job)))
        return job

    @staticmethod
    def _job(row):
        if row is None:
            raise KeyError("Job not found")
        return {**json.loads(row["data"]), "status": row["status"], "created_at": row["created_at"]}

    def job(self, store_id, identifier):
        with self.connect() as db:
            return self._job(db.execute("SELECT * FROM jobs WHERE store_id=? AND id=?", (store_id, identifier)).fetchone())

    def jobs(self, store_id):
        with self.connect() as db:
            return [self._job(row) for row in db.execute("SELECT * FROM jobs WHERE store_id=? ORDER BY created_at DESC LIMIT 100", (store_id,))]

    def update_job(self, store_id, identifier, **changes):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._job(db.execute("SELECT * FROM jobs WHERE store_id=? AND id=?", (store_id, identifier)).fetchone())
            job.update(changes)
            db.execute("UPDATE jobs SET status=?, data=? WHERE id=?", (job["status"], json.dumps(job), identifier))
        return job

    def cancel(self, store_id, identifier):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._job(db.execute("SELECT * FROM jobs WHERE store_id=? AND id=?", (store_id, identifier)).fetchone())
            if job["status"] in ("queued", "running"):
                job["cancel_requested"] = True
                if job["status"] == "queued":
                    job["status"] = "cancelled"
                db.execute("UPDATE jobs SET status=?, data=? WHERE id=?", (job["status"], json.dumps(job), identifier))
        return job

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
            if row is None:
                return None
            db.execute("UPDATE jobs SET status='running' WHERE id=?", (row["id"],))
            return {**self._job(row), "status": "running"}

    def recover(self):
        with self.connect() as db:
            for row in db.execute("SELECT * FROM jobs WHERE status='running'").fetchall():
                job = self._job(row)
                job.update(error="Processing interrupted by service restart", finished_at=now())
                db.execute("UPDATE jobs SET status='interrupted', data=? WHERE id=?", (json.dumps(job), row["id"]))

    def activate(self, store_id, calibration):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT data FROM documents WHERE kind='calibration' AND store_id=? AND id='active'", (store_id,)).fetchone()
            version = json.loads(row[0])["version"] + 1 if row else 1
            calibration = {**calibration, "version": version, "created_at": now()}
            for identifier in (str(version), "active"):
                db.execute("INSERT OR REPLACE INTO documents VALUES ('calibration',?,?,?)", (store_id, identifier, json.dumps(calibration)))
        return calibration
