"""Registered store map (MAP-2): camera frame -> map position -> cell, and per-cell observations for MAP-3.

Map file (JSON), all coordinates normalised to 0..1:

    {"map_version": "store-1-v1", "store_id": "store-1",
     "cells": [{"id": "a1", "polygon": [[0, 0], [0.5, 0], [0.5, 0.5], [0, 0.5]]}, ...],
     "cameras": {"c1": {"points": [[frame_x, frame_y, map_x, map_y], ...],          # 4 or more matching points
                        "visible_polygon": [[0, 0], [1, 0], [1, 1], [0, 1]]}}}       # on the map

A foot point is projected with the camera's homography and dropped when it lands outside that camera's visible
polygon or outside every cell. Position on the supplied map only: no physical distance is implied.
A cell that no camera sees is `unmapped`; a cell whose cameras were blocked is `insufficient_coverage`, never `no_one`.

python -m backend.events.spatial fit map.json      # reprojection error per camera, to check the picked points
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from ..interaction.core import contains

MAX_CELLS, MAX_WINDOWS = 500, 1440  # the dashboard's cell limit; a day of one-minute windows
LAYERS = ("customer_presence", "employee_presence", "confirmed_interactions", "unverified_interactions")
NO_CELL = ""  # a sample that is on no cell; never written


def _identifier(value, what: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > 200:
        raise ValueError(f"{what} must be a non-empty identifier of at most 200 characters")
    return value


def _polygon(points, what: str) -> list[tuple[float, float]]:
    if not isinstance(points, list) or not 3 <= len(points) <= 64:
        raise ValueError(f"{what} needs 3 to 64 points")
    polygon = []
    for point in points:
        if not isinstance(point, (list, tuple)) or len(point) != 2 or not all(
                isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1 for v in point):
            raise ValueError(f"{what} points must be [x, y] pairs within 0..1")
        polygon.append((float(point[0]), float(point[1])))
    return polygon


def fit_homography(points: list) -> np.ndarray:
    """3x3 frame -> map transform from 4 or more [frame_x, frame_y, map_x, map_y] pairs (direct linear transform)."""
    pairs = np.asarray(points, dtype=float)
    if pairs.ndim != 2 or pairs.shape[1] != 4 or len(pairs) < 4 or not np.isfinite(pairs).all():
        raise ValueError("A camera needs 4 or more finite [frame_x, frame_y, map_x, map_y] points")
    rows = []
    for x, y, u, v in pairs:
        rows += [[-x, -y, -1, 0, 0, 0, u * x, u * y, u], [0, 0, 0, -x, -y, -1, v * x, v * y, v]]
    _, singular, vt = np.linalg.svd(np.asarray(rows))
    h = vt[-1].reshape(3, 3)
    if singular[7] < 1e-9 or abs(h[2, 2]) < 1e-12:
        raise ValueError("Calibration points are degenerate (three on one line, or repeated points)")
    return h / h[2, 2]


def project(h: np.ndarray, point: tuple[float, float]) -> tuple[float, float] | None:
    x, y, w = h @ np.array([point[0], point[1], 1.0])
    return None if abs(w) < 1e-12 else (float(x / w), float(y / w))


def reprojection_error(h: np.ndarray, points: list) -> float:
    """Largest distance, in map units, between a calibration point's map position and its projection."""
    errors = []
    for x, y, u, v in points:
        got = project(h, (x, y))
        errors.append(float("inf") if got is None else ((got[0] - u) ** 2 + (got[1] - v) ** 2) ** 0.5)
    return max(errors)


