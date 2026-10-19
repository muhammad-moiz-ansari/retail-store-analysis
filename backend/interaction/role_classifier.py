"""Classify a tracked person using the employee bib dataset/model contract.

The preferred mode uses a YOLO model trained with employee/staff/bib labels.
For early dataset validation, a configurable HSV bib-colour fallback is supplied.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import TYPE_CHECKING

import cv2
import numpy as np

from .config import InteractionConfig
from .cust_emp_classifier import CustEmpClassifier

if TYPE_CHECKING:
    from ultralytics import YOLO


class RoleClassifier:
    def __init__(self, config: InteractionConfig, model: "YOLO | None" = None) -> None:
        self.config = config
        self.model = model
        self.agent = CustEmpClassifier(threshold=config.employee_score_threshold)
        self._history: dict[int, _TrackHistory] = {}
        self._role_frame: np.ndarray | None = None
        self._role_detections: list[tuple[tuple[float, ...], str, float]] = []

    def classify(
        self, frame: np.ndarray, bbox: tuple[int, int, int, int], track_id: int, timestamp: float
    ) -> tuple[str, float, dict]:
        """Classify from YOLO role, bib colour, staff-zone and stationary evidence via the weighted agent."""
        yolo = self._classify_with_model(frame, bbox) if self.model is not None and self.config.role_mode == "model" else None
        bib_role, bib_confidence = self._classify_bib_colour(frame, bbox)
        history = self._update_history(track_id, bbox, timestamp, frame.shape[1], frame.shape[0])
        # Temporal signals only reinforce an appearance signal or a configured
        # employee-only zone; browsing/dwelling elsewhere is not staff evidence.
        factors = {
            "yolo": None if yolo is None else (yolo[1] if yolo[0] == "employee" else -yolo[1]),
            "bib_colour": bib_confidence if bib_role == "employee" else 0.0,
            "staff_zone": min(1.0, history.staff_zone_seconds / max(1.0, self.config.staff_zone_dwell_seconds)),
            "stationary": min(1.0, history.stationary_seconds / 30.0),
        }
        _, raw_score, contributions = self.agent.decide(factors)
        if history.observations == 0:
            history.smoothed_employee_score = raw_score
        else:
            history.smoothed_employee_score = (
                self.config.role_smoothing * history.smoothed_employee_score
                + (1.0 - self.config.role_smoothing) * raw_score
            )
        history.observations += 1
        score = history.smoothed_employee_score
        frame_role = "employee" if score >= self.agent.threshold else "customer"
        # An ID keeps its role until the opposite role has held for role_hold_seconds:
        # ignores flicker, but still corrects a ByteTrack ID swap between people.
        if history.role is None or frame_role == history.role:
            history.role, history.pending_role = history.role or frame_role, None
        elif history.pending_role != frame_role:
            history.pending_role, history.pending_since = frame_role, timestamp
        elif timestamp - history.pending_since >= self.config.role_hold_seconds:
            history.role, history.pending_role = frame_role, None
        evidence = {
            "frame_role": frame_role,
            "yolo_role": None if yolo is None else yolo[0],
            "factors": {name: None if value is None else round(value, 3) for name, value in factors.items()},
            "contributions": contributions,
            "staff_zone_dwell_seconds": round(history.staff_zone_seconds, 2),
            "stationary_seconds": round(history.stationary_seconds, 2),
            "raw_employee_score": round(raw_score, 3),
            "employee_score": round(score, 3),
        }
        return (history.role, score, evidence)

    def _update_history(self, track_id: int, bbox: tuple[int, int, int, int], timestamp: float, width: int, height: int) -> "_TrackHistory":
        center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
        history = self._history.get(track_id)
        if history is None:
            history = _TrackHistory(center=center, last_seen_at=timestamp)
            self._history[track_id] = history
            return history
        elapsed = max(0.0, min(timestamp - history.last_seen_at, 2.0))
        if hypot(center[0] - history.center[0], center[1] - history.center[1]) <= self.config.stationary_distance_px:
            history.stationary_seconds += elapsed
        else:
            history.stationary_seconds = 0.0
        normalised = (center[0] / max(1, width), center[1] / max(1, height))
        if any(x1 <= normalised[0] <= x2 and y1 <= normalised[1] <= y2 for x1, y1, x2, y2 in self.config.staff_zones):
            history.staff_zone_seconds += elapsed
        history.center, history.last_seen_at = center, timestamp
        return history

    def _classify_with_model(self, frame: np.ndarray, bbox: tuple[int, int, int, int]) -> tuple[str, float] | None:
        """Run the role model once on the full frame and take the detection that best overlaps this person.

        Cropping let an overlapping neighbour's bib leak into the wrong person's crop.
        """
        if frame is not self._role_frame:
            self._role_frame, self._role_detections = frame, []
            for result in self.model(frame, verbose=False, conf=self.config.confidence, device=self.config.device):
                for box in result.boxes:
                    label = str(result.names[int(box.cls[0])]).lower()
                    role = "employee" if label in self.config.role_model_employee_labels else "customer" if label in {"customer", "person"} else None
                    if role:
                        self._role_detections.append((tuple(box.xyxy[0].tolist()), role, float(box.conf[0])))
        overlap, role, score = max(((_iou(bbox, box), role, score) for box, role, score in self._role_detections), default=(0.0, None, 0.0))
        return (role, score) if overlap >= 0.4 else None

    def _classify_bib_colour(self, frame: np.ndarray, bbox: tuple[int, int, int, int]) -> tuple[str, float]:
        """Measure bib colour in the middle torso, avoiding face/legs/background."""
        x1, y1, x2, y2 = bbox
        height, width = frame.shape[:2]
        x1, x2 = max(0, x1), min(width, x2)
        y1, y2 = max(0, y1), min(height, y2)
        torso = frame[y1 + (y2-y1)//4:y1 + 3*(y2-y1)//4, x1 + (x2-x1)//5:x2 - (x2-x1)//5]
        if torso.size == 0:
            return "customer", 0.0
        hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array(self.config.bib_hsv_lower), np.array(self.config.bib_hsv_upper))
        coverage = float(np.count_nonzero(mask)) / mask.size
        if coverage >= self.config.bib_min_coverage:
            return "employee", min(1.0, coverage / max(self.config.bib_min_coverage, 1e-6))
        return "customer", min(1.0, 1.0 - coverage)


def _iou(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    width = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = width * height
    return inter / max(1e-6, (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)


@dataclass
class _TrackHistory:
    center: tuple[float, float]
    last_seen_at: float
    stationary_seconds: float = 0.0
    staff_zone_seconds: float = 0.0
    smoothed_employee_score: float = 0.0
    observations: int = 0
    role: str | None = None
    pending_role: str | None = None
    pending_since: float = 0.0
