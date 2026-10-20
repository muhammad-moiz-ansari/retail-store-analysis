"""Version 1 boundary between Track A (CV) and Track B (events/storage)."""

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .schemas import Identifier, StrictModel, Unit


class ModelVersion(StrictModel):
    detector: str
    embedding: str
    preprocessing: str
    embedding_dimensions: int = Field(gt=0)
    orientation: str
    tracker: str


class Orientation(StrictModel):
    state: Literal["known", "unknown"] = "unknown"
    vector: tuple[float, float] | None = None
    confidence: Unit | None = None
    reason: str | None = "unavailable"
    method: str = "nose-ear-proxy"

    @model_validator(mode="after")
    def consistent(self):
        if self.state == "known":
            if self.vector is None or self.confidence is None or self.reason is not None:
                raise ValueError("Known orientation requires vector/confidence and no unknown reason")
            if not math.isclose(math.hypot(*self.vector), 1, abs_tol=1e-5):
                raise ValueError("Facing vectors must be unit length")
        elif self.vector is not None or self.confidence is not None or not self.reason:
            raise ValueError("Unknown orientation requires a reason and null estimates")
        return self


class TrackObservation(StrictModel):
    schema_version: Literal[1] = 1
    session_id: Identifier
    track_id: str
    global_person_id: Identifier
    source_seconds: float = Field(ge=0)
    utc_time: datetime | None = None
    bbox: tuple[float, float, float, float]
    source_size: tuple[int, int]
    detection_confidence: Unit
    role: Literal["employee", "customer", "unknown"] = "unknown"
    role_evidence: dict[str, float] = Field(default_factory=dict)
    role_reason: str | None = "uncalibrated"
    orientation: Orientation = Field(default_factory=Orientation)
    zone: str = "Unassigned"
    shift: str = "Unassigned"

    @model_validator(mode="after")
    def geometry(self):
        w, h = self.source_size
        x1, y1, x2, y2 = self.bbox
        if w <= 0 or h <= 0 or not (0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h):
            raise ValueError("Box must have positive area inside source image")
        if not self.track_id.startswith(self.session_id + ":"):
            raise ValueError("Track ID must be namespaced by session")
        if self.utc_time is not None and self.utc_time.utcoffset() is None:
            raise ValueError("UTC anchor must be timezone aware")
        return self

    def event_observation(self):
        """Use the cross-camera global ID in the existing event engine."""
        from .core import Observation
        x1, y1, x2, y2 = self.bbox
        diagonal = math.hypot(*self.source_size)
        return Observation(self.global_person_id, self.role, ((x1 + x2) / (2 * diagonal),
                           (y1 + y2) / (2 * diagonal)), self.orientation.vector,
                           self.orientation.confidence or 0, self.zone)


class FrameResult(StrictModel):
    schema_version: Literal[1] = 1
    store_id: Identifier
    camera_id: Identifier
    session_id: Identifier
    source_seconds: float = Field(ge=0)
    utc_time: datetime | None = None
    observations: list[TrackObservation] = Field(default_factory=list)
    detections: list[dict] = Field(default_factory=list)
    review_samples: list[dict] = Field(default_factory=list)
    status: Literal["analyzed", "failed"] = "analyzed"
    reason: str | None = None
    source_gap_seconds: float = Field(ge=0, default=0)
    skipped_frames: int = Field(ge=0, default=0)
    processing_seconds: float = Field(ge=0, default=0)
    models: ModelVersion
    calibration_version: str | None = None


class Signal(StrictModel):
    schema_version: Literal[1] = 1
    kind: Literal["session_started", "session_ended", "acquisition_error"]
    camera_id: Identifier
    session_id: Identifier
    source_seconds: float | None = Field(default=None, ge=0)
    reason: str | None = None
    utc_time: datetime | None = None


class ReferenceTrack(StrictModel):
    track_id: str
    camera_id: Identifier
    split: Literal["calibration"] = "calibration"
    role: Literal["employee", "customer"]
    label_version: str
    embeddings: list[list[float]] = Field(min_length=1, max_length=10)


class Calibration(StrictModel):
    schema_version: Literal[1] = 1
    version: str
    store_id: Identifier
    camera_id: Identifier
    models: ModelVersion
    references: list[ReferenceTrack]
    prototypes: dict[str, list[float]]
    similarity: Unit = 0.65
    margin: float = Field(default=0.08, gt=0, le=1)

    @model_validator(mode="after")
    def validate_prototypes(self):
        from .core import normalized
        if set(self.prototypes) != {"employee", "customer"}:
            raise ValueError("Both role prototypes are required")
        if len({r.track_id for r in self.references}) != len(self.references):
            raise ValueError("Reference tracks must be unique")
        for role in self.prototypes:
            if sum(r.role == role for r in self.references) < 2:
                raise ValueError("At least two reviewed tracks per role are required")
        for ref in self.references:
            if ref.camera_id != self.camera_id:
                raise ValueError("References must belong to the calibrated camera")
        vectors = list(self.prototypes.values()) + [v for r in self.references for v in r.embeddings]
        for vector in vectors:
            if len(vector) != self.models.embedding_dimensions:
                raise ValueError("Embedding dimensions do not match model")
            normalized(vector)
        return self
