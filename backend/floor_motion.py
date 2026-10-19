"""Conservative reference alignment monitor. Does not compensate camera movement."""
import cv2
import numpy as np


class MotionMonitor:
    def __init__(self, reference, cfg, reference_detections=()):
        self.cfg = cfg
        self.orb = cv2.ORB_create(nfeatures=2000, edgeThreshold=10, fastThreshold=10)
        self.reference_shape = reference.shape[:2]
        self.keypoints, self.descriptors = self.features(reference, reference_detections)

    def features(self, frame, detections):
        mask = np.zeros(frame.shape[:2], np.uint8)
        cv2.fillPoly(mask, [np.asarray(self.cfg["operational_region_px"], np.int32)], 255)
        for polygon in self.cfg.get("exclusion_regions_px", []):
            cv2.fillPoly(mask, [np.asarray(polygon, np.int32)], 0)
        for d in detections:
            x1, y1, x2, y2 = [round(v) for v in d["bbox_xyxy_px"]]
            cv2.rectangle(mask, (x1-8, y1-8), (x2+8, y2+8), 0, -1)
        return self.orb.detectAndCompute(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), mask)

    def check(self, frame, detections):
        q = self.cfg["motion"]["quality"]
        result = {"status": "motion_unverified", "reason": "insufficient_static_floor_features",
                  "match_count": 0, "inliers": 0, "inlier_ratio": None,
                  "alignment_residual_px": None, "displacement_px": None,
                  "spread_ratio": None, "compensated": False}
        kp, desc = self.features(frame, detections)
        if desc is None or self.descriptors is None or len(desc) < 2 or len(self.descriptors) < 2:
            return result
        matches = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(desc, self.descriptors, k=2)
        good = [pair[0] for pair in matches if len(pair) == 2 and pair[0].distance < q["match_ratio"] * pair[1].distance]
        result["match_count"] = len(good)
        if len(good) < q["min_inliers"]:
            return result
        current = np.float32([kp[m.queryIdx].pt for m in good])
        ref = np.float32([self.keypoints[m.trainIdx].pt for m in good])
        transform, inliers = cv2.findHomography(current, ref, cv2.RANSAC, q["ransac_threshold_px"])
        if transform is None or inliers is None or not np.isfinite(transform).all():
            return result
        inliers = inliers.ravel().astype(bool)
        count, ratio = int(inliers.sum()), float(inliers.mean())
        result.update(inliers=count, inlier_ratio=ratio)
        if count < q["min_inliers"] or ratio < q["min_inlier_ratio"]:
            result["reason"] = "weak_match_consensus"
            return result
        area = cv2.contourArea(cv2.convexHull(ref[inliers]))
        region_area = cv2.contourArea(np.asarray(self.cfg["operational_region_px"], np.float32))
        spread = area / max(region_area, 1.)
        projected = cv2.perspectiveTransform(current[inliers, None, :], transform)[:, 0]
        residual = float(np.median(np.linalg.norm(projected - ref[inliers], axis=1)))
        # Evaluate displacement over the entire supported floor, not just one feature cluster.
        corners = np.float32(self.cfg["operational_region_px"])
        transformed = cv2.perspectiveTransform(corners[:, None, :], transform)[:, 0]
        displacement = float(np.max(np.linalg.norm(transformed - corners, axis=1)))
        result.update(alignment_residual_px=residual, displacement_px=displacement, spread_ratio=spread)
        if spread < q["min_spread_ratio"] or residual > q["max_alignment_residual_px"]:
            result["reason"] = "poor_spread_or_alignment"
        elif displacement > q["max_displacement_px"]:
            result.update(status="motion_invalid", reason="floor_alignment_shifted")
        else:
            result.update(status="aligned_provisional", reason="floor_matches_within_configured_tolerances")
        return result
