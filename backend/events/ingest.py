"""Load one CV run (<prefix>.people.json, .interactions.json, .detections.json) into event schema v1.

Idempotent on run_id: re-ingesting a run replaces its rows. Times in the CV files are seconds from the clip
start; `started_at` anchors them to UTC.

python -m backend.events.ingest backend/output/run1/interaction --run-id run1 --camera c2 --zone z2 \
    --start 2026-11-03T09:00:00+00:00
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")
DEFAULT_DB_PATH = Path(os.getenv("EVENTS_DB_PATH", Path(__file__).resolve().parents[1] / "events.sqlite3"))
TABLES = ("tracks", "role_decisions", "interactions", "zone_dwell", "footfall", "queue_samples",
          "unattended_episodes", "pipeline_health")
COMMON = ("event_id", "run_id", "store_id", "camera_id", "zone_id", "ts_start", "ts_end")
DEFAULT_UNATTENDED_S = 180.0  # store_core's default thresholds.unattendedWaitMinutes (3)


def connect(path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    return conn


def insert(conn: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    if rows:
        columns = list(rows[0])
        conn.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})",
                         [[row[c] for c in columns] for row in rows])


def delete_run(conn: sqlite3.Connection, run_id: str) -> None:
    for table in TABLES:
        conn.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))


def derive_unattended(conn: sqlite3.Connection, run_id: str, min_seconds: float) -> int:
    """A customer whose wait from first sighting to their first confirmed interaction (or exit, if never
    helped) is at least `min_seconds`. Track IDs are per camera, so customers match on (camera, track)."""
    first_help = {(row["camera_id"], row["customer_track_id"]): row["ts_start"] for row in conn.execute(
        "SELECT camera_id, customer_track_id, MIN(ts_start) AS ts_start FROM interactions WHERE run_id = ? "
        "GROUP BY camera_id, customer_track_id", (run_id,))}
    episodes = []
    for track in conn.execute("SELECT * FROM tracks WHERE run_id = ? AND role = 'customer'", (run_id,)):
        helped_at = first_help.get((track["camera_id"], track["track_id"]))
        wait_end = helped_at if helped_at and helped_at < track["ts_end"] else track["ts_end"]
        waited = (datetime.fromisoformat(wait_end) - datetime.fromisoformat(track["ts_start"])).total_seconds()
        if waited >= min_seconds:
            episodes.append({**{c: track[c] for c in COMMON}, "event_id": f"{run_id}:unattended:{track['camera_id']}:{track['track_id']}",
                             "ts_end": wait_end, "customer_track_id": track["track_id"], "waited_s": round(waited, 3),
                             "helped": int(wait_end == helped_at)})
    insert(conn, "unattended_episodes", episodes)
    return len(episodes)


def health_rows(detections: list[dict], at, base: dict) -> list[dict]:
    """Per-minute pipeline health from the per-frame detections (frame check pending: frozen_or_dark NULL)."""
    minutes: dict[int, list[dict]] = {}
    for frame in detections:
        minutes.setdefault(int(frame["timestamp"] // 60), []).append(frame)
    seen: set[int] = set()
    rows = []
    last = max(minutes, default=0)
    for minute, frames in sorted(minutes.items()):
        people = [p for f in frames for p in f["people"]]
        ids = {p["track_id"] for p in people}
        gap = frames[-1]["timestamp"] - frames[-2]["timestamp"] if len(frames) > 1 else 1.0
        span = 60.0 if minute < last else min(frames[-1]["timestamp"] + gap - minute * 60, 60.0)  # the clip may end mid-minute
        rows.append({**base, "event_id": f"{base['run_id']}:health:{base['camera_id']}:{minute}",
                     "ts_start": at(minute * 60), "ts_end": at(minute * 60 + span),
                     "fps": round(len(frames) / span, 3),
                     "mean_confidence": round(sum(p["confidence"] for p in people) / len(people), 4) if people else None,
                     "unknown_role_share": round(sum(p["role"] == "unknown" for p in people) / len(people), 4) if people else None,
                     "id_churn": len(ids - seen), "frozen_or_dark": None})
        seen |= ids
    return rows


def ingest_run(conn: sqlite3.Connection, prefix: Path | str, run_id: str, camera_id: str, zone_id: str,
               started_at: datetime, store_id: str = "store-1", unattended_after_s: float = DEFAULT_UNATTENDED_S) -> dict:
    """Replace `run_id`'s rows with this CV run. `zone_id` is the camera's zone until per-zone dwell (B4.2) exists."""
    prefix = Path(prefix)
    read = lambda suffix: json.loads(prefix.with_suffix(suffix).read_text(encoding="utf-8"))
    people, events, detections = read(".people.json")["people"], read(".interactions.json"), read(".detections.json")
    at = lambda seconds: (started_at + timedelta(seconds=seconds)).isoformat()
    base = {"run_id": run_id, "store_id": store_id, "camera_id": camera_id, "zone_id": zone_id}
    key = f"{run_id}:{{}}:{camera_id}:{{}}"
    tracks = [{**base, "event_id": key.format("track", p["track_id"]), "ts_start": at(p["first_seen"]), "ts_end": at(p["last_seen"]),
               "track_id": p["track_id"], "role": p["role"], "employee_score": p.get("employee_score"),
               "frames_observed": p["frames_observed"]} for p in people]
    roles = [{**base, "event_id": key.format("role", f"{p['track_id']}:{i}"), "ts_start": at(s["from"]), "ts_end": at(s["to"]),
              "track_id": p["track_id"], "role": s["role"], "frames": s["frames"]}
             for p in people for i, s in enumerate(p.get("role_segments", []))]
    interactions = [{**base, "event_id": key.format("interaction", f"{e['employee_track_id']}:{e['customer_track_id']}:{e['started_at']:.3f}"),
                     "ts_start": at(e["started_at"]), "ts_end": at(e["last_seen_at"]),
                     "employee_track_id": e["employee_track_id"], "customer_track_id": e["customer_track_id"],
                     "duration_s": round(e["last_seen_at"] - e["started_at"], 3), "verdict": e["verdict"]} for e in events]
    with conn:
        delete_run(conn, run_id)
        for table, rows in (("tracks", tracks), ("role_decisions", roles), ("interactions", interactions),
                            ("pipeline_health", health_rows(detections, at, base))):
            insert(conn, table, rows)
        unattended = derive_unattended(conn, run_id, unattended_after_s)
    return {"tracks": len(tracks), "role_decisions": len(roles), "interactions": len(interactions), "unattended_episodes": unattended}


def validate(conn: sqlite3.Connection) -> list[str]:
    """Contract check: every row of every table has the common fields filled. Returns the problems found."""
    problems = []
    for table in TABLES:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        problems += [f"{table} lacks column {c}" for c in COMMON if c not in columns]
        if columns.issuperset(COMMON):
            empty = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE " + " OR ".join(f"{c} IS NULL OR {c} = ''" for c in COMMON)).fetchone()[0]
            problems += [f"{table}: {empty} rows with an empty common field"] if empty else []
            bad = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE ts_end < ts_start").fetchone()[0]
            problems += [f"{table}: {bad} rows end before they start"] if bad else []
    return problems


def unattended_threshold() -> float:
    """N from the manager's settings (thresholds.unattendedWaitMinutes), else the store default."""
    try:
        from ..store_core import connect as store_connect, get_setting
        with store_connect() as store:
            return float((get_setting(store, "thresholds") or {}).get("unattendedWaitMinutes", 3)) * 60
    except Exception:  # settings DB unavailable (CI, fresh checkout): fall back to the seeded default
        return DEFAULT_UNATTENDED_S


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a CV run into the event store (schema v1).")
    parser.add_argument("prefix", type=Path, help="Output path given to the CLI, e.g. backend/output/run1/interaction")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--camera", required=True, help="camera_id, e.g. c2")
    parser.add_argument("--zone", required=True, help="zone_id the camera covers, e.g. z2")
    parser.add_argument("--start", required=True, type=datetime.fromisoformat, help="UTC time of the clip's first frame (ISO 8601)")
    parser.add_argument("--store", default="store-1")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--unattended-after", type=float, help="Seconds; default from settings thresholds")
    args = parser.parse_args()
    if args.start.tzinfo is None:
        parser.error("--start needs a UTC offset, e.g. 2026-11-03T09:00:00+00:00")
    with connect(args.db) as conn:
        counts = ingest_run(conn, args.prefix, args.run_id, args.camera, args.zone, args.start, args.store,
                            args.unattended_after if args.unattended_after is not None else unattended_threshold())
        problems = validate(conn)
    print(f"{args.run_id} -> {args.db}: {counts}")
    if problems:
        raise SystemExit("schema v1 violations:\n" + "\n".join(problems))


if __name__ == "__main__":
    main()
