"""OpenCV overlays for reviewing interaction analytics output."""

from __future__ import annotations

import cv2
import numpy as np

from .engagement import BODY_PARTS
from .types import CONFIRMED


ROLE_COLORS = {"employee": (0, 180, 255), "customer": (255, 180, 0), "unknown": (160, 160, 160)}


# BGR colour and caption of each whole-view zone state (events.live_zones).
ZONE_STYLES = {"hot": ((0, 0, 255), "HOT ZONE: more customers than staff"), "gray": ((150, 150, 150), "GRAY ZONE: customers covered by staff"),
               "green": ((0, 170, 0), "GREEN ZONE: staff only"), "inactive": ((60, 60, 60), "NOT ACTIVE: nobody in view"),
               "starting": ((60, 60, 60), "STARTING")}


def draw_zones(frame: np.ndarray, zones: dict) -> np.ndarray:
    """Frame the whole picture in the zone's colour and caption it; the view is one zone."""
    framed = frame.copy()
    height, width = framed.shape[:2]
    color, caption = ZONE_STYLES[zones["view"]]
    cv2.rectangle(framed, (3, 3), (width - 4, height - 4), color, 7)
    cv2.rectangle(framed, (12, height - 40), (26 + 10 * len(caption), height - 12), color, -1)
    cv2.putText(framed, caption, (19, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    return framed


def draw_result(frame: np.ndarray, result: dict) -> np.ndarray:
    annotated = draw_zones(frame, result["zones"]) if result.get("zones") else frame.copy()
    centers: dict[int, tuple[int, int]] = {}
    for person in result["people"]:
        x1, y1, x2, y2 = person["bbox"]
        color = ROLE_COLORS[person["role"]]
        centers[person["track_id"]] = tuple(map(int, person["center"]))
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        for fraction in sorted({f for _, top, bottom in BODY_PARTS for f in (top, bottom)} - {0.0, 1.0}):
            y = int(y1 + fraction * (y2 - y1))  # head / hips / feet band edges (bands overlap)
            cv2.line(annotated, (x1, y), (x2, y), color, 1)
        label = f'{person["role"]} #{person["track_id"]} {person["role_confidence"]:.0%}'
        cv2.putText(annotated, label, (x1, max(18, y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    for event in result["interactions"]:
        if event.get("verdict", "unverified") not in CONFIRMED:
            continue  # rejected by the interaction judge
        a, b = centers.get(event["employee_track_id"]), centers.get(event["customer_track_id"])
        if a and b:
            cv2.line(annotated, a, b, (0, 255, 0), 2)
            cv2.putText(annotated, f'{event["duration_seconds"]:.1f}s {event["measured_by"]} {event["distance_body_heights"]:.2f}h', a, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    summary = f'Employees: {result["employee_count"]}  Customers: {result["customer_count"]}'
    cv2.putText(annotated, summary, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
    on = result["interaction_active"]
    cv2.rectangle(annotated, (12, 40), (232, 72), (0, 200, 0) if on else (80, 80, 80), -1)
    cv2.putText(annotated, f'INTERACTION: {"ON" if on else "OFF"}', (20, 63), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return annotated
