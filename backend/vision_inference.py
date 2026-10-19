"""Shared local YOLO/ByteTrack inference; results are original-frame pixels."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_model(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Model not found: {path}. Supply --model with existing local weights.")
    # Keep local CLI runs usable in restricted environments; never download weights.
    os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / "data/outputs/ultralytics"))
    os.environ.setdefault("YOLO_AUTOINSTALL", "false")
    from ultralytics import YOLO
    import torch
    # Avoid CPU thread oversubscription on desktop machines (also configurable).
    torch.set_num_threads(int(os.getenv("FLOOR_INFERENCE_THREADS", "2")))
    model = YOLO(str(path))
    if model.task != "detect":
        raise ValueError("Floor points require a bounding-box detection model.")
    return model


def track_frame(model, frame, classes=None, confidence=None):
    options = {"persist": True, "classes": classes, "device": "cpu",
               "verbose": False, "tracker": "bytetrack.yaml"}
    # Existing callers retain Ultralytics' tracking threshold; the floor CLI
    # explicitly supplies its accepted-detection threshold.
    if confidence is not None:
        options["conf"] = confidence
    return model.track(frame, **options)


class PersonDetector:
    def __init__(self, model_path, confidence=0.25):
        self.model = load_model(model_path)
        self.confidence = confidence
        self.classes = [i for i, name in self.model.names.items()
                        if name.lower() in {"person", "employee", "customer"}]
        if not self.classes:
            raise ValueError(f"No person/employee/customer classes in {self.model.names}")

    def __call__(self, frame):
        records = []
        for result in track_frame(self.model, frame, self.classes, self.confidence):
            if tuple(result.orig_shape) != frame.shape[:2]:
                raise ValueError("Detector returned incompatible original-frame geometry")
            for box in result.boxes:
                bbox = [float(v) for v in box.xyxy[0].tolist()]
                role = self.model.names[int(box.cls[0])].lower()
                score = float(box.conf[0])
                records.append({"bbox_xyxy_px": bbox,
                                "foot_px": [(bbox[0] + bbox[2]) / 2, bbox[3]],
                                "track_id": int(box.id[0]) if box.id is not None else None,
                                "role": role, "detector_confidence": score,
                                "role_confidence": score if role != "person" else None,
                                "confidence_semantics": "joint detection/class score"})
        return records
