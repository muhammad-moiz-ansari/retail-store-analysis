"""Registered map (MAP-2): calibration, cell lookup, per-cell observations and the dashboard payload."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from .spatial import LAYERS, cell_observations, cell_of, fit_homography, load_map, project, reprojection_error, spatial_payload

START = datetime(2026, 11, 3, 9, tzinfo=timezone.utc)
at = lambda seconds: START + timedelta(seconds=seconds)
SQUARE = lambda x0, x1: [[x0, 0], [x1, 0], [x1, 1], [x0, 1]]
IDENTITY = [[0, 0, 0, 0], [1, 0, 1, 0], [1, 1, 1, 1], [0, 1, 0, 1]]
# Camera c1 sees the left 60% of the map: cell "left" is observed, cell "right" is not.
MAP = {"map_version": "test-v1", "store_id": "store-1",
       "cells": [{"id": "left", "polygon": SQUARE(0, 0.5)}, {"id": "right", "polygon": SQUARE(0.5, 1)}],
       "cameras": {"c1": {"points": IDENTITY, "visible_polygon": SQUARE(0, 0.6)}}}

dwell = lambda role, start, end, track=1, cell="left": {"camera_id": "c1", "cell_id": cell, "track_id": track, "role": role,
                                                        "ts_start": at(start), "ts_end": at(end)}
health = lambda start, end, bad=0: {"camera_id": "c1", "ts_start": at(start), "ts_end": at(end), "frozen_or_dark": bad}


def payload(dwell_rows, health_rows, seconds, interactions=()):
    cells = spatial_payload(None, load_map(MAP), "r1", START, at(seconds), rows=(dwell_rows, health_rows, list(interactions)))["cells"]
    return {cell["id"]: cell for cell in cells}


def test_homography_recovers_the_calibration_and_rejects_degenerate_points() -> None:
    # A skewed view: the frame's corners land on a trapezium of the map.
    points = [[0, 0, 0.2, 0.1], [1, 0, 0.8, 0.1], [1, 1, 1.0, 0.9], [0, 1, 0.0, 0.9], [0.5, 0.5, 0.5, 0.42]]
    h = fit_homography(points[:4])
    assert reprojection_error(h, points[:4]) < 1e-9
    assert project(h, (0.5, 1)) == pytest.approx((0.5, 0.9))
    assert reprojection_error(fit_homography(points), points) < 0.05  # a fifth, slightly off point: least squares
    for bad in ([[0, 0, 0, 0], [0.5, 0.5, 0.5, 0.5], [1, 1, 1, 1], [0.2, 0.2, 0.2, 0.2]], IDENTITY[:3], [[0, 0, 0, float("nan")]] * 4):
        with pytest.raises(ValueError):
            fit_homography(bad)


def test_map_file_is_validated_and_points_outside_the_visible_area_have_no_cell() -> None:
    game_map = load_map(MAP)
    assert cell_of(game_map, "c1", (0.25, 0.5)) == "left"
    assert cell_of(game_map, "c1", (0.55, 0.5)) == "right"  # visible, and on the right cell
    assert cell_of(game_map, "c1", (0.8, 0.5)) is None      # on the map, but this camera does not see it
    for change in ({"cells": []}, {"cells": MAP["cells"] * 2}, {"cameras": {}}, {"map_version": " "},
                   {"cells": [{"id": "a", "polygon": [[0, 0], [2, 0], [1, 1]]}]},
                   {"cameras": {"c1": {"points": IDENTITY[:3], "visible_polygon": SQUARE(0, 1)}}}):
        with pytest.raises(ValueError):
            load_map({**MAP, **change})


def test_unseen_cells_are_unmapped_and_a_blocked_camera_is_never_no_one() -> None:
    cells = payload([dwell("customer", 0, 60, track=2)], [health(0, 60), health(60, 120, bad=1)], 120)
    assert (cells["right"]["category"], cells["right"]["quality"]) == (None, "unmapped")
    assert cells["right"]["values"] == dict.fromkeys(LAYERS)  # an unmapped cell carries no numbers at all
    # The second minute is blocked: the customer's absence there is unknown, not an empty cell.
    assert (cells["left"]["category"], cells["left"]["quality"]) == (None, "insufficient_coverage")
    assert cells["left"]["values"]["customer_presence"] == 60
    assert all(cell["category"] != "no_one" for cell in cells.values())


def test_categories_follow_roles_and_change_only_after_the_hold() -> None:
    both = [dwell("employee", 0, 120, track=1), dwell("customer", 0, 120, track=2)]
    interactions = [{"camera_id": "c1", "customer_track_id": 2, "verdict": "interaction", "ts_start": at(30)},
                    {"camera_id": "c1", "customer_track_id": 2, "verdict": "unverified", "ts_start": at(50)},
                    {"camera_id": "c1", "customer_track_id": 2, "verdict": "rejected", "ts_start": at(70)},
                    {"camera_id": "c1", "customer_track_id": 9, "verdict": "interaction", "ts_start": at(40)}]  # customer on no cell
    left = payload(both, [health(0, 120)], 120, interactions)["left"]
    assert (left["category"], left["quality"]) == ("customer_employee", "ok")
    assert left["values"] == {"customer_presence": 120, "employee_presence": 120, "confirmed_interactions": 1, "unverified_interactions": 1}

    walked_through = [dwell("customer", 0, 60, track=2)]
    assert payload(walked_through, [health(0, 120)], 120)["left"]["category"] == "customer"  # one empty window: not yet
    assert payload(walked_through, [health(0, 180)], 180)["left"]["category"] == "no_one"    # held for two windows
    assert payload([dwell("unknown", 0, 60)], [health(0, 60)], 60)["left"]["quality"] == "unknown_role"


def test_observations_split_the_window_and_clip_overlapping_tracks() -> None:
    rows = ([dwell("customer", 10, 50, track=2), dwell("customer", 30, 90, track=3)], [health(0, 150)], [])
    observations = [o for o in cell_observations(None, load_map(MAP), "r1", START, at(150), rows=rows) if o.cell_id == "left"]
    assert [(o.window.end - o.window.start).total_seconds() for o in observations] == [60, 60, 30]
    assert [o.customer_s for o in observations] == [50, 30, 0]  # two people at once are one presence, not two
    assert [o.observed_s for o in observations] == [60, 60, 30] and all(o.map_version == "test-v1" for o in observations)


def test_ingest_writes_replayable_cell_dwell_and_the_payload_reads_it(tmp_path, postgres_connection) -> None:
    from .ingest import ingest_run

    person = lambda track, role: {"track_id": track, "first_seen": 0.0, "last_seen": 59.0, "frames_observed": 60, "role": role,
                                  "employee_score": 0.5, "role_segments": [{"role": role, "from": 0.0, "to": 59.0, "frames": 60}]}
    seen = lambda track, role, x: {"track_id": track, "confidence": 0.9, "role": role, "bbox": [x - 5, 10, x + 5, 50]}
    # Both stand on the left cell for the first minute; the lens is covered for the second.
    detections = [{"frame": i, "timestamp": float(i), "interaction_active": False, "frozen_or_dark": i >= 60,
                   "people": [seen(1, "employee", 20), seen(2, "customer", 30), seen(3, "customer", 90)] if i < 60 else []} for i in range(120)]
    files = {".people.json": {"people": [person(1, "employee"), person(2, "customer"), person(3, "customer")], "frame_size": [100, 100]},
             ".interactions.json": [{"employee_track_id": 1, "customer_track_id": 2, "started_at": 10.0, "last_seen_at": 30.0, "verdict": "interaction"}],
             ".detections.json": detections}
    prefix = tmp_path / "interaction"
    for suffix, data in files.items():
        prefix.with_suffix(suffix).write_text(json.dumps(data))
    conn = postgres_connection
    ids = lambda: {r["event_id"] for r in conn.execute("SELECT event_id FROM cell_dwell")}
    first = ingest_run(conn, prefix, "r1", "c1", "z1", START, layout={"map_file": MAP})
    first_ids = ids()
    assert first["cell_dwell"] == 2 and len(first_ids) == 2  # track 3 is outside the visible area: no row
    assert ingest_run(conn, prefix, "r1", "c1", "z1", START, layout={"map_file": MAP})["cell_dwell"] == 2 and ids() == first_ids
    assert "cell_dwell" not in ingest_run(conn, prefix, "r2", "c1", "z1", START)  # no map configured: unchanged output
    with pytest.raises(ValueError, match="not registered"):
        ingest_run(conn, prefix, "r3", "c9", "z1", START, layout={"map_file": MAP})

    game_map = load_map(MAP)
    minute = {c["id"]: c for c in spatial_payload(conn, game_map, "r1", START, at(60))["cells"]}
    assert (minute["left"]["category"], minute["left"]["values"]["confirmed_interactions"]) == ("customer_employee", 1)
    both = {c["id"]: c for c in spatial_payload(conn, game_map, "r1", START, at(120))["cells"]}
    assert (both["left"]["category"], both["left"]["quality"]) == (None, "insufficient_coverage")
    assert both["right"]["quality"] == "unmapped"
