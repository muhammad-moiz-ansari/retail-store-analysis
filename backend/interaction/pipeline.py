"""High-level interaction pipeline joining detection, roles, and engagement."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from .config import InteractionConfig
from .engagement import EngagementDetector
from .role_classifier import RoleClassifier
from .tracker import ByteTrackPersonTracker
from .types import TrackedPerson


class InteractionPipeline:
    def __init__(self, config: InteractionConfig | None = None) -> None:
        self.config = config or InteractionConfig()
        from ultralytics import YOLO  # lazy: importing package does not require ML dependencies

        self.person_model = YOLO(str(self.config.person_model))
        role_model = YOLO(str(self.config.role_model)) if self.config.role_model and Path(self.config.role_model).is_file() else None
        self.tracker = ByteTrackPersonTracker(self.person_model, self.config)
        self.classifier = RoleClassifier(self.config, role_model)
        self.engagement = EngagementDetector(self.config)

    def process_frame(self, frame: np.ndarray, timestamp: float | None = None) -> dict:
        timestamp = time.time() if timestamp is None else timestamp
        people = [
            TrackedPerson(
                track_id=item["track_id"], bbox=item["bbox"], confidence=item["confidence"],
                role=role, role_confidence=role_confidence, role_evidence=evidence,
            )
            for item in self.tracker.detect_and_track(frame)
            for role, role_confidence, evidence in [
                self.classifier.classify(frame, item["bbox"], item["track_id"], timestamp)
            ]
        ]
        events = self.engagement.update(people, timestamp)
        employees = sum(person.role == "employee" for person in people)
        customers = len(people) - employees
        return {
            "timestamp": timestamp,
            "people": [person.to_dict() for person in people],
            "employee_count": employees,
            "customer_count": customers,
            "interactions": [event.to_dict() for event in events],
        }
