"""Per-track zone dwell and per-hour heatmaps from a run's detections (B4.2).

A person's position is their foot point (bottom centre of the box), normalised to the frame, so one camera config
works at any resolution. Floor zones are normalised polygons keyed by store zone_id (`floor_zones` in the camera's
--config file); a foot point outside every polygon counts toward the camera's own zone.
"""

from __future__ import annotations

from ..handoff_core import boundary_side, crossing_direction
from ..interaction.core import contains


def foot_point(bbox: list[float], frame_size: tuple[int, int]) -> tuple[float, float]:
    # Kept just inside the frame: feet cut off at the bottom edge must still fall in polygons drawn to that edge.
    inside = lambda v: min(max(v, 0.0), 1.0 - 1e-6)
    return (inside((bbox[0] + bbox[2]) / 2 / frame_size[0]), inside(bbox[3] / frame_size[1]))


def zone_of(point: tuple[float, float], zones: dict[str, list], default: str) -> str:
    return next((zone_id for zone_id, polygon in zones.items() if contains(point, [tuple(p) for p in polygon])), default)


def zone_segments(observations: list[tuple[float, str]], hold_s: float) -> list[tuple[str, float, float]]:
    """(zone, from, to) runs of one track from time-ordered (t, zone) samples. A new zone only counts once the
    track stays in it `hold_s`, so feet hovering on a border don't make a burst of one-frame visits."""
    segments: list[list] = []
    pending: tuple[str, float] | None = None  # (zone, first seen) of a zone not yet held long enough
    for t, zone in observations:
        if not segments:
            segments.append([zone, t, t])
        elif zone == segments[-1][0]:
            segments[-1][2], pending = t, None
        elif pending and pending[0] == zone:
            if t - pending[1] >= hold_s:
                segments[-1][2] = pending[1]
                segments.append([zone, pending[1], t])
                pending = None
        else:
            pending = (zone, t)
    return [tuple(s) for s in segments]


def heatmap(detections: list[dict], frame_size: tuple[int, int], grid: tuple[int, int]) -> dict[int, list[list[int]]]:
    """{hour from clip start: rows x cols counts of foot points}, one count per person per processed frame."""
    cols, rows = grid
    hours: dict[int, list[list[int]]] = {}
    for frame in detections:
        cells = hours.setdefault(int(frame["timestamp"] // 3600), [[0] * cols for _ in range(rows)])
        for person in frame["people"]:
            x, y = foot_point(person["bbox"], frame_size)
            cells[min(rows - 1, max(0, int(y * rows)))][min(cols - 1, max(0, int(x * cols)))] += 1
    return hours


def line_crossing(xs: list[tuple[float, float]], boundary: float, in_direction: str) -> tuple[str, float] | None:
    """('in' | 'out', time) when a track ends on the other side of a vertical entrance line than it started, at the
    time of its last side change; None otherwise. Net, not per frame, so feet jittering on the line count once."""
    if len(xs) < 2:
        return None
    direction = crossing_direction(xs[0][1], xs[-1][1], boundary)
    if direction is None:
        return None
    last_change = [t for (_, a), (t, b) in zip(xs, xs[1:]) if boundary_side(a, boundary) != boundary_side(b, boundary)][-1]
    return ("in" if direction == in_direction else "out"), last_change
