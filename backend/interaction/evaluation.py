"""Detection/tracking/role/orientation evaluation; no implicit quality approval."""

import math
from collections import Counter, defaultdict

from .geometry import match_boxes


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def evaluate_frames(truth, predictions, angle_tolerance=45):
    """Truth frames include every annotated time, including failures/missing predictions.

    Frame key: (source_id, source_seconds). Truth person fields: bbox, track_id,
    role, orientation (unit vector or null). Prediction fields follow FrameResult.
    Unknown GT role/orientation is excluded from accuracy denominators.
    """
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    def key(frame):
        return frame["source_id"], round(frame["source_seconds"], 6)

    gt_by_key, pred_by_key = {}, {}
    for frames, index in ((truth, gt_by_key), (predictions, pred_by_key)):
        for frame in frames:
            if key(frame) in index:
                raise ValueError("Duplicate evaluation frame")
            index[key(frame)] = frame
    if set(pred_by_key) - set(gt_by_key):
        raise ValueError("Predictions include unannotated times; select the evaluation grid explicitly")
    detections_tp = detections_total = gt_total = tracked_total = 0
    roles = {role: Counter() for role in ("employee", "customer")}
    role_eligible = role_unknown = orientation_eligible = orientation_available = orientation_correct = 0
    identity_counts, gt_counts, pred_counts = Counter(), Counter(), Counter()
    prior_match, ever_matched = {}, set()
    fragments = switches = 0
    for frame_key, frame in sorted(gt_by_key.items()):
        people = frame["people"]
        prediction = pred_by_key.get(frame_key, {})
        observations = prediction.get("observations", []) if prediction.get("status", "analyzed") == "analyzed" else []
        detections = prediction.get("detections", []) if prediction.get("status", "analyzed") == "analyzed" else []
        gt_boxes = [p["bbox"] for p in people]
        detections_tp += len(match_boxes(gt_boxes, [p["bbox"] for p in detections], 0.5))
        detections_total += len(detections)
        gt_total += len(people)
        tracked_total += len(observations)
        matches = match_boxes(gt_boxes, [p["bbox"] for p in observations], 0.5)
        for obs in observations:
            pred_counts[(frame_key[0], obs["track_id"])] += 1
        for index, person in enumerate(people):
            identity = (frame_key[0], person["track_id"])
            gt_counts[identity] += 1
            obs = observations[matches[index]] if index in matches else None
            current = (frame_key[0], obs["track_id"]) if obs else None
            if current:
                identity_counts[identity, current] += 1
                if identity in ever_matched and prior_match.get(identity) is None:
                    fragments += 1
                if prior_match.get(identity) and prior_match[identity] != current:
                    switches += 1
                ever_matched.add(identity)
            prior_match[identity] = current
            actual_role = person.get("role", "unknown")
            predicted_role = obs.get("role", "unknown") if obs else "unknown"
            if actual_role in roles:
                role_eligible += 1
                role_unknown += predicted_role == "unknown"
                for role, counts in roles.items():
                    counts["tp"] += actual_role == predicted_role == role
                    counts["fp"] += predicted_role == role and actual_role != role
                    counts["fn"] += actual_role == role and predicted_role != role
            actual_vector = person.get("orientation")
            if actual_vector is not None:
                if len(actual_vector) != 2 or not math.isclose(math.hypot(*actual_vector), 1, abs_tol=1e-5):
                    raise ValueError("Annotation facing vectors must be unit length")
                orientation_eligible += 1
                estimate = obs.get("orientation", {}) if obs else {}
                if estimate.get("state") == "known":
                    orientation_available += 1
                    vector = estimate["vector"]
                    if not math.isclose(math.hypot(*vector), 1, abs_tol=1e-5):
                        raise ValueError("Prediction facing vectors must be unit length")
                    dot = sum(a * b for a, b in zip(actual_vector, vector))
                    orientation_correct += dot >= math.cos(math.radians(angle_tolerance)) - 1e-8
    gt_ids, pred_ids = list(gt_counts), list(pred_counts)
    matrix = np.zeros((len(gt_ids), len(pred_ids)))
    for g, identity in enumerate(gt_ids):
        for p, predicted in enumerate(pred_ids):
            matrix[g, p] = identity_counts[identity, predicted]
    rows, columns = linear_sum_assignment(matrix, maximize=True)
    idtp = int(matrix[rows, columns].sum())
    return {"schema_version": 1, "annotated_frames": len(truth), "annotated_people": gt_total,
            "detection": {"precision": ratio(detections_tp, detections_total), "recall": ratio(detections_tp, gt_total)},
            "tracking": {"idf1": ratio(2 * idtp, gt_total + tracked_total), "fragmentations": fragments, "id_switches": switches},
            "roles": {role: {"precision": ratio(c["tp"], c["tp"] + c["fp"]),
                              "recall": ratio(c["tp"], c["tp"] + c["fn"])} for role, c in roles.items()},
            "unknown_role_rate": ratio(role_unknown, role_eligible), "role_denominator": role_eligible,
            "orientation": {"accuracy": ratio(orientation_correct, orientation_available),
                            "availability": ratio(orientation_available, orientation_eligible),
                            "eligible": orientation_eligible, "available": orientation_available}}


def evaluate_slices(truth, predictions):
    report = evaluate_frames(truth, predictions)
    slices = defaultdict(list)
    for frame in truth:
        slices["camera:" + frame["camera_id"]].append(frame)
        for condition in frame.get("conditions", []):
            slices["condition:" + condition].append(frame)
    report["slices"] = {}
    for name, frames in slices.items():
        keys = {(f["source_id"], round(f["source_seconds"], 6)) for f in frames}
        report["slices"][name] = evaluate_frames(frames, [p for p in predictions if (p["source_id"], round(p["source_seconds"], 6)) in keys])
    return report


def quality_gate(report, specification):
    reasons = []
    required = {"annotated_frames", "annotated_people", "detection.precision", "detection.recall",
                "tracking.idf1", "roles.employee.precision", "roles.employee.recall",
                "roles.customer.precision", "roles.customer.recall", "unknown_role_rate",
                "orientation.accuracy", "orientation.availability", "orientation.eligible"}
    limits = specification.get("limits", {})
    if not specification.get("approved_by") or not specification.get("version"):
        reasons.append("Evaluation protocol has not been approved")
    if not required.issubset(limits):
        reasons.append("Required sample sizes or quality thresholds are missing")
    for name in required:
        value = report
        for part in name.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        limit = limits.get(name)
        if value is None or not isinstance(limit, (int, float)) or not math.isfinite(limit):
            reasons.append(f"Insufficient evidence/threshold: {name}")
        elif (value > limit if name == "unknown_role_rate" else value < limit):
            reasons.append(f"Threshold failed: {name}")
    return {"status": "failed_or_insufficient" if reasons else "passed", "reasons": reasons,
            "specification_version": specification.get("version")}
