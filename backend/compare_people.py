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

from device import DEVICE

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


def count_people(model, frame) -> int:
    results = model(frame, verbose=False, classes=[0], device=DEVICE)
    count = sum(len(r.boxes) for r in results)
    return count


def ratio_value(employees: int, customers: int) -> float:
    if employees < 0 or customers < 0:
        return 0.0
    if customers == 0:
        return math.inf if employees > 0 else 0.0
    return employees / customers


def build_ratio_verdict(video1_count: int, video2_count: int, tolerance: float = 0.25) -> str:
    """Return a decision that reflects the relative coverage ratio rather than the raw count delta."""
    if video1_count == video2_count:
        return "Balanced"

    v1_ratio = ratio_value(video1_count, max(video2_count, 1))
    v2_ratio = ratio_value(video2_count, max(video1_count, 1))

    if abs(v1_ratio - v2_ratio) <= tolerance:
        return "Balanced"
    if v1_ratio > v2_ratio:
        return "V1 stronger ratio"
    return "V2 stronger ratio"


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

    # Process
    results = []
    v1_total = 0
    v2_total = 0

    print(f"{'Sample':>7} | {'Frame':>7} | {'Timestamp':>10} | {'V1 Count':>9} | {'V2 Count':>9} | {'Verdict'}")
    print("-" * 75)

    start = time.time()

    for i, frame_idx in enumerate(frame_indices):
        ts_ms = (frame_idx / fps1) * 1000
        ts_s = ts_ms / 1000

        frame1 = seek_and_read(video1_path, ts_ms)
        frame2 = seek_and_read(video2_path, ts_ms)

        if frame1 is None or frame2 is None:
            print(f"{i+1:>7} | {frame_idx:>7} | {ts_s:>9.3f}s | {'SKIP':>9} | {'SKIP':>9} |")
            continue

        c1 = count_people(model, frame1)
        c2 = count_people(model, frame2)
        diff = c1 - c2
        verdict = build_ratio_verdict(c1, c2)

        v1_total += c1
        v2_total += c2

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
    print(f"\nTotal people detected:")
    print(f"  Video 1: {v1_total}")
    print(f"  Video 2: {v2_total}")
    print(f"\nAverage per frame:")
    print(f"  Video 1: {v1_total/valid:.2f}" if valid else "  Video 1: N/A")
    print(f"  Video 2: {v2_total/valid:.2f}" if valid else "  Video 2: N/A")

    # Save JSON
    ratio_window = 0.25
    output = {
        "video1": video1_path,
        "video2": video2_path,
        "frame_interval": frame_interval,
        "num_samples": num_samples,
        "valid_samples": valid,
        "common_frames": common_frames,
        "fps1": round(fps1, 2),
        "fps2": round(fps2, 2),
        "count_mode": "ratio_verdict",
        "totals": {"video1": v1_total, "video2": v2_total},
        "averages": {
            "video1": round(v1_total / valid, 2) if valid else 0,
            "video2": round(v2_total / valid, 2) if valid else 0,
        },
        "comparison_threshold": ratio_window,
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
