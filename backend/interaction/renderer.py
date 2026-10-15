"""OpenCV overlays for reviewing interaction analytics output."""

from __future__ import annotations

import cv2
import numpy as np


ROLE_COLORS = {"employee": (0, 180, 255), "customer": (255, 180, 0)}


def draw_result(frame: np.ndarray, result: dict) -> np.ndarray:
    annotated = frame.copy()
    centers: dict[int, tuple[int, int]] = {}
    for person in result["people"]:
        x1, y1, x2, y2 = person["bbox"]
        color = ROLE_COLORS[person["role"]]
        centers[person["track_id"]] = tuple(map(int, person["center"]))
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label = f'{person["role"]} #{person["track_id"]} {person["role_confidence"]:.0%}'
        cv2.putText(annotated, label, (x1, max(18, y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    for event in result["interactions"]:
        a, b = centers.get(event["employee_track_id"]), centers.get(event["customer_track_id"])
        if a and b:
            cv2.line(annotated, a, b, (0, 255, 0), 2)
            cv2.putText(annotated, f'{event["duration_seconds"]:.1f}s', a, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    summary = f'Employees: {result["employee_count"]}  Customers: {result["customer_count"]}'
    cv2.putText(annotated, summary, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
    return annotated
