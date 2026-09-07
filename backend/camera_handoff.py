"""Offline two-camera directional handoff processing.

The model and video dependencies are loaded only when video processing is
requested. Matching decisions live in ``handoff_core`` and remain testable
without a local CV installation.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from handoff_core import HandoffConfig, crossing_direction, match_handoff_events, normalized_x


def appearance_descriptor(frame: Any, bbox: list[int]) -> list[float]:
    """Create a compact crop descriptor using resized RGB statistics."""
    import cv2

    x1, y1, x2, y2 = bbox
    height, width = frame.shape[:2]
    x1, x2 = max(0, x1), min(width, x2)
    y1, y2 = max(0, y1), min(height, y2)
    if x2 <= x1 or y2 <= y1:
        return []
    crop = frame[y1:y2, x1:x2]
    crop = cv2.resize(crop, (16, 32))
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    features: list[float] = []
    for channel, bins in ((0, 8), (1, 4), (2, 4)):
        histogram = cv2.calcHist([hsv], [channel], None, [bins], [0, 256])
        total = float(histogram.sum()) or 1.0
        features.extend(float(value / total) for value in histogram.flatten())
    features.extend([float((x2 - x1) / max(1, y2 - y1)), float((y2 - y1) / max(1, height))])
    return features


def process_camera(
    camera_id: str,
    video_path: Path,
    boundary: float,
    expected_direction: str,
    model_path: Path,
    sample_every: int,
    cooldown_seconds: float,
    log,
) -> dict[str, Any]:
    """Process one camera independently and emit eligible boundary events."""
    import cv2
    from ultralytics import YOLO

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    model = YOLO(str(model_path))
    track_states: dict[str, dict[str, Any]] = {}
    track_summaries: dict[str, dict[str, Any]] = {}
    events: list[dict[str, Any]] = []
    frame_index = 0
    event_number = 1

    log(f"[{camera_id}] processing {video_path.name} ({width}px, {fps:.2f} FPS, {total_frames} frames)\n")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % max(1, sample_every) != 0:
            frame_index += 1
            continue

        timestamp = frame_index / fps
        results = model.track(frame, persist=True, classes=[0], device="cpu", verbose=False, tracker="bytetrack.yaml")
        boxes = results[0].boxes if results else []
        for box in boxes:
            if box.id is None:
                continue
            local_id = str(int(box.id[0]))
            x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
            center_x = (x1 + x2) / 2
            x_normalized = normalized_x(center_x, width)
            state = track_states.setdefault(local_id, {"first_seen": timestamp, "last_seen": timestamp, "previous_x": x_normalized, "last_event": None})
            direction = crossing_direction(float(state["previous_x"]), x_normalized, boundary)
            is_initial_target_entry = (
                expected_direction == "left"
                and state["first_seen"] == timestamp
                and x_normalized <= boundary + 0.08
            )
            eligible = direction == expected_direction or is_initial_target_entry
            if eligible and (state["last_event"] is None or timestamp - state["last_event"] >= cooldown_seconds):
                events.append({
                    "event_id": f"{camera_id}-event-{event_number:04d}",
                    "camera_id": camera_id,
                    "local_track_id": local_id,
                    "direction": expected_direction,
                    "boundary": "right" if expected_direction == "right" else "left",
                    "timestamp_seconds": round(timestamp, 3),
                    "frame": frame_index,
                    "x_normalized": round(x_normalized, 4),
                    "appearance": appearance_descriptor(frame, [x1, y1, x2, y2]),
                    "confidence": round(float(box.conf[0]), 4),
                })
                event_number += 1
                state["last_event"] = timestamp
            state["previous_x"] = x_normalized
            state["last_seen"] = timestamp
            summary = track_summaries.setdefault(local_id, {"local_track_id": local_id, "first_seen": timestamp, "last_seen": timestamp, "frames": 0})
            summary["last_seen"] = timestamp
            summary["frames"] += 1
        frame_index += 1

    cap.release()
    log(f"[{camera_id}] found {len(track_summaries)} local tracks and {len(events)} eligible events\n")
    return {"camera_id": camera_id, "video": str(video_path), "fps": fps, "total_frames": total_frames, "tracks": list(track_summaries.values()), "events": events}


def run_pipeline(
    cam1_path: Path,
    cam2_path: Path,
    model_path: Path,
    sample_every: int = 5,
    min_gap: float = 1.0,
    max_gap: float = 45.0,
    cam1_boundary: float = 0.85,
    cam2_boundary: float = 0.15,
    log=print,
) -> dict[str, Any]:
    config = HandoffConfig(source_boundary=cam1_boundary, target_boundary=cam2_boundary, min_gap_seconds=min_gap, max_gap_seconds=max_gap)
    started = time.perf_counter()
    cam1 = process_camera("cam1", cam1_path, cam1_boundary, "right", model_path, sample_every, config.cooldown_seconds, log)
    cam2 = process_camera("cam2", cam2_path, cam2_boundary, "left", model_path, sample_every, config.cooldown_seconds, log)
    matches = match_handoff_events(cam1["events"], cam2["events"], config)
    elapsed = time.perf_counter() - started
    return {
        "schema_version": 1,
        "configuration": {"source_camera": config.source_camera, "target_camera": config.target_camera, "source_boundary": config.source_boundary, "target_boundary": config.target_boundary, "min_gap_seconds": config.min_gap_seconds, "max_gap_seconds": config.max_gap_seconds, "sample_every": sample_every},
        "cameras": [cam1, cam2],
        "handoffs": matches,
        "processing": {"elapsed_seconds": round(elapsed, 3), "cpu_only": True, "appearance_method": "normalized_hsv_histogram_and_shape"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Process a directional cam1-to-cam2 handoff")
    parser.add_argument("--cam1", required=True, type=Path)
    parser.add_argument("--cam2", required=True, type=Path)
    parser.add_argument("--model", default=Path(__file__).with_name("yolov8n.pt"), type=Path)
    parser.add_argument("--output", default=Path(__file__).parent / "output" / "camera_handoff.json", type=Path)
    parser.add_argument("--sample-every", default=5, type=int)
    parser.add_argument("--min-gap", default=1.0, type=float)
    parser.add_argument("--max-gap", default=45.0, type=float)
    parser.add_argument("--cam1-boundary", default=0.85, type=float)
    parser.add_argument("--cam2-boundary", default=0.15, type=float)
    args = parser.parse_args()
    for video in (args.cam1, args.cam2):
        if not video.exists():
            parser.error(f"Video does not exist: {video}")
    result = run_pipeline(args.cam1, args.cam2, args.model, args.sample_every, args.min_gap, args.max_gap, args.cam1_boundary, args.cam2_boundary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()