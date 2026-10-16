"""Image-plane geometry: +x right, +y down; radians clockwise from +x."""

import math

from .core import contains, head_direction
from .cv_contracts import Orientation


def iou(a, b):
    width = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    height = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    intersection = width * height
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
    return intersection / union if union > 0 else 0


def match_boxes(detections, poses, threshold=0.3):
    """Maximum-weight one-to-one assignment, with unmatched dummy nodes."""
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    if not detections or not poses:
        return {}
    weights = np.zeros((len(detections), len(poses) + len(detections)))
    for d, box in enumerate(detections):
        for p, pose in enumerate(poses):
            overlap = iou(box, pose)
            weights[d, p] = overlap if overlap >= threshold else -1
    rows, columns = linear_sum_assignment(weights, maximize=True)
    return {int(d): int(p) for d, p in zip(rows, columns) if p < len(poses) and weights[d, p] >= threshold}


def orientation_from_pose(keypoints, confidence=0.5):
    if any(len(point) != 3 or not all(math.isfinite(v) for v in point)
           or not 0 <= point[2] <= 1 for point in keypoints):
        return Orientation(reason="invalid_keypoints")
    vector, score = head_direction(keypoints, confidence)
    if vector is None:
        return Orientation(reason="weak_or_ambiguous_keypoints")
    return Orientation(state="known", vector=vector, confidence=score, reason=None)


def zone_at(point, zones):
    """First configured polygon wins; edges belong to that polygon."""
    for zone in zones:
        for a, b in zip(zone.polygon, zone.polygon[1:] + zone.polygon[:1]):
            cross = (point[0] - a[0]) * (b[1] - a[1]) - (point[1] - a[1]) * (b[0] - a[0])
            if abs(cross) < 1e-9 and min(a[0], b[0]) <= point[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= point[1] <= max(a[1], b[1]):
                return zone.name, zone.employee_prior
        if contains(point, zone.polygon):
            return zone.name, zone.employee_prior
    return "Unassigned", 0