def load_map(source) -> dict:
    """Validate a map file (path or already-parsed dict). Returns cells as {id: polygon} and a fitted homography per camera."""
    data = source if isinstance(source, dict) else json.loads(Path(source).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cells"), list) or not isinstance(data.get("cameras"), dict):
        raise ValueError("A map needs map_version, store_id, a cells list and a cameras object")
    if not 1 <= len(data["cells"]) <= MAX_CELLS:
        raise ValueError(f"A map needs 1 to {MAX_CELLS} cells")
    cells = {}
    for cell in data["cells"]:
        cell_id = _identifier(cell.get("id") if isinstance(cell, dict) else None, "Cell id")
        if cell_id in cells:
            raise ValueError(f"Duplicate cell id {cell_id!r}")
        cells[cell_id] = _polygon(cell.get("polygon"), f"Cell {cell_id!r}")
    cameras = {}
    for camera_id, camera in data["cameras"].items():
        _identifier(camera_id, "Camera id")
        if not isinstance(camera, dict):
            raise ValueError(f"Camera {camera_id!r} needs points and visible_polygon")
        cameras[camera_id] = {"points": camera.get("points"), "h": fit_homography(camera.get("points")),
                              "visible": _polygon(camera.get("visible_polygon"), f"Camera {camera_id!r} visible_polygon")}
    if not cameras:
        raise ValueError("A map needs at least one camera")
    return {"map_version": _identifier(data.get("map_version"), "map_version"), "store_id": _identifier(data.get("store_id"), "store_id"),
            "cells": cells, "cameras": cameras}


def cell_of(game_map: dict, camera_id: str, frame_point: tuple[float, float]) -> str | None:
    """The cell under a normalised frame point, or None when it is outside the camera's visible area or every cell."""
    camera = game_map["cameras"][camera_id]
    point = project(camera["h"], frame_point)
    if point is None or not contains(point, camera["visible"]):
        return None
    return next((cell_id for cell_id, polygon in game_map["cells"].items() if contains(point, polygon)), None)


def cameras_seeing(game_map: dict, camera_ids=None) -> dict[str, list[str]]:
    """{cell: cameras whose visible polygon holds the cell's centre}. An empty list means the cell is unmapped."""
    seen = {}
    for cell_id, polygon in game_map["cells"].items():
        centre = (sum(p[0] for p in polygon) / len(polygon), sum(p[1] for p in polygon) / len(polygon))
        seen[cell_id] = [c for c, camera in game_map["cameras"].items()
                         if (camera_ids is None or c in camera_ids) and contains(centre, camera["visible"])]
    return seen


def covered(intervals: list[tuple[datetime, datetime]], start: datetime, end: datetime) -> float:
    """Seconds of [start, end) covered by the union of the intervals."""
    total, cursor = 0.0, start
    for a, b in sorted((max(a, start), min(b, end)) for a, b in intervals if a < end and b > start):
        if b > cursor:
            total += (b - max(a, cursor)).total_seconds()
            cursor = b
    return total


def _rows(conn, game_map: dict, run_id: str, store_id: str, start: datetime, end: datetime, camera_ids) -> tuple[list, list, list]:
    cameras = list(game_map["cameras"] if camera_ids is None else [c for c in game_map["cameras"] if c in camera_ids])
    args = (run_id, store_id, cameras, end, start)
    where = "run_id = %s AND store_id = %s AND camera_id = ANY(%s) AND ts_start < %s AND ts_end >= %s"
    dwell = conn.execute(f"SELECT camera_id, cell_id, track_id, role, ts_start, ts_end FROM cell_dwell WHERE {where} AND map_version = %s",
                         (*args, game_map["map_version"])).fetchall()
    health = conn.execute(f"SELECT camera_id, ts_start, ts_end, frozen_or_dark FROM pipeline_health WHERE {where}", args).fetchall()
    interactions = conn.execute(f"SELECT camera_id, customer_track_id, verdict, ts_start FROM interactions WHERE {where}", args).fetchall()
    return dwell, health, interactions


def cell_observations(conn, game_map: dict, run_id: str, start: datetime, end: datetime, *, store_id: str | None = None,
                      camera_ids=None, window_s: float = 60.0, rows=None) -> list:
    """One CellObservation per cell per window, in time order. Role seconds are the union of that role's time on the
    cell; observed seconds are the union of healthy pipeline_health time of the cameras that see the cell."""
    from ..agents.business.occupancy import CellObservation

    if end <= start:
        raise ValueError("The window must end after it starts")
    window_s = max(window_s, (end - start).total_seconds() / MAX_WINDOWS)
    dwell, health, _ = rows or _rows(conn, game_map, run_id, store_id or game_map["store_id"], start, end, camera_ids)
    seeing = cameras_seeing(game_map, camera_ids)
    healthy: dict[str, list] = {}
    for row in health:
        if row["frozen_or_dark"] != 1:
            healthy.setdefault(row["camera_id"], []).append((row["ts_start"], row["ts_end"]))
    present: dict[tuple[str, str], list] = {}
    for row in dwell:
        present.setdefault((row["cell_id"], row["role"]), []).append((row["ts_start"], row["ts_end"]))
    observations, a = [], start
    while a < end:
        b = min(a + timedelta(seconds=window_s), end)
        span = (b - a).total_seconds()
        seconds = lambda intervals: min(covered(intervals, a, b), span)
        for cell_id, cameras in seeing.items():
            role = lambda name: seconds(present.get((cell_id, name), []))
            observations.append(CellObservation(
                cell_id=cell_id, window={"start": a, "end": b}, mapped=bool(cameras), map_version=game_map["map_version"],
                observed_s=seconds([i for c in cameras for i in healthy.get(c, [])]),
                customer_s=role("customer"), employee_s=role("employee"), unknown_role_s=role("unknown")))
        a = b
    return observations


def spatial_payload(conn, game_map: dict, run_id: str, start: datetime, end: datetime, *, store_id: str | None = None,
                    camera_ids=None, window_s: float = 60.0, policy=None, rows=None) -> dict:
    """The dashboard's map payload: each cell's category at the end of [start, end) after hysteresis, plus separate
    layer totals over the whole window. An unmapped cell carries no values; masked cells carry no category."""
    from ..agents.business.occupancy import OccupancyPolicy, OccupancyTracker

    rows = rows or _rows(conn, game_map, run_id, store_id or game_map["store_id"], start, end, camera_ids)
    dwell, _, interactions = rows
    tracker, latest = OccupancyTracker(policy or OccupancyPolicy()), {}
    for observation in cell_observations(conn, game_map, run_id, start, end, camera_ids=camera_ids, window_s=window_s, rows=rows):
        latest[observation.cell_id] = tracker.update(observation)
    presence: dict[tuple[str, str], list] = {}
    for row in dwell:
        presence.setdefault((row["cell_id"], row["role"]), []).append((row["ts_start"], row["ts_end"]))
    counts: dict[tuple[str, str], int] = {}
    for event in interactions:  # counted on the cell the customer stood on when the interaction began
        cell = next((d["cell_id"] for d in dwell if d["camera_id"] == event["camera_id"] and d["track_id"] == event["customer_track_id"]
                     and d["ts_start"] <= event["ts_start"] <= d["ts_end"]), None)
        layer = {"interaction": "confirmed_interactions", "unverified": "unverified_interactions"}.get(event["verdict"])
        if cell and layer:
            counts[cell, layer] = counts.get((cell, layer), 0) + 1
    cells = []
    for cell_id, polygon in game_map["cells"].items():
        state = latest[cell_id]
        values = dict.fromkeys(LAYERS) if state.quality == "unmapped" else {
            "customer_presence": round(covered(presence.get((cell_id, "customer"), []), start, end), 1),
            "employee_presence": round(covered(presence.get((cell_id, "employee"), []), start, end), 1),
            "confirmed_interactions": counts.get((cell_id, "confirmed_interactions"), 0),
            "unverified_interactions": counts.get((cell_id, "unverified_interactions"), 0)}
        cells.append({"id": cell_id, "polygon": [list(p) for p in polygon], "category": state.category,
                      "quality": state.quality, "values": values})
    return {"version": game_map["map_version"], "window": {"start": start.isoformat(), "end": end.isoformat()},
            "policyVersion": tracker.policy.version, "cells": cells}


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] != "fit":
        raise SystemExit("usage: python -m backend.events.spatial fit <map.json>")
    game_map = load_map(sys.argv[2])
    seeing = cameras_seeing(game_map)
    print(f"{game_map['map_version']} ({game_map['store_id']}): {len(game_map['cells'])} cells, "
          f"{sum(not c for c in seeing.values())} unmapped")
    for camera_id, camera in game_map["cameras"].items():
        print(f"  {camera_id}: {len(camera['points'])} points, largest reprojection error {reprojection_error(camera['h'], camera['points']):.4f} "
              f"of the map's width, sees {sum(camera_id in c for c in seeing.values())} cells")


if __name__ == "__main__":
    main()
