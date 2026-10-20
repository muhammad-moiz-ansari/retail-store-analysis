"""Stateful employee/customer proximity interaction detection.

Works on a moving camera: no floor calibration, distances are in body heights.
"""

from __future__ import annotations

from math import hypot

from .config import InteractionConfig
from .types import InteractionEvent, TrackedPerson

# The box is split into generous, overlapping bands (single detector, no pose model),
# lowest first: feet are on the floor so they carry depth and take precedence; hips
# and head are fallbacks with tighter limits. shortcut: fixed bands assume an upright
# person; a seated/bending person shifts them, use pose keypoints if hardware allows.
BODY_PARTS = (("feet", 0.65, 1.0), ("hips", 0.25, 0.70), ("head", 0.0, 0.30))


def part_band(person: TrackedPerson, top: float, bottom: float) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = person.bbox
    return (x1, y1 + top * (y2 - y1), x2, y1 + bottom * (y2 - y1))


def _visible_band(person: TrackedPerson, part: str, top: float, bottom: float, others: list[TrackedPerson],
                  frame_height: int, margin: float) -> tuple[float, float, float, float] | None:
    if part == "feet" and person.bbox[3] >= frame_height - margin:
        return None  # box cut off by the frame bottom: the feet are not in view
    if part == "head" and person.bbox[1] <= margin:
        return None
    band = part_band(person, top, bottom)
    cx, cy = (band[0] + band[2]) / 2, (band[1] + band[3]) / 2
    if part != "head" and any(o is not person and o.bbox[0] < cx < o.bbox[2] and o.bbox[1] < cy < o.bbox[3]
                              and o.bbox[3] > person.bbox[3] for o in others):
        return None  # hidden behind someone standing nearer the camera (their box reaches lower)
    return band


def body_distance(a: TrackedPerson, b: TrackedPerson, config: InteractionConfig,
                  others: list[TrackedPerson] = (), frame_height: int = 10**9) -> tuple[float, str, bool] | None:
    """(gap between matching body bands in body heights, part used, close enough), lowest band visible on both."""
    heights = sorted((a.bbox[3] - a.bbox[1], b.bbox[3] - b.bbox[1]))
    if heights[0] <= 0:
        return None
    others = list(others) or [a, b]
    for part, top, bottom in BODY_PARTS:
        ba = _visible_band(a, part, top, bottom, others, frame_height, config.frame_edge_margin_px)
        bb = _visible_band(b, part, top, bottom, others, frame_height, config.frame_edge_margin_px)
        if ba and bb:
            # Edge-to-edge gap, 0 when the bands touch. A cut-off box understates height,
            # so the distance errs towards "not close".
            dx = max(0.0, ba[0] - bb[2], bb[0] - ba[2])
            dy = max(0.0, ba[1] - bb[3], bb[1] - ba[3])
            distance = hypot(dx, dy) / (sum(heights) / 2)
            # Very different apparent heights mean different depths, however close in the image.
            close = distance <= config.interaction_thresholds_heights[part] and heights[0] / heights[1] >= config.min_height_ratio
            return distance, part, close
    return None


class EngagementDetector:
    def __init__(self, config: InteractionConfig) -> None:
        self.config = config
        self._events: dict[tuple[int, int], InteractionEvent] = {}

    def update(self, people: list[TrackedPerson], timestamp: float, frame_height: int = 10**9) -> list[InteractionEvent]:
        """Update interaction state and return active/just-finished eligible events."""
        employees = [person for person in people if person.role == "employee"]
        customers = [person for person in people if person.role == "customer"]
        seen: set[tuple[int, int]] = set()
        for employee in employees:
            for customer in customers:
                measured = body_distance(employee, customer, self.config, people, frame_height)
                if measured is None or not measured[2]:
                    continue
                distance, part, _ = measured
                key = (employee.track_id, customer.track_id)
                seen.add(key)
                event = self._events.get(key)
                if event is None:
                    self._events[key] = InteractionEvent(*key, timestamp, timestamp, distance, part)
                else:
                    event.last_seen_at, event.distance_body_heights, event.measured_by, event.active = timestamp, distance, part, True

        output: list[InteractionEvent] = []
        for key, event in list(self._events.items()):
            if key not in seen and timestamp - event.last_seen_at > self.config.max_missing_seconds:
                event.active = False
                del self._events[key]
            if event.duration_seconds >= self.config.min_interaction_seconds:
                output.append(event)
        return output

    def active_events(self) -> list[InteractionEvent]:
        return list(self._events.values())
