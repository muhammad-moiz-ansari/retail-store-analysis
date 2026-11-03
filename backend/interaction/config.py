"""Interaction pipeline configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

try:
    from ..device import DEVICE
except ImportError:
    from device import DEVICE


@dataclass(slots=True)
class InteractionConfig:
    # COCO yolov8n tracks people: best.pt missed ~60% of the people COCO finds on our clips.
    # best.pt (OpenVINO, 320 px) only labels roles, during each track's first role_model_seconds.
    person_model: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1] / "yolov8n.pt")
    person_classes: tuple[int, ...] | None = (0,)
    imgsz: int = 320
    role_model_customer_labels: tuple[str, ...] = ("customer",)
    role_model: Path | None = field(default_factory=lambda: Path(__file__).resolve().parents[1] / "models" / "best_320_openvino_model")
    role_model_seconds: float = 1.0  # after this a track keeps the role it got, or goes without one
    role_recheck_seconds: float = 2.0  # one role-model look per track this often, to catch ID switches
    role_model_employee_labels: tuple[str, ...] = ("employee", "staff", "bib")
    role_mode: Literal["model", "bib_color"] = "model"
    bib_hsv_lower: tuple[int, int, int] = (20, 70, 70)
    bib_hsv_upper: tuple[int, int, int] = (40, 255, 255)
    bib_min_coverage: float = 0.04
    # Normalised (x1, y1, x2, y2) regions reserved for staff workstations,
    # counters, tills, or stock-room doors. They must be calibrated per camera.
    staff_zones: tuple[tuple[float, float, float, float], ...] = ()
    # Event-store layout of this camera (B4): normalised floor polygons keyed by store zone_id, e.g.
    # {"z2": [[0, 0.4], [0.5, 0.4], [0.5, 1], [0, 1]]}; feet outside every polygon count toward the camera's zone.
    floor_zones: dict[str, list[list[float]]] = field(default_factory=dict)
    zone_hold_seconds: float = 1.0  # a track must stay this long in a new zone before it counts as a move
    heatmap_grid: tuple[int, int] = (32, 18)  # cols, rows
    # Entrance camera only: a vertical line at this normalised x; a track ending on the other side of it from where it
    # started is one footfall, "in" when it moved toward entrance_in_direction ("right" or "left").
    entrance_line: float | None = None
    entrance_in_direction: Literal["right", "left"] = "right"
    stationary_distance_px: float = 18.0
    staff_zone_dwell_seconds: float = 12.0
    # Few-shot role references for this camera: torso descriptors of tracks a person labelled
    # (written by `python -m backend.interaction.calibrate`). They teach a new store its uniform without retraining.
    role_references: dict[str, list[list[float]]] = field(default_factory=dict)
    role_reference_margin: float = 0.3  # employee-minus-customer similarity that counts as full evidence
    role_weights: dict[str, float] = field(default_factory=dict)  # per-store overrides of the agent's weights
    role_unknown_band: float = 0.0  # scores within threshold ± band are "unknown"; 0 always picks a role
    role_smoothing: float = 0.65  # share of the old employee score kept per 0.1 s, whatever the frame rate
    employee_score_threshold: float = 0.45
    role_hold_seconds: float = 1.5
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
    relink_min_similarity: float = 0.40  # torso histogram correlation: other people 0.0-0.25, same person 0.4-0.75
    min_interaction_seconds: float = 2.0
    # Walking pace is ~0.8 body heights/s, so a passer-by drifts well past this within min_interaction_seconds.
    max_relative_drift_heights: float = 0.5
    max_missing_seconds: float = 1.5
    # Second-stage judge: once proximity says "interaction", it looks at the pair and can veto it.
    # pose: a head must point at the other person.
    interaction_judge: Literal["off", "pose"] = "pose"
    pose_model: Path = field(default_factory=lambda: Path(__file__).resolve().parents[1] / "models" / "yolov8n-pose.pt")
    facing_angle_degrees: float = 60.0  # 2D head direction is coarse, so allow a wide cone
    min_facing_fraction: float = 0.5  # share of judged frames in which someone faces the other
    judge_device: str | None = None  # None = same as device; e.g. YOLO on cpu, judge on cuda:0
    judge_frames: int = 4  # frames sampled across the last min_interaction_seconds
    judge_recheck_seconds: float = 1.0  # a rejected pair is re-judged this often while still close
    device: str = DEVICE  # "cuda:0" runs YOLO on the GPU (the .pt model; OpenVINO is CPU-only)

    @classmethod
    def from_json(cls, path: Path | None, **overrides) -> "InteractionConfig":
        """Per-store/camera settings from a JSON file (any field above); `overrides` win. Unknown keys raise."""
        values = json.loads(Path(path).read_text(encoding="utf-8")) if path else {}
        return cls(**{**values, **overrides})
