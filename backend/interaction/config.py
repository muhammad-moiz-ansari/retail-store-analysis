"""Interaction pipeline configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(slots=True)
class InteractionConfig:
    person_model: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1] / "yolov8n.pt")
    role_model: Path | None = None
    role_model_employee_labels: tuple[str, ...] = ("employee", "staff", "bib")
    role_mode: Literal["model", "bib_color"] = "model"
    bib_hsv_lower: tuple[int, int, int] = (20, 70, 70)
    bib_hsv_upper: tuple[int, int, int] = (40, 255, 255)
    bib_min_coverage: float = 0.04
    # Normalised (x1, y1, x2, y2) regions reserved for staff workstations,
    # counters, tills, or stock-room doors. They must be calibrated per camera.
    staff_zones: tuple[tuple[float, float, float, float], ...] = ()
    stationary_distance_px: float = 18.0
    staff_zone_dwell_seconds: float = 12.0
    role_smoothing: float = 0.65
    employee_score_threshold: float = 0.60
    confidence: float = 0.35
    tracker: str = "bytetrack.yaml"
    interaction_distance_px: float = 180.0
    min_interaction_seconds: float = 2.0
    max_missing_seconds: float = 1.5
    device: str = "cpu"
