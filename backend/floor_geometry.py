"""Metre geometry and explicit quality states; no detector or rendering dependencies."""
import copy
import math

import cv2
import numpy as np


def points(value, minimum=4):
    a = np.asarray(value, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 2 or len(a) < minimum or not np.isfinite(a).all():
        raise ValueError(f"Require at least {minimum} finite 2D points")
    if len(np.unique(a, axis=0)) != len(a):
        raise ValueError("Duplicate landmarks")
    if len(a) >= 3:
        hull = cv2.convexHull(a.astype(np.float32))
        if cv2.contourArea(hull) < 1e-8:
            raise ValueError("Degenerate collinear geometry")
        if len(a) == 4:
            from itertools import combinations
            for ids in combinations(range(4), 3):
                b = a[list(ids)]
                if abs(np.linalg.det(np.column_stack([b, np.ones(3)]))) < 1e-8:
                    raise ValueError("Three calibration points are collinear")
    return a


def project(H_image_to_floor, xy):
    p = np.asarray(xy, dtype=float)
    h = np.asarray(H_image_to_floor, dtype=float)
    if h.shape != (3, 3) or p.shape != (2,) or not np.isfinite(h).all() or not np.isfinite(p).all():
        raise ValueError("Invalid projection inputs")
    q = h @ np.r_[p, 1.0]
    if not np.isfinite(q).all() or abs(q[2]) < 1e-10:
        raise ValueError("Invalid homogeneous denominator")
    result = q[:2] / q[2]
    if not np.isfinite(result).all():
        raise ValueError("Non-finite projection")
    return result.tolist()


def materialize_landmarks(config):
    """Derive floor points from editable measurements, never from a saved stale H."""
    cfg = copy.deepcopy(config)
    rectangle = cfg.get("rectangle")
    if rectangle:
        width = float(rectangle["width"])
        depth = float(rectangle["depth_or_diagonal"])
        factor = {"ft": .3048, "m": 1.0}.get(rectangle["units"])
        if factor is None or min(width, depth) <= 0:
            raise ValueError("Rectangle needs positive dimensions in ft or m")
        if rectangle["interpretation"] == "width_and_diagonal":
            if depth <= width:
                raise ValueError("Rectangle diagonal must exceed width")
            depth = math.sqrt(depth ** 2 - width ** 2)
        elif rectangle["interpretation"] != "width_and_depth":
            raise ValueError("Unknown rectangle interpretation")
        width, depth = width * factor, depth * factor
        # Explicit order around perimeter; the owner's labels may be A,B,D,C.
        coords = [[0, 0], [width, 0], [width, depth], [0, depth]]
        mapping = dict(zip(rectangle["corner_order"], coords))
        for landmark in cfg["landmarks"]:
            landmark["floor_xy_m"] = mapping[landmark["id"]]
        cfg["derived_rectangle_m"] = {"width": width, "depth": depth}
    return cfg


def fit_calibration(config):
    cfg = materialize_landmarks(config)
    if cfg.get("schema_version") != 1 or cfg.get("floor_units") != "m":
        raise ValueError("Require schema_version 1 and floor_units m")
    if cfg.get("coordinate_space") != "original_distorted_pixels":
        raise ValueError("Only original_distorted_pixels is supported; undistort both paths before extending this")
    if cfg.get("distortion", {}).get("handling") != "uncorrected":
        raise ValueError("Unsupported distortion handling")
    image = points([v["image_xy_px"] for v in cfg["landmarks"]])
    floor = points([v["floor_xy_m"] for v in cfg["landmarks"]])
    size = cfg["frame_size"]
    if len(size) != 2 or min(size) <= 0 or (image < 0).any() or (image >= np.asarray(size)).any():
        raise ValueError("Landmarks outside original frame geometry")
    threshold = float(cfg.get("quality", {}).get("ransac_threshold_px", 3))
    if threshold <= 0:
        raise ValueError("RANSAC pixel threshold must be positive")
    # Fit in pixels, then invert: threshold is pixels, never an implicit metre threshold.
    inverse, mask = cv2.findHomography(floor, image, cv2.RANSAC if len(image) > 4 else 0, threshold)
    if inverse is None or not np.isfinite(inverse).all() or abs(np.linalg.det(inverse)) < 1e-14:
        raise ValueError("Homography is singular or cannot be fit")
    H = np.linalg.inv(inverse)
    H /= np.linalg.norm(H)
    residual_m = [float(np.linalg.norm(np.asarray(project(H, a)) - b)) for a, b in zip(image, floor)]
    residual_px = [float(np.linalg.norm(np.asarray(project(inverse, a)) - b)) for a, b in zip(floor, image)]
    region = points(cfg["operational_region_px"], 3)
    if not cv2.isContourConvex(region.astype(np.float32)):
        raise ValueError("Operational region must be a convex polygon in perimeter order")
    calibrated_hull = cv2.convexHull(image.astype(np.float32))
    if any(cv2.pointPolygonTest(calibrated_hull, tuple(map(float, a)), True) < -.01 for a in region):
        raise ValueError("Operational region extends beyond calibrated landmark coverage")
    for a in region:
        project(H, a)
    denominators = np.column_stack([region, np.ones(len(region))]) @ H[2]
    if denominators.min() * denominators.max() <= 0:
        raise ValueError("Homography horizon crosses the operational region")
    cfg["H_direction"] = "image_to_floor"
    cfg["H_image_to_floor"] = H.tolist()
    cfg["fit"] = {"inliers": mask.ravel().astype(bool).tolist(), "residual_m": residual_m,
                  "residual_px": residual_px, "ransac_threshold_px": threshold,
                  "note": "Training landmark residuals are not independent accuracy"}
    cfg.setdefault("independent_validation", {"status": "pending", "sample_count": 0})
    cfg["calibration_status"] = "provisional" if cfg.get("measurements_status") != "verified" else "unvalidated"
    return cfg


def validate_runtime(cfg, size):
    if cfg.get("measurements_status") == "illustrative":
        raise ValueError("Illustrative configuration cannot be used as actual calibration")
    if list(size) != cfg["frame_size"]:
        raise ValueError(f"Frame/config mismatch: {size} vs {cfg['frame_size']}; regenerate calibration")
    if cfg.get("H_direction") != "image_to_floor":
        raise ValueError("Wrong homography direction")
    # Refit so edits to landmarks/dimensions cannot leave a stale matrix active.
    fresh = fit_calibration(cfg)
    if not np.allclose(fresh["H_image_to_floor"], cfg["H_image_to_floor"], atol=1e-8):
        raise ValueError("Calibration inputs changed; rerun calibrate_floor.py to regenerate H")


def inside(xy, polygon):
    return cv2.pointPolygonTest(np.asarray(polygon, np.float32), tuple(map(float, xy)), False) >= 0


def position(detection, cfg, size, motion_status="motion_unverified", detections=()):
    result = {"floor_xy_m": None, "status": "unreliable", "reason": None,
              "position_reliability": "unsupported", "approximate": True}
    if cfg is None:
        result.update(status="uncalibrated", reason="calibration_missing")
        return result
    b = np.asarray(detection["bbox_xyxy_px"], float)
    if b.shape != (4,) or not np.isfinite(b).all() or b[2] <= b[0] or b[3] <= b[1]:
        result["reason"] = "invalid_box"
        return result
    foot = [(b[0] + b[2]) / 2, b[3]]
    if b[0] < 0 or b[1] < 0 or b[2] > size[0] or b[3] > size[1]:
        result["reason"] = "box_outside_frame"
    elif b[3] >= size[1] - cfg.get("quality", {}).get("bottom_margin_px", 4):
        result["reason"] = "lower_frame_truncation"
    elif any(inside(foot, p) for p in cfg.get("exclusion_regions_px", [])):
        result["reason"] = "manual_foot_exclusion"
    elif any(other is not detection and other["bbox_xyxy_px"][0] < foot[0] < other["bbox_xyxy_px"][2]
             and other["bbox_xyxy_px"][1] < foot[1] < other["bbox_xyxy_px"][3] for other in detections):
        result["reason"] = "foot_overlapped_by_person"
    elif not inside(foot, cfg["operational_region_px"]):
        result.update(status="out_of_region", reason="outside_calibrated_coverage")
    elif motion_status not in {"reference_frame", "aligned_provisional"}:
        result.update(status="motion_invalid" if motion_status == "motion_invalid" else "motion_unverified",
                      reason="reference_alignment_not_supported")
    else:
        try:
            result.update(floor_xy_m=project(cfg["H_image_to_floor"], foot), status="observed_proxy",
                          position_reliability="bbox_bottom_proxy", reason=None)
        except ValueError as exc:
            result["reason"] = str(exc)
    return result


def pair_distance(a, b):
    result = {"distance_m": None, "status": "unavailable", "reason": None, "approximate": True}
    if a["camera_id"] != b["camera_id"] or a["timestamp_s"] != b["timestamp_s"]:
        result["reason"] = "camera_or_timestamp_mismatch"
    elif any(p.get("status") != "observed_proxy" or p.get("floor_xy_m") is None for p in (a, b)):
        result["reason"] = "unsupported_position"
    else:
        xy_a, xy_b = np.asarray(a["floor_xy_m"], float), np.asarray(b["floor_xy_m"], float)
        if xy_a.shape != (2,) or xy_b.shape != (2,) or not np.isfinite([xy_a, xy_b]).all():
            result["reason"] = "invalid_metric_coordinates"
        else:
            result.update(distance_m=float(np.linalg.norm(xy_a - xy_b)),
                          status="approximate", reason="provisional_calibration_and_bbox_proxy")
    return result


def restore_box(box, scale_xy, pad_xy=(0, 0)):
    """For future adapters. Ultralytics xyxy is already restored: never call it twice."""
    scale = np.asarray(scale_xy, float)
    if scale.shape != (2,) or not np.isfinite(scale).all() or min(scale) <= 0:
        raise ValueError("Invalid preprocessing scale")
    return ((np.asarray(box).reshape(2, 2) - np.asarray(pad_xy)) / scale).ravel().tolist()
