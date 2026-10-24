"""Pose judge: confirms a proximity interaction only if someone's head is turned towards the other person."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .core import head_direction
from .geometry import match_boxes


@dataclass(frozen=True)
class JudgeResult:
    label: str  # interaction | no_interaction | unknown
    confidence: float
    evidence: dict[str, Any] = field(default_factory=dict)


def head_vector(keypoints, min_confidence: float = 0.5) -> tuple[float, float] | None:
    """Head direction from nose vs ears; a head in profile hides its far ear, so one visible ear is enough."""
    vector, _ = head_direction(keypoints, min_confidence)
    if vector is not None:
        return vector
    nose, ears = keypoints[0], [keypoints[i] for i in (3, 4) if keypoints[i][2] >= min_confidence]
    if nose[2] < min_confidence or len(ears) != 1:
        return None  # back to the camera (no nose), or facing the camera: no evidence either way
    dx, dy = nose[0] - ears[0][0], nose[1] - ears[0][1]
    length = math.hypot(dx, dy)
    return (dx / length, dy / length) if length >= 2 else None


def facing(keypoints, own_box, other_box, max_angle_degrees: float) -> bool | None:
    """True if the head points at the other person's head, None if the head direction is unknown."""
    vector = head_vector(keypoints)
    if vector is None:
        return None
    nose = keypoints[0]
    # Aim at the other head (top of their box): at conversation range their box centre is well below eye level.
    to_other = ((other_box[0] + other_box[2]) / 2 - nose[0], other_box[1] + 0.15 * (other_box[3] - other_box[1]) - nose[1])
    length = math.hypot(*to_other)
    if length < 1e-6:
        return None
    return (vector[0] * to_other[0] + vector[1] * to_other[1]) / length >= math.cos(math.radians(max_angle_degrees))


def judge_frames(people_keypoints: list[tuple[list | None, list | None]], boxes: list, max_angle_degrees: float,
                 min_facing_fraction: float) -> JudgeResult:
    """people_keypoints[i] = (employee keypoints, customer keypoints) in frame i, None if no pose matched."""
    facing_frames = known_frames = 0
    for (employee, customer), (employee_box, customer_box) in zip(people_keypoints, boxes):
        if employee is None and customer is None:
            continue  # pose model found neither person in this frame
        known_frames += 1
        facing_frames += any(facing(keypoints, own, other, max_angle_degrees) for keypoints, own, other in (
            (employee, employee_box, customer_box), (customer, customer_box, employee_box)) if keypoints is not None)
    if not known_frames:
        return JudgeResult("unknown", 0.0, {"reason": "no_pose"})
    fraction = facing_frames / known_frames
    label = "interaction" if fraction >= min_facing_fraction else "no_interaction"
    return JudgeResult(label, fraction if label == "interaction" else 1 - fraction,
                     {"facing_frames": facing_frames, "frames_with_pose": known_frames})


class PoseJudge:
    """Runs a YOLO pose model on the pair crops; at least one head must point at the other person."""

    def __init__(self, model: Path | str, device: str = "cpu", max_angle_degrees: float = 60, min_facing_fraction: float = 0.5,
                 imgsz: int = 320):
        from ultralytics import YOLO  # lazy, like the detector

        # Pair crops are ~300-500 px, so 320 is near native resolution; the default 640 upsamples for nothing.
        self.model, self.device, self.imgsz = YOLO(str(model)), device, imgsz
        self.max_angle_degrees, self.min_facing_fraction = max_angle_degrees, min_facing_fraction

    def classify_interaction(self, frames_bgr: list[Any], boxes: list | None = None) -> JudgeResult:
        if not boxes:
            return JudgeResult("unknown", 0.0, {"reason": "pose_judge_needs_boxes"})
        people = []
        for frame, pair in zip(frames_bgr, boxes):
            result = self.model(frame, verbose=False, device=self.device, imgsz=self.imgsz)[0]
            poses = result.boxes.xyxy.tolist() if result.keypoints is not None else []
            matched = match_boxes(list(pair), poses)
            keypoints = result.keypoints.data.tolist() if poses else []
            people.append(tuple(keypoints[matched[i]] if i in matched else None for i in (0, 1)))
        return judge_frames(people, boxes, self.max_angle_degrees, self.min_facing_fraction)
