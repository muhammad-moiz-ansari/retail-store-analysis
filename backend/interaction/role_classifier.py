"""Classify a tracked person using the employee bib dataset/model contract.

The preferred mode uses a YOLO model trained with employee/staff/bib labels.
For early dataset validation, a configurable HSV bib-colour fallback is supplied.
"""

from __future__ import annotations

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

    def classify(self, frame: np.ndarray, bbox: tuple[int, int, int, int]) -> tuple[str, float]:
        """Return employee/customer and confidence for one detected person."""
        if self.model is not None and self.config.role_mode == "model":
            result = self._classify_with_model(frame, bbox)
            if result is not None:
                return result
        return self._classify_bib_colour(frame, bbox)

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
