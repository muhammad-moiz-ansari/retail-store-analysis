"""Deterministic role, geometry, and temporal logic, independent of CV models."""

import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from .schemas import CameraConfig


def normalized(values):
    length = math.sqrt(sum(float(x) ** 2 for x in values))
    if not length or not math.isfinite(length):
        raise ValueError("Embedding must be finite and nonzero")
    return [float(x) / length for x in values]


def prototype(vectors):
    if not vectors or len({len(v) for v in vectors}) != 1:
        raise ValueError("Reference embeddings must have matching dimensions")
    return normalized([sum(xs) / len(vectors) for xs in zip(*(normalized(v) for v in vectors))])


def cosine(a, b):
    if len(a) != len(b):
        raise ValueError("Embedding dimensions differ")
    return sum(x * y for x, y in zip(normalized(a), normalized(b)))


def contains(point, polygon):
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        if (a[1] > y) != (b[1] > y):
            if x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
                inside = not inside
    return inside


def classify(embedding, calibration, config, zone_prior=0, dwell=0):
    if not calibration:
        return {"role": "unknown", "confidence": 0, "evidence": {}}
    scores = {role: cosine(embedding, calibration["prototypes"][role]) for role in ("employee", "customer")}
    prior = config.prior_weight * (zone_prior + min(1, dwell / config.dwell_seconds)) / 2
    margin = scores["employee"] - scores["customer"] + prior
    role = "employee" if margin > 0 else "customer"
    known = scores[role] >= config.role_similarity and abs(margin) >= config.role_margin
    return {"role": role if known else "unknown", "confidence": round(max(0, min(1, abs(margin))), 4),
            "evidence": {**scores, "prior": prior, "margin": margin}}


def head_direction(keypoints, min_confidence=0.5):
    # COCO nose relative to the ear midpoint is a conservative head-facing proxy.
    # Shoulders alone have a front/back ambiguity and cannot establish facing.
    if len(keypoints) < 5:
        return None, 0.0
    nose, left, right = (keypoints[i] for i in (0, 3, 4))
    confidence = min(nose[2], left[2], right[2])
    if confidence < min_confidence:
        return None, confidence
    vector = (nose[0] - (left[0] + right[0]) / 2, nose[1] - (left[1] + right[1]) / 2)
    span = math.hypot(left[0] - right[0], left[1] - right[1])
    if span < 2 or math.hypot(*vector) < max(2, span * 0.15):
        return None, 0.0
    return tuple(normalized(vector)), confidence


@dataclass
class Observation:
    track_id: str
    role: str
    position: tuple[float, float]
    facing: tuple[float, float] | None = None
    orientation_confidence: float = 0
    zone: str = "Unassigned"


def pair_qualifies(employee, customer, config):
    delta = tuple(b - a for a, b in zip(employee.position, customer.position))
    distance = math.hypot(*delta)
    if distance <= 1e-8 or distance > config.distance_threshold:
        return False
    threshold = math.cos(math.radians(config.facing_angle_degrees))
    for person, sign in ((employee, 1), (customer, -1)):
        if person.facing is None or person.orientation_confidence < config.orientation_confidence:
            return False
        facing = normalized(person.facing)
        if sum(f * d * sign / distance for f, d in zip(facing, delta)) < threshold:
            return False
    return True


class EventEngine:
    def __init__(self, job_id, store_id, camera_id, start_time, shift, calibration_version,
                 config: CameraConfig):
        self.job_id, self.store_id, self.camera_id = job_id, store_id, camera_id
        self.start_time = datetime.fromisoformat(start_time)
        self.shift, self.version, self.config = shift, calibration_version, config
        self.pairs = {}
        self.last_time = -1.0

    def _finish(self, pair):
        duration = pair["last"] - pair["start"]
        if duration + 1e-8 < self.config.min_duration_seconds:
            return None
        identity = f'{self.job_id}:{pair["employee"]}:{pair["customer"]}:{pair["start"]:.6f}'
        return {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, identity)), "event_type": "engagement",
                "job_id": self.job_id, "store_id": self.store_id, "camera_id": self.camera_id,
                "employee_track_id": pair["employee"], "customer_track_id": pair["customer"],
                "employee_zone": pair["zone"], "employee_shift": self.shift,
                "start_time": (self.start_time + timedelta(seconds=pair["start"])).isoformat(),
                "end_time": (self.start_time + timedelta(seconds=pair["last"])).isoformat(),
                "duration_seconds": round(duration, 3), "calibration_version": self.version,
                "orientation_method": "nose-ear-proxy"}

    def update(self, timestamp, observations):
        if not math.isfinite(timestamp) or timestamp < 0 or timestamp <= self.last_time:
            raise ValueError("Observation timestamps must strictly increase")
        self.last_time = timestamp
        qualifying = {}
        for employee in (o for o in observations if o.role == "employee"):
            for customer in (o for o in observations if o.role == "customer"):
                if pair_qualifies(employee, customer, self.config):
                    qualifying[(employee.track_id, customer.track_id)] = employee
        events = []
        for key, pair in list(self.pairs.items()):
            if (key not in qualifying or timestamp - pair["last"] > self.config.max_observation_gap_seconds
                    or qualifying[key].zone != pair["zone"]):
                event = self._finish(self.pairs.pop(key))
                if event:
                    events.append(event)
        for key, employee in qualifying.items():
            pair = self.pairs.setdefault(key, {"employee": key[0], "customer": key[1],
                                              "zone": employee.zone, "start": timestamp})
            pair["last"] = timestamp
        return events

    def flush(self):
        events = [event for pair in self.pairs.values() if (event := self._finish(pair))]
        self.pairs.clear()
        return events
