"""YOLO person detection plus persistent ByteTrack IDs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from ..camera_handoff import appearance_descriptor
from ..handoff_core import appearance_similarity
from .config import InteractionConfig

if TYPE_CHECKING:
    from ultralytics import YOLO


class ByteTrackPersonTracker:
    """Adapter around Ultralytics tracking, plus ID memory for people hidden mid-frame."""

    def __init__(self, model: "YOLO", config: InteractionConfig) -> None:
        self.model = model
        self.config = config
        self._alias: dict[int, int] = {}  # raw tracker ID -> stable ID
        self._seen: dict[int, dict] = {}  # stable ID -> last bbox, time, mean appearance
        self._live_prev: set[int] = set()

    def detect_and_track(self, frame: np.ndarray, timestamp: float) -> list[dict]:
        results = self.model.track(
            frame,
            persist=True,
            classes=None if self.config.person_classes is None else list(self.config.person_classes),
            imgsz=self.config.imgsz,
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
                    "label": str(result.names[int(box.cls[0])]).lower(),
                })
        return self._relink(frame, people, timestamp)

    def _relink(self, frame: np.ndarray, people: list[dict], timestamp: float) -> list[dict]:
        """Give a new raw ID that appears mid-frame the stable ID of a person who vanished mid-frame.

        Lost at a left/right edge means they left; lost mid-frame means hidden and back soon.
        shortcut: exits are only the left/right frame edges (no doors), add exit zones per camera if needed.
        """
        width = frame.shape[1]
        margin = self.config.exit_edge_margin * width
        at_edge = lambda bbox: bbox[0] <= margin or bbox[2] >= width - margin
        live = {self._alias[p["track_id"]] for p in people if p["track_id"] in self._alias}
        for person in people:
            descriptor = appearance_descriptor(frame, list(person["bbox"]))
            raw = person["track_id"]
            if raw not in self._alias:
                self._alias[raw] = raw
                if not at_edge(person["bbox"]) and descriptor:
                    candidates = [
                        (appearance_similarity(seen["descriptor"], descriptor), stable)
                        for stable, seen in self._seen.items()
                        if stable not in live and not at_edge(seen["bbox"])
                        and timestamp - seen["last_seen"] <= self.config.relink_seconds
                    ]
                    similarity, stable = max(candidates, default=(0.0, None))
                    if stable is not None and similarity >= self.config.relink_min_similarity:
                        self._alias[raw] = stable
                live.add(self._alias[raw])
            person["track_id"] = stable = self._alias[raw]
            seen = self._seen.get(stable)
            if seen is None or not seen["descriptor"]:
                self._seen[stable] = seen = {"descriptor": descriptor, "frames": 1}
            elif descriptor:
                # Running mean, so a half-hidden last frame cannot dominate the fingerprint.
                seen["frames"] += 1
                seen["descriptor"] = [old + (new - old) / seen["frames"] for old, new in zip(seen["descriptor"], descriptor)]
            seen["bbox"], seen["last_seen"] = person["bbox"], timestamp
            seen.setdefault("born", timestamp)
        # During an occlusion the tracker often starts the new ID while the old one still
        # holds a shrinking partial box (e.g. just a head); when the old one then dies
        # mid-frame inside a young box, fold the young ID back into the old one.
        for lost in self._live_prev - live:
            old = self._seen.get(lost)
            if old is None or at_edge(old["bbox"]):
                continue
            for person in people:
                young = person["track_id"]
                fresh = self._seen[young]
                if young != lost and timestamp - fresh["born"] <= 1.0 and fresh["born"] > old["born"] \
                        and _inside_fraction(old["bbox"], person["bbox"]) >= 0.5 \
                        and appearance_similarity(old["descriptor"], fresh["descriptor"]) >= self.config.relink_min_similarity:
                    for raw, stable in self._alias.items():
                        if stable == young:
                            self._alias[raw] = lost
                    person["track_id"] = lost
                    old["bbox"], old["last_seen"] = fresh["bbox"], timestamp
                    del self._seen[young]
                    live = (live - {young}) | {lost}
                    break
        self._live_prev = live
        return people


def _inside_fraction(inner: tuple[int, int, int, int], outer: tuple[int, int, int, int]) -> float:
    """Share of `inner`'s area that lies inside `outer`."""
    width = max(0, min(inner[2], outer[2]) - max(inner[0], outer[0]))
    height = max(0, min(inner[3], outer[3]) - max(inner[1], outer[1]))
    return width * height / max(1, (inner[2] - inner[0]) * (inner[3] - inner[1]))
