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
    torch.set_num_threads(int(os.getenv("INFERENCE_THREADS", "2")))
    model = YOLO(str(path))
    if model.task != "detect":
        raise ValueError("Tracking requires a bounding-box detection model.")
    return model


def track_frame(model, frame, classes=None):
    return model.track(frame, persist=True, classes=classes, device="cpu",
                       verbose=False, tracker="bytetrack.yaml")
