"""YOLO person detection plus persistent ByteTrack IDs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .config import InteractionConfig

if TYPE_CHECKING:
    from ultralytics import YOLO


class ByteTrackPersonTracker:
    """Thin adapter around Ultralytics' supported ByteTrack integration."""

    def __init__(self, model: "YOLO", config: InteractionConfig) -> None:
        self.model = model
        self.config = config

    def detect_and_track(self, frame: np.ndarray) -> list[dict]:
        results = self.model.track(
            frame,
            persist=True,
            classes=[0],  # COCO person
            conf=self.config.confidence,
            tracker=self.config.tracker,
            device=self.config.device,
            verbose=False,
        )
        people: list[dict] = []
        for result in results:
            if result.boxes is None or result.boxes.id is None:
                continue
            for box, track_id in zip(result.boxes, result.boxes.id):
                x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
                people.append({
                    "track_id": int(track_id.item()),
                    "bbox": (x1, y1, x2, y2),
                    "confidence": float(box.conf[0]),
                })
        return people
