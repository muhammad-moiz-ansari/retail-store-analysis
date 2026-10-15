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

if TYPE_CHECKING:
    from ultralytics import YOLO


class RoleClassifier:
    def __init__(self, config: InteractionConfig, model: "YOLO | None" = None) -> None:
        self.config = config
        self.model = model
        self._history: dict[int, _TrackHistory] = {}

    def classify(
        self, frame: np.ndarray, bbox: tuple[int, int, int, int], track_id: int, timestamp: float
    ) -> tuple[str, float, dict[str, float]]:
        """Classify from visual, dwell, movement, and configured work-zone evidence."""
        if self.model is not None and self.config.role_mode == "model":
            result = self._classify_with_model(frame, bbox)
        else:
            result = None
        visual_role, visual_confidence = result or self._classify_bib_colour(frame, bbox)
        visual_score = visual_confidence if visual_role == "employee" else 0.0
        history = self._update_history(track_id, bbox, timestamp, frame.shape[1], frame.shape[0])
        zone_score = min(1.0, history.staff_zone_seconds / max(1.0, self.config.staff_zone_dwell_seconds))
        # Temporal signals only reinforce an appearance signal or a configured
        # employee-only zone; browsing/dwelling elsewhere is not staff evidence.
        raw_score = min(1.0, 0.80 * visual_score + 0.15 * zone_score + 0.05 * min(1.0, history.stationary_seconds / 30.0))
        if history.observations == 0:
            history.smoothed_employee_score = raw_score
        else:
            history.smoothed_employee_score = (
                self.config.role_smoothing * history.smoothed_employee_score
                + (1.0 - self.config.role_smoothing) * raw_score
            )
        history.observations += 1
        score = history.smoothed_employee_score
        evidence = {
            "visual_employee_score": round(visual_score, 3),
            "staff_zone_dwell_seconds": round(history.staff_zone_seconds, 2),
            "stationary_seconds": round(history.stationary_seconds, 2),
            "employee_score": round(score, 3),
        }
        return ("employee" if score >= self.config.employee_score_threshold else "customer", score, evidence)

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
        x1, y1, x2, y2 = bbox
        crop = frame[max(0, y1):max(y1 + 1, y2), max(0, x1):max(x1 + 1, x2)]
        if crop.size == 0:
            return None
        results = self.model(crop, verbose=False, conf=self.config.confidence, device=self.config.device)
        for result in results:
            for box in result.boxes:
                label = str(result.names[int(box.cls[0])]).lower()
                score = float(box.conf[0])
                if label in self.config.role_model_employee_labels:
                    return "employee", score
                if label in {"customer", "person"}:
                    return "customer", score
        return None

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


@dataclass
class _TrackHistory:
    center: tuple[float, float]
    last_seen_at: float
    stationary_seconds: float = 0.0
    staff_zone_seconds: float = 0.0
    smoothed_employee_score: float = 0.0
    observations: int = 0
