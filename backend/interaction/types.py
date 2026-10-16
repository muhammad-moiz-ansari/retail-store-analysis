"""Serialisable objects used by interaction analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Role = Literal["employee", "customer"]


@dataclass(slots=True)
class TrackedPerson:
    track_id: int
    bbox: tuple[int, int, int, int]
    confidence: float
    role: Role
    role_confidence: float
    role_evidence: dict | None = None

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def to_dict(self) -> dict:
        result = asdict(self)
        result["bbox"], result["center"] = list(self.bbox), list(self.center)
        return result


@dataclass(slots=True)
class InteractionEvent:
    employee_track_id: int
    customer_track_id: int
    started_at: float
    last_seen_at: float
    distance_px: float
    active: bool = True

    @property
    def duration_seconds(self) -> float:
        return max(0.0, self.last_seen_at - self.started_at)

    def to_dict(self) -> dict:
        result = asdict(self)
        result["duration_seconds"], result["distance_px"] = round(self.duration_seconds, 3), round(self.distance_px, 2)
        return result
