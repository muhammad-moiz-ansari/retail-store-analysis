"""Interaction pipeline configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(slots=True)
class InteractionConfig:
    # One model detects + tracks + labels roles: best.pt exported to OpenVINO at 320 px
    # (~10 fps tracking on a laptop CPU). For a plain COCO model set person_classes=(0,).
    person_model: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1] / "models" / "best_320_openvino_model")
    person_classes: tuple[int, ...] | None = None
    imgsz: int = 320
    role_model_customer_labels: tuple[str, ...] = ("customer",)
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
    employee_score_threshold: float = 0.45
    role_hold_seconds: float = 3.0
    confidence: float = 0.35
    tracker: str = str(Path(__file__).with_name("botsort_reid.yaml"))
    # Interaction distance in body heights (mean box height of the pair), no floor calibration.
    # Higher body parts carry less depth information, so their limits are tighter.
    frame_edge_margin_px: float = 4.0  # a box this close to the frame edge is cut off
    interaction_thresholds_heights: dict[str, float] = field(default_factory=lambda: {"feet": 1.0, "hips": 0.8, "head": 0.6})
    min_height_ratio: float = 0.6
    # ID memory: a person lost mid-frame (not at a left/right edge) is assumed hidden and
    # gets their old ID back if a similar-looking person appears mid-frame within relink_seconds.
    exit_edge_margin: float = 0.05
    relink_seconds: float = 5.0
    relink_min_similarity: float = 0.90
    min_interaction_seconds: float = 2.0
    max_missing_seconds: float = 1.5
    device: str = "cpu"
