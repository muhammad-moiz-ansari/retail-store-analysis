import math
import tempfile
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np

from .calibration import RoleEstimator, build_calibration
from .core import EventEngine
from .cv_contracts import ModelVersion, Orientation, ReferenceTrack, TrackObservation
from .frames import Frame, MediaError, recording_frames
from .geometry import orientation_from_pose, zone_at
from .live import LiveSource
from .pipeline import FrameProcessor, process_recording
from .schemas import CameraConfig, Zone


MODELS = ModelVersion(detector="det", embedding="emb", preprocessing="prep",
                      embedding_dimensions=3, orientation="pose", tracker="byte")


class TaskATests(unittest.TestCase):
    def test_frame_processor_emits_namespaced_reviewable_observation(self):
        class FakeModels:
            metadata = MODELS

            def create_tracker(self):
                return object()

            def track(self, image, tracker):
                self.last_detections = [{"bbox": [10, 10, 40, 80], "confidence": .9}]
                return [{"local_id": "7", "bbox": [10, 10, 40, 80], "confidence": .9}]

            def poses(self, image):
                return []

            def embed(self, crop):
                return [1, 0, 0]

        processor = FrameProcessor(FakeModels(), "store", CameraConfig(camera_id="cam"),
                                   session_id="session", utc_anchor=datetime(2026, 9, 14, tzinfo=timezone.utc))
        records = list(process_recording(processor, iter([Frame(np.zeros((100, 100, 3), dtype=np.uint8), 0)])))
        frame = records[1]
        self.assertEqual(frame.observations[0].track_id, "session:" + frame.observations[0].track_id.split(":", 1)[1])
        self.assertEqual(frame.observations[0].role, "unknown")
        self.assertEqual(len(frame.review_samples), 1)
        self.assertEqual(records[-1].reason, "eof")

    def test_vlm_role_is_used_only_when_enabled_and_confident(self):
        class FakeVLM:
            def classify_role(self, crop):
                from .vlm import VLMResult
                return VLMResult("employee", .95, {"vest": "orange"})

            def classify_interaction(self, frames):
                from .vlm import VLMResult
                return VLMResult("no_interaction", .95)

        class FakeModels:
            metadata = MODELS
            def create_tracker(self): return object()
            def track(self, image, tracker):
                self.last_detections = [{"bbox": [10, 10, 40, 80], "confidence": .9}]
                return [{"local_id": "7", "bbox": [10, 10, 40, 80], "confidence": .9}]
            def poses(self, image): return []
            def embed(self, crop): return [1, 0, 0]

        config = CameraConfig(camera_id="cam", vlm_role_enabled=True)
        processor = FrameProcessor(FakeModels(), "store", config, session_id="session", vlm=FakeVLM())
        result = processor.process(Frame(np.zeros((100, 100, 3), dtype=np.uint8), 0))
        self.assertEqual(result.observations[0].role, "employee")
        self.assertEqual(result.observations[0].role_reason, "vlm_role_classification")
        self.assertEqual(result.observations[0].vlm_role_evidence["vest"], "orange")

    def test_contract_rejects_unnamespaced_and_unknown_direction(self):
        with self.assertRaises(ValueError):
            TrackObservation(session_id="s1", track_id="track-1", global_person_id="person-1", source_seconds=0,
                             bbox=(0, 0, 10, 10), source_size=(100, 100), detection_confidence=.9)
        unknown = Orientation(reason="weak_keypoints")
        self.assertEqual(unknown.state, "unknown")
        with self.assertRaises(ValueError):
            Orientation(state="known", vector=(1, 0), confidence=.9, reason="still-present")

    def test_calibration_requires_both_roles_and_is_camera_scoped(self):
        refs = []
        for role, vector, camera in (("employee", [1, 0, 0], "cam"),
                                     ("employee", [.9, .1, 0], "cam"),
                                     ("customer", [0, 1, 0], "cam"),
                                     ("customer", [0, .9, .1], "cam")):
            refs.append(ReferenceTrack(role=role, track_id=f"cam:{role}:{len(refs)}",
                                       camera_id=camera, label_version="labels-v1", embeddings=[vector]))
        calibration = build_calibration("store", "cam", "v1", MODELS, refs)
        self.assertEqual(set(calibration.prototypes), {"employee", "customer"})
        with self.assertRaises(ValueError):
            RoleEstimator(MODELS, "store", "other", calibration)

    def test_weak_appearance_cannot_be_rescued_by_zone_prior(self):
        refs = []
        for role, vector in (("employee", [1, 0, 0]), ("employee", [.9, .1, 0]),
                             ("customer", [0, 1, 0]), ("customer", [0, .9, .1])):
            refs.append(ReferenceTrack(role=role, track_id=f"cam:{role}:{len(refs)}",
                                       camera_id="cam", label_version="labels-v1", embeddings=[vector]))
        calibration = build_calibration("store", "cam", "v1", MODELS, refs)
        estimator = RoleEstimator(MODELS, "store", "cam", calibration)
        estimator.update("cam:track", [1, 1, 0])
        role, evidence, reason = estimator.estimate("cam:track", CameraConfig(camera_id="cam"), zone_prior=1)
        self.assertEqual(role, "unknown")
        self.assertEqual(reason, "insufficient_visual_evidence")
        self.assertIn("visual_margin", evidence)

    def test_orientation_and_zone_are_explicit(self):
        points = [(0, 0, .9), (0, 0, 0), (0, 0, 0), (2, 4, .9), (8, 4, .9)]
        result = orientation_from_pose(points)
        self.assertEqual(result.state, "known")
        self.assertAlmostEqual(math.hypot(*result.vector), 1)
        config = CameraConfig(camera_id="cam", zones=[Zone(name="A", polygon=[(0, 0), (1, 0), (1, 1), (0, 1)])])
        self.assertEqual(zone_at((.5, .5), config.zones), ("A", 0))
        self.assertEqual(zone_at((1.5, .5), config.zones), ("Unassigned", 0))

    def test_event_engine_requires_three_source_seconds(self):
        config = CameraConfig(camera_id="cam", distance_threshold=.2, min_duration_seconds=3)
        engine = EventEngine("job", "store", "cam", "2026-09-14T10:00:00+00:00", "shift", "v1", config)
        emp = SimpleNamespace(track_id="s:e", role="employee", position=(.2, .2), facing=(1, 0), orientation_confidence=.9, zone="A")
        cust = SimpleNamespace(track_id="s:c", role="customer", position=(.3, .2), facing=(-1, 0), orientation_confidence=.9, zone="A")
        self.assertEqual(engine.update(0, [emp, cust]), [])
        self.assertEqual(engine.update(1, [emp, cust]), [])
        self.assertEqual(engine.update(2, [emp, cust]), [])
        self.assertEqual(engine.update(3, [emp, cust]), [])
        event = engine.flush()
        self.assertEqual(len(event), 1)
        self.assertEqual(event[0]["duration_seconds"], 3)

    def test_recording_decoder_rejects_missing_source_pts(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as file:
            file.write(b"not-video")
            file.flush()
            with self.assertRaises(MediaError):
                next(recording_frames(file.name))

    def test_live_source_only_accepts_rtsp(self):
        with self.assertRaises(ValueError):
            LiveSource("cam", "http://localhost/camera")


if __name__ == "__main__":
    unittest.main()
