"""Pure rules for directional camera handoffs.

This module deliberately has no OpenCV or model imports so the identity
association logic can be tested on a CPU-only development machine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HandoffConfig:
    source_camera: str = "cam1"
    target_camera: str = "cam2"
    source_boundary: float = 0.85
    target_boundary: float = 0.15
    min_gap_seconds: float = 1.0
    max_gap_seconds: float = 45.0
    confirmed_threshold: float = 0.78
    uncertain_threshold: float = 0.52
    cooldown_seconds: float = 2.0


def boundary_side(x_normalized: float, boundary: float) -> str:
    """Return the side of a vertical boundary occupied by a point."""
    return "left" if x_normalized < boundary else "right"


def crossing_direction(previous_x: float, current_x: float, boundary: float) -> str | None:
    """Return the crossing direction when a point changes boundary side."""
    previous_side = boundary_side(previous_x, boundary)
    current_side = boundary_side(current_x, boundary)
    if previous_side == current_side:
        return None
    return "right" if current_side == "right" else "left"


def normalized_x(center_x: float, frame_width: float) -> float:
    if frame_width <= 0:
        raise ValueError("frame_width must be positive")
    return max(0.0, min(1.0, center_x / frame_width))


def cosine_similarity(first: list[float], second: list[float]) -> float:
    if not first or not second or len(first) != len(second):
        return 0.0
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    if first_norm == 0 or second_norm == 0:
        return 0.0
    return max(0.0, min(1.0, sum(a * b for a, b in zip(first, second)) / (first_norm * second_norm)))


def appearance_similarity(first: list[float], second: list[float]) -> float:
    """Compare lightweight normalized crop descriptors."""
    return cosine_similarity(first, second)


def time_compatibility(gap_seconds: float, config: HandoffConfig) -> float:
    if gap_seconds < config.min_gap_seconds or gap_seconds > config.max_gap_seconds:
        return 0.0
    span = config.max_gap_seconds - config.min_gap_seconds
    if span <= 0:
        return 1.0
    midpoint = (config.min_gap_seconds + config.max_gap_seconds) / 2
    distance = abs(gap_seconds - midpoint)
    return max(0.0, 1.0 - (distance / (span / 2)))


def score_candidate(exit_event: dict[str, Any], entry_event: dict[str, Any], config: HandoffConfig) -> dict[str, float]:
    gap = float(entry_event["timestamp_seconds"]) - float(exit_event["timestamp_seconds"])
    time_score = time_compatibility(gap, config)
    appearance_score = appearance_similarity(
        exit_event.get("appearance", []), entry_event.get("appearance", [])
    )
    score = (0.55 * appearance_score) + (0.45 * time_score)
    return {
        "score": round(score, 4),
        "appearance_similarity": round(appearance_score, 4),
        "time_compatibility": round(time_score, 4),
        "gap_seconds": round(gap, 3),
    }


def match_handoff_events(
    exits: list[dict[str, Any]],
    entries: list[dict[str, Any]],
    config: HandoffConfig,
) -> list[dict[str, Any]]:
    """Greedily resolve eligible candidates one-to-one by descending score."""
    candidates: list[dict[str, Any]] = []
    for exit_event in exits:
        if exit_event.get("camera_id") != config.source_camera or exit_event.get("direction") != "right":
            continue
        for entry_event in entries:
            if entry_event.get("camera_id") != config.target_camera or entry_event.get("direction") != "left":
                continue
            scores = score_candidate(exit_event, entry_event, config)
            if scores["time_compatibility"] == 0:
                continue
            candidates.append({"exit": exit_event, "entry": entry_event, **scores})

    candidates.sort(key=lambda candidate: candidate["score"], reverse=True)
    used_exits: set[str] = set()
    used_entries: set[str] = set()
    matches: list[dict[str, Any]] = []
    master_number = 1

    for candidate in candidates:
        exit_id = str(candidate["exit"]["event_id"])
        entry_id = str(candidate["entry"]["event_id"])
        if exit_id in used_exits or entry_id in used_entries:
            continue
        used_exits.add(exit_id)
        used_entries.add(entry_id)
        score = candidate["score"]
        if score >= config.confirmed_threshold:
            status = "confirmed"
            master_id = f"master-{master_number:03d}"
            master_number += 1
        elif score >= config.uncertain_threshold:
            status = "uncertain"
            master_id = None
        else:
            status = "unmatched"
            master_id = None
        matches.append({
            "status": status,
            "master_id": master_id,
            "source_event_id": exit_id,
            "target_event_id": entry_id,
            "source_track_id": candidate["exit"].get("local_track_id"),
            "target_track_id": candidate["entry"].get("local_track_id"),
            "score": score,
            "evidence": {
                "appearance_similarity": candidate["appearance_similarity"],
                "time_compatibility": candidate["time_compatibility"],
                "gap_seconds": candidate["gap_seconds"],
            },
        })

    matched_exit_ids = {match["source_event_id"] for match in matches}
    matched_entry_ids = {match["target_event_id"] for match in matches}
    for event in exits:
        if event.get("direction") == "right" and event.get("event_id") not in matched_exit_ids:
            matches.append({"status": "unmatched", "master_id": None, "source_event_id": event.get("event_id"), "target_event_id": None, "source_track_id": event.get("local_track_id"), "target_track_id": None, "score": 0.0, "evidence": {}})
    for event in entries:
        if event.get("event_id") not in matched_entry_ids:
            matches.append({"status": "unmatched", "master_id": None, "source_event_id": None, "target_event_id": event.get("event_id"), "source_track_id": None, "target_track_id": event.get("local_track_id"), "score": 0.0, "evidence": {}})
    return matches