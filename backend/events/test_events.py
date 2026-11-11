"""Event store v1: ingestion, unattended derivation, fixture day, and the schema contract on real CV runs."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from .fixtures import RUN_ID, generate
from .ingest import ingest_run, validate

START = datetime(2026, 11, 3, 9, tzinfo=timezone.utc)


def write_run(prefix: Path) -> None:
    people = [{"track_id": 1, "first_seen": 0.0, "last_seen": 300.0, "frames_observed": 300, "role": "employee",
               "employee_score": 0.9, "role_segments": [{"role": "employee", "from": 0.0, "to": 300.0, "frames": 300}]},
              # waits 200 s, then helped
              {"track_id": 2, "first_seen": 10.0, "last_seen": 280.0, "frames_observed": 270, "role": "customer",
               "employee_score": 0.1, "role_segments": [{"role": "customer", "from": 10.0, "to": 280.0, "frames": 270}]},
              # helped after 20 s: not unattended
              {"track_id": 3, "first_seen": 30.0, "last_seen": 100.0, "frames_observed": 70, "role": "customer",
               "employee_score": 0.2, "role_segments": [{"role": "customer", "from": 30.0, "to": 100.0, "frames": 70}]},
              # never helped, leaves after 190 s; an ID swap shows as two role segments
              {"track_id": 4, "first_seen": 60.0, "last_seen": 250.0, "frames_observed": 190, "role": "customer",
               "employee_score": 0.3, "role_segments": [{"role": "employee", "from": 60.0, "to": 70.0, "frames": 10},
                                                        {"role": "customer", "from": 70.0, "to": 250.0, "frames": 180}]}]
    interactions = [{"employee_track_id": 1, "customer_track_id": 2, "started_at": 210.0, "last_seen_at": 240.0, "verdict": "interaction"},
                    {"employee_track_id": 1, "customer_track_id": 3, "started_at": 50.0, "last_seen_at": 80.0, "verdict": "unverified"}]
    detections = [{"frame": i, "timestamp": i * 1.0, "interaction_active": False, "frozen_or_dark": i >= 80,
                   "people": [{"track_id": 1 if i < 60 else 4, "confidence": 0.8, "role": "employee" if i < 90 else "unknown"}]}
                  for i in range(120)]
    for suffix, data in ((".people.json", {"people": people}), (".interactions.json", interactions), (".detections.json", detections)):
        prefix.with_suffix(suffix).write_text(json.dumps(data))


def test_ingest_is_idempotent_and_derives_unattended(tmp_path, postgres_connection) -> None:
    prefix = tmp_path / "interaction"
    write_run(prefix)
    conn = postgres_connection
    for _ in range(2):  # re-ingesting the same run replaces it
        counts = ingest_run(conn, prefix, "r1", "c2", "z2", START, unattended_after_s=180)
    assert counts == {"tracks": 4, "role_decisions": 5, "interactions": 2, "zone_dwell": 4, "footfall": 0, "queue_samples": 0, "heatmaps": 0, "unattended_episodes": 2}
    assert conn.execute("SELECT COUNT(*) FROM tracks").fetchone()["count"] == 4
    episodes = {row["customer_track_id"]: (row["waited_s"], row["helped"]) for row in conn.execute("SELECT * FROM unattended_episodes")}
    assert episodes == {2: (200.0, 1), 4: (190.0, 0)}
    health = conn.execute("SELECT * FROM pipeline_health ORDER BY ts_start").fetchall()
    assert [(h["fps"], h["id_churn"], h["unknown_role_share"]) for h in health] == [(1.0, 1, 0.0), (1.0, 1, 0.5)]
    assert health[0]["ts_start"] == START
    assert [h["frozen_or_dark"] for h in health] == [0, 1]  # 40 of the second minute's 60 frames flagged
    assert validate(conn) == []


def test_fixture_day_is_valid_and_has_the_planted_patterns(postgres_connection) -> None:
    conn = postgres_connection
    first = generate(conn)
    assert generate(conn) == first  # seeded and idempotent
    assert validate(conn) == []
    one = lambda sql: next(iter(conn.execute(sql).fetchone().values()))
    rush = one("SELECT COUNT(*) FROM footfall WHERE direction = 'in' AND extract(hour FROM ts_start AT TIME ZONE 'UTC') IN (17, 18)") / 2
    calm = one("SELECT COUNT(*) FROM footfall WHERE direction = 'in' AND extract(hour FROM ts_start AT TIME ZONE 'UTC') IN (10, 11)") / 2
    assert rush > 2 * calm
    unattended = {r["zone_id"]: r["count"] for r in conn.execute("SELECT zone_id, COUNT(*) FROM unattended_episodes GROUP BY zone_id")}
    assert unattended["z3"] > 2 * max(unattended.get("z2", 0), unattended.get("z4", 0))
    assert one("SELECT COUNT(*) FROM pipeline_health WHERE camera_id = 'c2' AND frozen_or_dark = 1") == 40
    assert one("SELECT COUNT(*) FROM tracks WHERE camera_id = 'c2' AND role = 'customer' "
               "AND ts_start >= '2026-11-03T14:00Z' AND ts_start < '2026-11-03T14:40Z'") == 0
    assert one(f"SELECT COUNT(DISTINCT run_id) FROM tracks") == 1 and one("SELECT run_id FROM tracks LIMIT 1") == RUN_ID


RUNS = [p for p in sorted(Path(__file__).resolve().parents[1].glob("output/**/*.people.json"))
        if p.with_name(p.name.replace(".people.", ".interactions.")).exists()]  # older runs predate the current file set


@pytest.mark.parametrize("people", RUNS[:5], ids=lambda p: str(p.parent.name))
def test_real_cv_runs_meet_schema_v1(tmp_path, postgres_connection, people) -> None:
    """Contract: whatever the CLI wrote locally must load and fill every common field (skipped without runs)."""
    conn = postgres_connection
    ingest_run(conn, people.with_name(people.name.removesuffix(".people.json")), "real", "c2", "z2", START)
    assert validate(conn) == []


def test_zone_segments_ignore_border_flicker() -> None:
    from .zones import zone_segments

    samples = [(0, "z2"), (1, "z2"), (1.5, "z3"), (2, "z2"), (3, "z3"), (3.5, "z3"), (4.5, "z3"), (5, "z2")]
    assert zone_segments(samples, 1.0) == [("z2", 0, 3), ("z3", 3, 4.5)]  # the 0.5 s blip and the final sample don't count


def test_ingest_splits_tracks_into_floor_zones_and_hourly_heatmaps(tmp_path, postgres_connection) -> None:
    prefix = tmp_path / "run"
    # Track 1 (customer) walks from the left half (z2) into the right half (z3) at 10 s; track 2 (employee) stays right.
    detections = [{"frame": i, "timestamp": float(i), "people": [
        {"track_id": 1, "bbox": [10 + 18 * i, 0, 30 + 18 * i, 100], "confidence": 0.9, "role": "customer"},
        {"track_id": 2, "bbox": [300, 0, 320, 100], "confidence": 0.9, "role": "employee"}]} for i in range(20)]
    people = [{"track_id": 1, "first_seen": 0.0, "last_seen": 19.0, "frames_observed": 20, "role": "customer"},
              {"track_id": 2, "first_seen": 0.0, "last_seen": 19.0, "frames_observed": 20, "role": "employee"}]
    interactions = [{"employee_track_id": 2, "customer_track_id": 1, "started_at": 15.0, "last_seen_at": 19.0, "verdict": "interaction"}]
    for suffix, data in ((".people.json", {"frame_size": [400, 100], "people": people}),
                         (".interactions.json", interactions), (".detections.json", detections)):
        prefix.with_suffix(suffix).write_text(json.dumps(data))
    conn = postgres_connection
    layout = {"floor_zones": {"z2": [[0, 0], [0.5, 0], [0.5, 1], [0, 1]], "z3": [[0.5, 0], [1, 0], [1, 1], [0.5, 1]]},
              "heatmap_grid": (4, 2)}
    started = datetime(2026, 11, 3, 9, 59, 50, tzinfo=timezone.utc)  # crosses 10:00, so two hourly heatmaps
    counts = ingest_run(conn, prefix, "r", "c2", "z1", started, layout={**layout, "entrance_line": 0.5})
    assert (counts["zone_dwell"], counts["heatmaps"], counts["footfall"]) == (3, 2, 1)
    assert conn.execute("SELECT track_id, direction, ts_start FROM footfall").fetchone() == {"track_id": 1, "direction": "in", "ts_start": START.replace(hour=10)}
    dwell = [(r["track_id"], r["zone_id"], r["dwell_s"]) for r in conn.execute("SELECT * FROM zone_dwell ORDER BY track_id, ts_start")]
    assert dwell == [(1, "z2", 10.0), (1, "z3", 9.0), (2, "z3", 19.0)]
    assert conn.execute("SELECT zone_id FROM interactions").fetchone()["zone_id"] == "z3"
    assert {r["track_id"]: r["zone_id"] for r in conn.execute("SELECT track_id, zone_id FROM tracks")} == {1: "z2", 2: "z3"}
    maps = conn.execute("SELECT ts_start, cells FROM heatmaps ORDER BY ts_start").fetchall()
    assert maps[0]["ts_start"] == START and sum(map(sum, json.loads(maps[0]["cells"]))) == 20  # 10 frames x 2
    assert validate(conn) == []


def test_entrance_line_counts_net_crossings_once() -> None:
    from .zones import line_crossing

    walk_in = [(0, 0.2), (1, 0.45), (2, 0.55), (3, 0.48), (4, 0.6), (5, 0.9)]  # jitters on the line at 0.5
    assert line_crossing(walk_in, 0.5, "right") == ("in", 4)
    assert line_crossing(list(reversed([(5 - t, x) for t, x in walk_in])), 0.5, "right")[0] == "out"
    assert line_crossing([(0, 0.2), (1, 0.7), (2, 0.3)], 0.5, "right") is None  # came back: browsing at the door
    assert line_crossing(walk_in, 0.5, "left") == ("out", 4)


def test_queue_counts_customers_in_the_polygon_and_estimates_wait(tmp_path, postgres_connection) -> None:
    from .zones import queue_lengths

    box = lambda x: [x, 0, x + 10, 100]  # feet at the bottom edge, x centre = x + 5 of a 100 px wide frame
    detections = [{"timestamp": 0.0, "people": [{"bbox": box(0), "role": "customer"}, {"bbox": box(10), "role": "employee"}]},
                  {"timestamp": 4.0, "people": [{"bbox": box(0), "role": "customer"}, {"bbox": box(20), "role": "customer"},
                                                {"bbox": box(80), "role": "customer"}]},
                  {"timestamp": 11.0, "people": []}]
    queue = [[0, 0], [0.5, 0], [0.5, 1], [0, 1]]
    assert queue_lengths(detections, (100, 100), queue, 5.0) == [(0.0, 1), (5.0, 2), (10.0, 2)]  # 10 s still sees the 4 s frame
    prefix = tmp_path / "till"
    for suffix, data in ((".people.json", {"frame_size": [100, 100], "people": []}),
                         (".interactions.json", [{"employee_track_id": 1, "customer_track_id": 2, "started_at": 0.0,
                                                  "last_seen_at": 60.0, "verdict": "interaction"}]),
                         (".detections.json", [{**d, "people": [{**p, "track_id": i, "confidence": 0.9} for i, p in enumerate(d["people"])]}
                                               for d in detections])):
        prefix.with_suffix(suffix).write_text(json.dumps(data))
    conn = postgres_connection
    ingest_run(conn, prefix, "t", "c3", "z6", START, layout={"queue_zone": queue})
    assert [tuple(r.values()) for r in conn.execute("SELECT queue_length, est_wait_s FROM queue_samples ORDER BY ts_start")] == [(1, 60.0), (2, 120.0), (2, 120.0)]
