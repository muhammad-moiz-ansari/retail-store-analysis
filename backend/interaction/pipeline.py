"""Interaction pipelines: standalone YOLO+ByteTrack engagement and streaming Track A handoff."""

from __future__ import annotations

import math
import time
import uuid
from collections import deque
from datetime import timedelta, timezone
from pathlib import Path

import numpy as np

from .config import InteractionConfig
from .cv_contracts import FrameResult, Orientation, Signal, TrackObservation
from .engagement import EngagementDetector
from .geometry import match_boxes, orientation_from_pose, zone_at
from .identity import EphemeralIdentityRegistry
from .pose import PoseJudge
from .role_classifier import RoleClassifier
from .tracker import ByteTrackPersonTracker
from .types import CONFIRMED, TrackedPerson


class InteractionPipeline:
    def __init__(self, config: InteractionConfig | None = None) -> None:
        self.config = config or InteractionConfig()
        from ultralytics import YOLO  # lazy: importing package does not require ML dependencies

        person_model = Path(self.config.person_model)
        if self.config.device != "cpu" and "openvino" in person_model.name:
            person_model = person_model.with_name("best.pt")  # OpenVINO runs on CPU only; the GPU takes the .pt
        self.person_model = YOLO(str(person_model), task="detect")
        role_model = YOLO(str(self.config.role_model)) if self.config.role_model and Path(self.config.role_model).is_file() else None
        self.tracker = ByteTrackPersonTracker(self.person_model, self.config)
        self.classifier = RoleClassifier(self.config, role_model)
        self.engagement = EngagementDetector(self.config)
        self.judge = PoseJudge(self.config.pose_model, self.config.judge_device or self.config.device,
                               self.config.facing_angle_degrees, self.config.min_facing_fraction) \
            if self.config.interaction_judge == "pose" else None
        self._recent: deque[tuple[float, np.ndarray, dict[int, tuple[int, int, int, int]]]] = deque()
        self._verdicts: dict[tuple[int, int, float], dict] = {}

    def process_frame(self, frame: np.ndarray, timestamp: float | None = None) -> dict:
        timestamp = time.time() if timestamp is None else timestamp
        people = [
            TrackedPerson(
                track_id=item["track_id"], bbox=item["bbox"], confidence=item["confidence"],
                role=role, role_confidence=role_confidence, role_evidence=evidence,
            )
            for item in self.tracker.detect_and_track(frame, timestamp)
            for role, role_confidence, evidence in [
                self.classifier.classify(frame, item["bbox"], item["track_id"], timestamp, self._tracked_role(item))
            ]
        ]
        events = self.engagement.update(people, timestamp, frame.shape[0])
        if self.judge:
            self._recent.append((timestamp, frame, {person.track_id: person.bbox for person in people}))
            while self._recent[0][0] < timestamp - self.config.min_interaction_seconds:
                self._recent.popleft()
            for event in events:
                self._judge(event, timestamp)
        employees = sum(person.role == "employee" for person in people)
        customers = len(people) - employees
        return {
            "timestamp": timestamp,
            "people": [person.to_dict() for person in people],
            "employee_count": employees,
            "customer_count": customers,
            # Every proximity candidate, with the judge's verdict; only CONFIRMED ones count as interactions.
            "interactions": [{**event.to_dict(), "verdict": self.verdict(event)} for event in events],
            # On while any employee/customer interaction past min_interaction_seconds is ongoing.
            "interaction_active": any(event.active and self.verdict(event) in CONFIRMED for event in events),
        }

    @staticmethod
    def _key(event) -> tuple[int, int, float]:
        return event.employee_track_id, event.customer_track_id, event.started_at

    def verdict(self, event) -> str:
        """interaction | no_interaction | unverified (judge off, failed or unsure)."""
        state = self._verdicts.get(self._key(event))
        return state["label"] if state else "unverified"

    def _judge(self, event, timestamp: float) -> None:
        # Synchronous on purpose: a judge on a background thread slowed every later detector frame ~2x
        # (thread-pool contention, torch or OpenVINO alike); inline it costs ~250 ms once per candidate.
        state = self._verdicts.get(self._key(event))
        recheck = state and state["label"] == "no_interaction" and timestamp - state["checked_at"] >= self.config.judge_recheck_seconds
        if state and not recheck:
            return
        crops, boxes = self._pair_crops(event)
        if not crops:
            return
        try:
            label = self.judge.classify_interaction(crops, boxes).label
        except Exception:  # a broken judge must not lose the proximity result
            label = "unknown"
        self._verdicts[self._key(event)] = {"label": "unverified" if label == "unknown" else label, "checked_at": timestamp}

    def _pair_crops(self, event) -> tuple[list[np.ndarray], list]:
        """judge_frames frames spread over the buffered window, cropped to both people with some context,
        and the (employee, customer) boxes in crop coordinates."""
        ids = (event.employee_track_id, event.customer_track_id)
        window = [(frame, boxes) for _, frame, boxes in self._recent if all(i in boxes for i in ids)]
        count = min(self.config.judge_frames, len(window))
        crops, pair_boxes = [], []
        for frame, boxes in (window[round(i * (len(window) - 1) / max(1, count - 1))] for i in range(count)):
            x1, y1 = min(boxes[i][0] for i in ids), min(boxes[i][1] for i in ids)
            x2, y2 = max(boxes[i][2] for i in ids), max(boxes[i][3] for i in ids)
            margin, (height, width) = int(0.15 * (y2 - y1)), frame.shape[:2]
            left, top = max(0, x1 - margin), max(0, y1 - margin)
            crops.append(frame[top:min(height, y2 + margin), left:min(width, x2 + margin)].copy())
            pair_boxes.append(tuple((b[0] - left, b[1] - top, b[2] - left, b[3] - top) for b in (boxes[ids[0]], boxes[ids[1]])))
        return crops, pair_boxes

    def _tracked_role(self, item: dict) -> tuple[str, float] | None:
        """Role straight from the tracking model's class, when it is a role model (e.g. best.pt)."""
        if item.get("label") in self.config.role_model_employee_labels:
            return "employee", item["confidence"]
        if item.get("label") in self.config.role_model_customer_labels:
            return "customer", item["confidence"]
        return None


