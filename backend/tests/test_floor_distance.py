import copy
import json
from pathlib import Path
import unittest

import cv2
import numpy as np

from backend.floor_geometry import fit_calibration, pair_distance, position, project, restore_box, validate_runtime
from backend.floor_evaluation import evaluate, statistics
from backend.floor_motion import MotionMonitor
from backend.floor_tracking import PositionSmoother


def config():
    cfg = json.loads((Path(__file__).resolve().parents[2] / "config/cameras/floor_example.json").read_text())
    cfg["measurements_status"] = "estimated"
    return fit_calibration(cfg)


def detection(box=None, track=1):
    return {"bbox_xyxy_px": box or [280, 210, 320, 300], "track_id": track, "role": "customer"}


class GeometryTests(unittest.TestCase):
    def test_known_perspective_and_distance(self):
        H = [[.01, 0, 0], [0, .02, 0], [0, .001, 1]]
        np.testing.assert_allclose(project(H, [200, 100]), [2/1.1, 2/1.1])
        a = {"camera_id": "a", "timestamp_s": 1, "floor_xy_m": [0,0], "status": "observed_proxy"}
        b = {**a, "floor_xy_m": [3,4]}
        self.assertEqual(pair_distance(a,b)["distance_m"], 5)

    def test_rectangle_fit_and_units(self):
        cfg = config()
        for p in cfg["landmarks"]:
            np.testing.assert_allclose(project(cfg["H_image_to_floor"], p["image_xy_px"]), p["floor_xy_m"], atol=1e-6)
        cfg["rectangle"].update(width=3.13225, depth_or_diagonal=4.2075, units="ft")
        cfg = fit_calibration(cfg)
        self.assertAlmostEqual(cfg["derived_rectangle_m"]["width"], .9547098)
        self.assertAlmostEqual(cfg["derived_rectangle_m"]["depth"], 1.282446)

    def test_duplicates_and_collinearity(self):
        for xy in ([[1,1],[1,1],[2,2],[3,4]], [[1,1],[2,2],[3,3],[4,4]], [[1,1],[2,2],[3,3],[4,2]]):
            cfg = config()
            for p, point in zip(cfg["landmarks"], xy):
                p["image_xy_px"] = point
            with self.assertRaises(ValueError):
                fit_calibration(cfg)

    def test_invalid_projection(self):
        for H, xy in ((np.zeros((3,3)), [1,2]), (np.eye(3), [np.nan,0]), (np.eye(2), [1,2])):
            with self.assertRaises(ValueError):
                project(H, xy)

    def test_runtime_geometry_and_stale_config(self):
        cfg = config()
        validate_runtime(cfg, [640,480])
        with self.assertRaises(ValueError):
            validate_runtime(cfg, [1280,960])
        cfg["rectangle"]["width"] = 3
        with self.assertRaises(ValueError):
            validate_runtime(cfg, [640,480])

    def test_unit_direction_and_coordinate_guards(self):
        for key, value in (("floor_units", "ft"), ("coordinate_space", "normalized")):
            cfg = config()
            cfg[key] = value
            with self.assertRaises(ValueError):
                fit_calibration(cfg)
        cfg = config()
        cfg["H_direction"] = "floor_to_image"
        with self.assertRaises(ValueError):
            validate_runtime(cfg, [640,480])
        cfg = config()
        cfg["measurements_status"] = "illustrative"
        with self.assertRaises(ValueError):
            validate_runtime(cfg, [640,480])

    def test_region_and_lower_frame(self):
        cfg = config()
        self.assertEqual(position(detection([0,0,30,50]), cfg,[640,480],"reference_frame")["status"], "out_of_region")
        self.assertEqual(position(detection([200,200,300,479]), cfg,[640,480],"reference_frame")["reason"], "lower_frame_truncation")
        cfg["operational_region_px"] = [[0,0],[639,0],[639,479],[0,479]]
        with self.assertRaises(ValueError):
            fit_calibration(cfg)

    def test_occlusion_manual_and_motion_states(self):
        cfg = config()
        d = detection()
        self.assertEqual(position(d,cfg,[640,480],"reference_frame")["status"], "observed_proxy")
        self.assertIsNone(position(d,cfg,[640,480],"motion_invalid")["floor_xy_m"])
        self.assertIsNone(position(d,cfg,[640,480],"motion_unverified")["floor_xy_m"])
        other = detection([250,250,350,350],2)
        self.assertEqual(position(d,cfg,[640,480],"reference_frame",[d,other])["reason"], "foot_overlapped_by_person")
        cfg["exclusion_regions_px"] = [[[250,250],[350,250],[350,350],[250,350]]]
        self.assertEqual(position(d,cfg,[640,480],"reference_frame")["reason"], "manual_foot_exclusion")

    def test_invalid_box_and_predicted_pair(self):
        self.assertEqual(position(detection(),None,[640,480])["status"],"uncalibrated")
        for box in ([10,10,0,0], [1,2,np.nan,4]):
            self.assertIsNone(position(detection(box), config(),[640,480],"reference_frame")["floor_xy_m"])
        a = {"camera_id":"a", "timestamp_s":1, "floor_xy_m":[1,2], "status":"predicted"}
        self.assertIsNone(pair_distance(a,a)["distance_m"])
        b = {**a,"timestamp_s":2,"status":"observed_proxy"}
        self.assertEqual(pair_distance(a,b)["reason"],"camera_or_timestamp_mismatch")
        b.update(timestamp_s=1,floor_xy_m=[np.nan,0])
        a["status"] = "observed_proxy"
        self.assertEqual(pair_distance(a,b)["reason"],"invalid_metric_coordinates")

    def test_letterbox_and_resize_recovery(self):
        np.testing.assert_allclose(restore_box([60,120,110,220], [.5,.5], [10,20]), [100,200,200,400])
        np.testing.assert_allclose(restore_box([100,100,200,200], [.5,.25]), [200,400,400,800])

    def test_more_than_four_robust_pixel_fit(self):
        cfg = config()
        cfg.pop("rectangle")
        H = cfg["H_image_to_floor"]
        for i, xy in enumerate([[200,300],[300,300],[400,300],[300,350],[250,250],[350,250]]):
            cfg["landmarks"].append({"id":f"extra{i}","image_xy_px":xy,"floor_xy_m":project(H,xy)})
        cfg["landmarks"][-1]["image_xy_px"] = [600,20]
        fitted = fit_calibration(cfg)
        self.assertFalse(fitted["fit"]["inliers"][-1])
        np.testing.assert_allclose(project(fitted["H_image_to_floor"],[300,300]),project(H,[300,300]),atol=1e-5)


