"""Independent landmark and pair evaluation; never conflates synthetic and physical accuracy."""
from collections import defaultdict
import json

import numpy as np

from .floor_geometry import inside, project, validate_runtime


def statistics(errors):
    a = np.asarray(errors, float)
    if not len(a):
        return {"sample_count": 0, "mae_m": None, "median_absolute_error_m": None,
                "p95_absolute_error_m": None, "signed_bias_m": None}
    return {"sample_count": len(a), "mae_m": float(np.mean(np.abs(a))),
            "median_absolute_error_m": float(np.median(np.abs(a))),
            "p95_absolute_error_m": float(np.percentile(np.abs(a), 95)),
            "signed_bias_m": float(np.mean(a))}


def evaluate(cfg, annotations):
    validate_runtime(cfg, cfg["frame_size"])
    groups = defaultdict(lambda: {"point_radial_error_m": [], "point_x_error_m": [],
                                  "point_y_error_m": [], "pair_distance_error_m": []})
    rejected, accepted = 0, 0
    used_points = [np.asarray(p["image_xy_px"]) for p in cfg["landmarks"]]
    def accept_image(xy):
        nonlocal rejected
        if not inside(xy, cfg["operational_region_px"]):
            rejected += 1
            return False
        return True
    for kind in ("points", "pairs"):
        for row in annotations.get(kind, []):
            buckets = ["all", f'region:{row.get("region", "unlabelled")}',
                       f'visibility:{row.get("visibility", "unlabelled")}']
            if row.get("status", "observed_proxy") != "observed_proxy":
                rejected += 1
                continue
            if kind == "points":
                xy = row["image_xy_px"]
                if any(np.linalg.norm(np.asarray(xy) - fitted) < .01 for fitted in used_points):
                    raise ValueError("Withheld evaluation point repeats a fitting landmark")
                if not accept_image(xy):
                    continue
                error = np.asarray(project(cfg["H_image_to_floor"], xy)) - np.asarray(row["floor_xy_m"], float)
                if error.shape != (2,) or not np.isfinite(error).all():
                    raise ValueError("Invalid validation floor coordinates")
                for group in buckets:
                    groups[group]["point_radial_error_m"].append(float(np.linalg.norm(error)))
                    groups[group]["point_x_error_m"].append(float(error[0]))
                    groups[group]["point_y_error_m"].append(float(error[1]))
            else:
                a, b = row["image_a_px"], row["image_b_px"]
                if all(any(np.linalg.norm(np.asarray(xy) - fitted) < .01 for fitted in used_points) for xy in (a, b)):
                    raise ValueError("A separation between fitting landmarks is not independent validation")
                if not accept_image(a) or not accept_image(b):
                    continue
                known = float(row["known_distance_m"])
                if not np.isfinite(known) or known < 0:
                    raise ValueError("Known separation must be finite nonnegative metres")
                predicted = float(np.linalg.norm(np.asarray(project(cfg["H_image_to_floor"], a)) - project(cfg["H_image_to_floor"], b)))
                for group in buckets:
                    groups[group]["pair_distance_error_m"].append(predicted - known)
            accepted += 1
    count = accepted + rejected
    return {"calibration_id": cfg["calibration_id"], "reference_kind": annotations.get("reference_kind", "unverified"),
            "physical_validation": "pending" if annotations.get("reference_kind") != "independently_measured" else "measured_evaluation_only_review_results",
            "accepted_samples": accepted, "rejected_samples": rejected,
            "accepted_coverage": accepted / count if count else None, "rejection_rate": rejected / count if count else None,
            "groups": {name: {key: statistics(values) for key, values in data.items()} for name, data in groups.items()},
            "note": "Point radial errors have unsigned magnitude; signed bias is meaningful for point x/y and pair error separately. Fitting residuals are not physical validation."}


def metrics_coverage(path):
    statuses = defaultdict(int)
    pairs, supported = 0, 0
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            for position in row["positions"]:
                statuses[position["status"]] += 1
            for pair in row["distances"]:
                pairs += 1
                supported += pair["distance_m"] is not None
    total = sum(statuses.values())
    accepted = statuses.get("observed_proxy", 0)
    return {"position_status_counts": dict(statuses), "detections": total,
            "accepted_position_coverage": accepted / total if total else None,
            "rejection_rate": 1 - accepted / total if total else None,
            "pair_samples": pairs, "supported_pairs": supported}
