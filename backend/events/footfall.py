"""Directional entrance crossings for one time-ordered, camera-local track."""

from math import isfinite
from typing import Literal

Direction = Literal["in", "out"]


def entrance_crossings(
    samples: list[tuple[float, float]],
    boundary: float,
    in_direction: Literal["left", "right"],
    *,
    half_band: float = 0.02,
    hold_seconds: float = 0.25,
    max_gap_seconds: float = 1.0,
) -> list[tuple[Direction, float]]:
    """Return confirmed crossings at the first observed time on the destination side.

    A neutral band and a stable-side hold reject boundary jitter. Observation
    gaps reset the track state: crossing during a gap is unknown.
    """
    if (
        not all(isfinite(value) for value in (boundary, half_band, hold_seconds, max_gap_seconds))
        or not 0 < half_band < min(boundary, 1 - boundary)
        or not 0 < hold_seconds <= max_gap_seconds
        or in_direction not in {"left", "right"}
    ):
        raise ValueError("Invalid entrance crossing configuration")

    crossings: list[tuple[Direction, float]] = []
    stable_side = None
    candidate = None
    previous_time = None
    for timestamp, x in samples:
        if not isfinite(timestamp) or timestamp < 0 or not 0 <= x <= 1:
            raise ValueError("Entrance samples require a nonnegative time and normalized x")
        if previous_time is not None:
            if timestamp < previous_time:
                raise ValueError("Entrance samples must be time-ordered")
            if timestamp == previous_time:
                continue
            if timestamp - previous_time > max_gap_seconds:
                stable_side = candidate = None
        previous_time = timestamp

        side = "left" if x < boundary - half_band else "right" if x > boundary + half_band else None
        if side is None or side == stable_side:
            candidate = None
            continue
        if candidate is None or candidate[0] != side:
            candidate = side, timestamp
            continue
        if timestamp - candidate[1] >= hold_seconds:
            if stable_side is not None:
                crossings.append(("in" if side == in_direction else "out", candidate[1]))
            stable_side, candidate = side, None
    return crossings
