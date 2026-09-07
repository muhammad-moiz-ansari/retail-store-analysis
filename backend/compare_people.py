#!/usr/bin/env python3
"""Compare people count between two videos at the same timestamps.

For each sampled frame, counts people in both videos and determines
which video needs more people to equalize the count.

Usage:
    python compare_people.py video1.mp4 video2.mp4 [num_samples]
"""

import csv
import json
import math
import random
import sys
import time
from pathlib import Path

import cv2
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "backend" / "yolov8n.pt"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "output"


def get_video_info(video_path: str) -> tuple:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    duration_ms = (total / fps) * 1000 if fps > 0 else 0
    return fps, total, duration_ms


def seek_and_read(video_path: str, timestamp_ms: float):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)
    ret, frame = cap.read()
    cap.release()
    return frame if ret else None


def detect_people(model, frame) -> list[tuple[int, int]]:
    """Return person centers for one sampled frame."""
    results = model(frame, verbose=False, classes=[0], device="cpu")
    centers = []
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            centers.append((round((x1 + x2) / 2), round((y1 + y2) / 2)))
    return centers


def process_video_samples(video_path: str, frame_indices: set[int], model, label: str):
    """Sample a video and link nearby detections into local tracks."""
    cap = cv2.VideoCapture(video_path)
    counts = {}
    unique_track_ids = set()
    active_tracks = {}
    next_track_id = 1
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx in frame_indices:
            centers = detect_people(model, frame)
            assigned = set()
            current_track_ids = []
            for center in centers:
                nearest_id = None
                nearest_distance = float("inf")
                for track_id, previous in active_tracks.items():
                    if track_id in assigned:
                        continue
                    distance = math.dist(center, previous)
                    if distance < nearest_distance:
                        nearest_id = track_id
                        nearest_distance = distance
                if nearest_id is None or nearest_distance > 280:
                    nearest_id = next_track_id
                    next_track_id += 1
                active_tracks[nearest_id] = center
                assigned.add(nearest_id)
                current_track_ids.append(nearest_id)
            counts[frame_idx] = len(centers)
            unique_track_ids.update(current_track_ids)
            print(f"  {label} frame {frame_idx:4d}: {len(centers)} people")
        frame_idx += 1

    cap.release()
    return counts, unique_track_ids


def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_people.py video1.mp4 video2.mp4 [frame_interval]", file=sys.stderr)
        sys.exit(1)

    video1_path = sys.argv[1]
    video2_path = sys.argv[2]
    frame_interval = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    # Get video info
    fps1, total1, dur1 = get_video_info(video1_path)
    fps2, total2, dur2 = get_video_info(video2_path)
    common_frames = min(total1, total2)

    print(f"Video 1: {video1_path} ({dur1/1000:.1f}s, {total1} frames, {fps1:.1f} fps)")
    print(f"Video 2: {video2_path} ({dur2/1000:.1f}s, {total2} frames, {fps2:.1f} fps)")
    print(f"Common frames: {common_frames}")
    print(f"Sampling every {frame_interval}th frame...\n")

    # Load YOLO
    print("Loading YOLOv8n...")
    model = YOLO(str(MODEL_PATH))

    # Generate frame indices (every Nth frame)
    frame_indices = list(range(0, common_frames, frame_interval))
    num_samples = len(frame_indices)

    # Process each video independently so local track IDs cannot overlap.
    results = []
    start = time.time()

    frame_index_set = set(frame_indices)
    counts1, tracks1 = process_video_samples(video1_path, frame_index_set, model, "V1")

    counts2, tracks2 = process_video_samples(video2_path, frame_index_set, model, "V2")

    for i, frame_idx in enumerate(frame_indices):
        ts_ms = (frame_idx / fps1) * 1000
        ts_s = ts_ms / 1000

        if frame_idx not in counts1 or frame_idx not in counts2:
            print(f"{i+1:>7} | {frame_idx:>7} | {ts_s:>9.3f}s | {'SKIP':>9} | {'SKIP':>9} |")
            continue

        c1 = counts1[frame_idx]
        c2 = counts2[frame_idx]
        diff = c1 - c2

        if diff > 0:
            verdict = f"V2 needs +{diff}"
        elif diff < 0:
            verdict = f"V1 needs +{abs(diff)}"
        else:
            verdict = "Equal"

        results.append({
            "sample": i + 1,
            "frame": frame_idx,
            "timestamp_s": round(ts_s, 3),
            "v1_count": c1,
            "v2_count": c2,
            "diff": diff,
            "verdict": verdict,
        })

        print(f"{i+1:>7} | {frame_idx:>7} | {ts_s:>9.3f}s | {c1:>9} | {c2:>9} | {verdict}")

    elapsed = time.time() - start
    valid = len(results)

    print("-" * 70)
    print(f"\nCompleted in {elapsed:.1f}s ({valid}/{num_samples} samples)")
    print(f"\nUnique tracked people:")
    print(f"  Video 1: {len(tracks1)}")
    print(f"  Video 2: {len(tracks2)}")
    print(f"\nAverage per frame:")
    average1 = sum(item["v1_count"] for item in results) / valid if valid else 0
    average2 = sum(item["v2_count"] for item in results) / valid if valid else 0
    print(f"  Video 1: {average1:.2f}" if valid else "  Video 1: N/A")
    print(f"  Video 2: {average2:.2f}" if valid else "  Video 2: N/A")

    # Save JSON
    output = {
        "count_mode": "unique_local_tracks",
        "video1": video1_path,
        "video2": video2_path,
        "frame_interval": frame_interval,
        "num_samples": num_samples,
        "valid_samples": valid,
        "common_frames": common_frames,
        "fps1": round(fps1, 2),
        "fps2": round(fps2, 2),
        "totals": {"video1": len(tracks1), "video2": len(tracks2)},
        "averages": {
            "video1": round(average1, 2),
            "video2": round(average2, 2),
        },
        "occupancy": {
            "video1_peak": max(counts1.values(), default=0),
            "video2_peak": max(counts2.values(), default=0),
        },
        "samples": results,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = OUTPUT_DIR / "people_comparison.json"
    json_path.write_text(json.dumps(output, indent=2))
    print(f"\nJSON saved to {json_path}")

    # Save CSV
    csv_path = OUTPUT_DIR / "people_comparison.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["sample", "frame", "timestamp_s", "v1_count", "v2_count", "diff", "verdict"])
        writer.writeheader()
        writer.writerows(results)
    print(f"CSV saved to {csv_path}")


if __name__ == "__main__":
    main()