class FrameProcessor:
    def __init__(self, models, store_id, config, calibration=None, session_id=None,
                 utc_anchor=None, shift_at=None, identity_registry=None):
        self.models, self.store_id, self.config = models, store_id, config.model_copy(deep=True)
        self.session_id = session_id or uuid.uuid4().hex
        if utc_anchor is not None and utc_anchor.utcoffset() is None:
            raise ValueError("UTC anchor must include timezone")
        self.anchor = utc_anchor.astimezone(timezone.utc) if utc_anchor else None
        self.shift_at = shift_at or (lambda timestamp: "Unassigned")
        # Calibration is accepted for wire compatibility only. Appearance is
        # identity/Re-ID evidence and never an employee/customer role source.
        self.calibration = calibration.model_copy(deep=True) if calibration else None
        self.identities = identity_registry or EphemeralIdentityRegistry()
        self.tracker = models.create_tracker()
        self.tracks = {}
        self.last_time = None

    def utc(self, seconds):
        return self.anchor + timedelta(seconds=seconds) if self.anchor else None

    def process(self, frame):
        timestamp = frame.seconds
        if not math.isfinite(timestamp) or timestamp < 0 or (self.last_time is not None and timestamp <= self.last_time):
            raise ValueError("Frame timestamps must strictly increase")
        gap = timestamp - self.last_time if self.last_time is not None else 0
        self.last_time = timestamp
        started = time.perf_counter()
        base = dict(store_id=self.store_id, camera_id=self.config.camera_id, session_id=self.session_id,
                    source_seconds=timestamp, utc_time=self.utc(timestamp), models=self.models.metadata,
                    calibration_version=None,
                    source_gap_seconds=gap, skipped_frames=frame.skipped)
        # Tracker state must not link people through an acquisition/processing outage.
        if gap > self.config.max_observation_gap_seconds:
            self.tracker = self.models.create_tracker()
            self.tracks.clear()
        try:
            h, w = frame.image.shape[:2]
            detections = self.models.track(frame.image, self.tracker)
            poses = self.models.poses(frame.image)
            matches = match_boxes([d["bbox"] for d in detections], [p["bbox"] for p in poses])
            observations = []
            samples = []
            for local, state in list(self.tracks.items()):
                if timestamp - state["last_seen"] > self.config.max_observation_gap_seconds:
                    del self.tracks[local]
            for index, detection in enumerate(detections):
                bbox = detection["bbox"]
                if len(bbox) != 4 or not all(math.isfinite(v) for v in bbox):
                    raise ValueError("Invalid model box")
                x1, y1 = max(0, min(w, bbox[0])), max(0, min(h, bbox[1]))
                x2, y2 = max(0, min(w, bbox[2])), max(0, min(h, bbox[3]))
                if x1 >= x2 or y1 >= y2:
                    raise ValueError("Degenerate model box")
                local = detection["local_id"]
                state = self.tracks.get(local)
                first_seen = state is None or timestamp - state["last_seen"] > self.config.max_observation_gap_seconds
                if first_seen:
                    person = self.identities.resolve_track(
                        self.store_id, self.session_id, self.config.camera_id, str(local)
                    )
                    state = {"id": self.session_id + ":" + uuid.uuid4().hex, "first_seen": timestamp,
                             "global_person_id": person["global_person_id"],
                             "last_embedding": -math.inf, "samples": [], "last_seen": timestamp}
                    self.tracks[local] = state
                state["last_seen"] = timestamp
                crop = frame.image[int(y1):math.ceil(y2), int(x1):math.ceil(x2)]
                valid_crop = min(crop.shape[:2]) >= 16 and detection["confidence"] >= 0.5
                if valid_crop and timestamp - state["last_embedding"] >= 1 - 1e-8:
                    vector = self.models.embed(crop)
                    state["last_embedding"] = timestamp
                    if len(state["samples"]) < 10:
                        state["samples"].append(vector)
                        samples.append({"track_id": state["id"], "camera_id": self.config.camera_id,
                                        "source_seconds": timestamp, "bbox": [x1, y1, x2, y2],
                                        "embedding": vector, "sample_number": len(state["samples"])})
                zone, _prior = zone_at(((x1 + x2) / (2 * w), (y1 + y2) / (2 * h)), self.config.zones)
                if first_seen:
                    person = self.identities.apply_customer_entry(
                        self.store_id,
                        state["global_person_id"],
                        {"camera_id": self.config.camera_id, "event": "first_seen", "zone": zone},
                        self.config.customer_entry_rules,
                    )
                else:
                    person = self.identities.get_person(self.store_id, state["global_person_id"])
                role = person["role"]
                reason = None if role != "unknown" else "unresolved_global_identity"
                orientation = Orientation(reason="unmatched_pose")
                if index in matches:
                    orientation = orientation_from_pose(poses[matches[index]]["keypoints"], self.config.orientation_confidence)
                if valid_crop and hasattr(self.models, "crop_orientation"):
                    orientation = self.models.crop_orientation(crop, self.config.orientation_confidence) or orientation
                observations.append(TrackObservation(session_id=self.session_id, track_id=state["id"],
                    global_person_id=state["global_person_id"],
                    source_seconds=timestamp, utc_time=self.utc(timestamp), bbox=(x1, y1, x2, y2), source_size=(w, h),
                    detection_confidence=detection["confidence"], role=role, role_evidence={}, role_reason=reason,
                    orientation=orientation, zone=zone, shift=self.shift_at(self.utc(timestamp))))
            return FrameResult(**base, observations=observations, review_samples=samples,
                               detections=getattr(self.models, "last_detections", detections),
                               processing_seconds=time.perf_counter() - started)
        except Exception as exc:
            # A failed frame is observable evidence loss, never a successful empty frame.
            self.tracker = self.models.create_tracker()
            self.tracks.clear()
            return FrameResult(**base, status="failed", reason=type(exc).__name__,
                               processing_seconds=time.perf_counter() - started)

def process_recording(processor, frames, cancelled=lambda: False):
    """Yield typed records. Exactly one terminal signal follows a started session."""
    yield Signal(kind="session_started", camera_id=processor.config.camera_id,
                 session_id=processor.session_id, utc_time=processor.anchor)
    reason = "eof"
    try:
        for frame in frames:
            if cancelled():
                reason = "cancelled"
                break
            yield processor.process(frame)
    except Exception as exc:
        reason = "media_error:" + type(exc).__name__
    finally:
        if hasattr(frames, "close"):
            frames.close()
    yield Signal(kind="session_ended", camera_id=processor.config.camera_id,
                 session_id=processor.session_id, source_seconds=processor.last_time,
                 reason=reason, utc_time=processor.utc(processor.last_time) if processor.last_time is not None else None)
