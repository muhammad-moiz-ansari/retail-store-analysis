"""Lazy CV adapters. One loaded model bundle, independent ByteTrack state per session."""

import hashlib
from pathlib import Path
from types import SimpleNamespace

from .core import normalized
from .cv_contracts import ModelVersion


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class CVModels:
    def __init__(self, detector_path, pose_path=None, orientation_path=None, threads=2):
        import torch
        import torchvision
        import ultralytics
        from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small
        from ultralytics import YOLO

        if not Path(detector_path).is_file():
            raise FileNotFoundError("Detector checkpoint not provisioned")
        if pose_path is not None and not Path(pose_path).is_file():
            raise FileNotFoundError("Pose checkpoint not provisioned")
        torch.set_num_threads(threads)
        self.detector = YOLO(str(detector_path))
        self.pose = YOLO(str(pose_path)) if pose_path else None
        weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1
        self.embedder = mobilenet_v3_small(weights=weights).eval().cpu()
        self.embedder.classifier = torch.nn.Identity()
        self.transform = weights.transforms()
        self.orientation_head = None
        if orientation_path:
            checkpoint = torch.load(orientation_path, map_location="cpu", weights_only=True)
            if checkpoint.get("schema_version") != 1 or checkpoint.get("classes") != list(range(9)):
                raise ValueError("Incompatible orientation checkpoint")
            self.orientation_head = mobilenet_v3_small(weights=None, num_classes=9).eval().cpu()
            self.orientation_head.load_state_dict(checkpoint["state_dict"])
        method = "eight-direction:" + fingerprint(orientation_path) if orientation_path else (
            "nose-ear-proxy:" + fingerprint(pose_path) if pose_path else "unavailable")
        self.metadata = ModelVersion(detector="yolov8n:" + fingerprint(detector_path),
            embedding=f"mobilenet_v3_small:IMAGENET1K_V1:torchvision-{torchvision.__version__}",
            preprocessing="IMAGENET1K_V1:RGB:resize256:centercrop224:normalize-v1",
            embedding_dimensions=576, orientation=method,
            tracker=f"ByteTrack:ultralytics-{ultralytics.__version__}:buffer5")

    def create_tracker(self):
        from ultralytics.trackers.byte_tracker import BYTETracker
        return BYTETracker(SimpleNamespace(track_high_thresh=0.25, track_low_thresh=0.1,
            new_track_thresh=0.25, track_buffer=5, match_thresh=0.8, fuse_score=True))

    def track(self, frame, tracker):
        # Ultralytics maps letterboxed predictions back to the original source image.
        result = self.detector.predict(frame, imgsz=960, rect=False, classes=[0], conf=0.1,
                                       device="cpu", verbose=False)[0]
        self.last_detections = [{"bbox": box, "confidence": score} for box, score in
                                zip(result.boxes.xyxy.cpu().tolist(), result.boxes.conf.cpu().tolist())]
        tracks = tracker.update(result.boxes.cpu().numpy(), img=frame)
        return [{"local_id": str(int(row[4])), "bbox": [float(v) for v in row[:4]],
                 "confidence": float(row[5])} for row in tracks]

    def poses(self, frame):
        if self.pose is None or self.orientation_head is not None:
            return []
        result = self.pose.predict(frame, imgsz=960, rect=False, device="cpu", verbose=False)[0]
        if result.keypoints is None:
            return []
        return [{"bbox": box, "keypoints": points} for box, points in
                zip(result.boxes.xyxy.cpu().tolist(), result.keypoints.data.cpu().tolist())]

    def embed(self, crop):
        import torch
        from PIL import Image
        image = Image.fromarray(crop[:, :, ::-1].copy())
        with torch.inference_mode():
            vector = self.embedder(self.transform(image).unsqueeze(0))[0].tolist()
        return normalized(vector)

    def crop_orientation(self, crop, threshold=0.5):
        import math
        import torch
        from PIL import Image
        from .cv_contracts import Orientation
        if self.orientation_head is None:
            return None
        with torch.inference_mode():
            scores = self.orientation_head(self.transform(Image.fromarray(crop[:, :, ::-1].copy())).unsqueeze(0)).softmax(-1)[0]
        label, score = int(scores.argmax()), float(scores.max())
        if label == 8 or score < threshold:
            return Orientation(reason="unobservable_or_low_confidence", method="eight-direction")
        angle = label * math.pi / 4
        return Orientation(state="known", vector=(math.cos(angle), math.sin(angle)), confidence=score,
                           reason=None, method="eight-direction")