class TrackingAndMotionTests(unittest.TestCase):
    def test_prediction_jump_expiration(self):
        smoother = PositionSmoother()
        a = {"track_id":1, "floor_xy_m":[0,0], "status":"observed_proxy", "timestamp_s":0}
        smoother.update([a],0)
        predictions = smoother.update([], .1)
        self.assertEqual(predictions[0]["last_reliable_observation_s"],0)
        self.assertEqual(predictions[0]["status"],"predicted")
        self.assertEqual(smoother.update([], .5),[])
        b = {**a, "floor_xy_m":[100,0]}
        smoother.update([b],.6)
        self.assertEqual(b["reason"],"implausible_metric_jump")
        smoother.update([],2)
        self.assertEqual(smoother.states,{})

    def test_smoothing_preserves_raw_and_failure(self):
        smoother = PositionSmoother()
        a = {"track_id":1,"floor_xy_m":[0,0],"status":"observed_proxy"}
        smoother.update([a],0)
        b = {**a,"floor_xy_m":[.1,0]}
        smoother.update([b],.1)
        self.assertLess(b["smoothed_xy_m"][0],.1)
        self.assertEqual(b["floor_xy_m"],[.1,0])
        b.update(status="motion_invalid",floor_xy_m=None)
        smoother.update([b],.2)
        self.assertEqual(smoother.states,{})

    def test_no_features_unverified(self):
        cfg = config()
        frame = np.zeros((480,640,3),np.uint8)
        self.assertEqual(MotionMonitor(frame,cfg).check(frame,[])["status"],"motion_unverified")

    def test_known_camera_shift_rejected(self):
        cfg = config()
        cfg["operational_region_px"] = [[20,20],[620,20],[620,460],[20,460]]
        rng = np.random.default_rng(12)
        frame = rng.integers(0,256,(480,640,3),dtype=np.uint8)
        monitor = MotionMonitor(frame,cfg)
        self.assertEqual(monitor.check(frame,[])["status"],"aligned_provisional")
        shifted = cv2.warpAffine(frame,np.float32([[1,0,0],[0,1,12]]),(640,480))
        result = monitor.check(shifted,[])
        self.assertEqual(result["status"],"motion_invalid")
        self.assertGreater(result["displacement_px"],10)


class EvaluationTests(unittest.TestCase):
    def test_error_statistics(self):
        result = statistics([-1,0,2])
        self.assertEqual(result["sample_count"],3)
        self.assertEqual(result["mae_m"],1)
        self.assertAlmostEqual(result["signed_bias_m"],1/3)
        self.assertIsNone(statistics([])["mae_m"])

    def test_synthetic_evaluation_and_withheld_guard(self):
        cfg = config()
        a,b = [250,300],[350,300]
        floor = project(cfg["H_image_to_floor"],a)
        distance = np.linalg.norm(np.asarray(floor)-project(cfg["H_image_to_floor"],b))
        annotations = {"reference_kind":"synthetic", "points":[{"image_xy_px":a,"floor_xy_m":floor}],
                       "pairs":[{"image_a_px":a,"image_b_px":b,"known_distance_m":float(distance)}]}
        result = evaluate(cfg,annotations)
        self.assertEqual(result["accepted_samples"],2)
        self.assertEqual(result["physical_validation"],"pending")
        self.assertEqual(result["groups"]["all"]["pair_distance_error_m"]["mae_m"],0)
        annotations["points"][0]["image_xy_px"] = cfg["landmarks"][0]["image_xy_px"]
        with self.assertRaises(ValueError):
            evaluate(cfg,annotations)


if __name__ == "__main__":
    unittest.main()
