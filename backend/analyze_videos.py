#!/usr/bin/env python3
"""Analyze two videos: detect people, measure distances, compare.

Usage:
    python analyze_videos.py video1.mp4 video2.mp4
"""

import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

BACKEND_DIR = Path(__file__).resolve().parent
MODEL_PATH = BACKEND_DIR / "yolov8n.pt"
OUTPUT_DIR = BACKEND_DIR / "output"


def extract_frames(video_path: str, every_n: int = 30):
    """Extract every Nth frame from a video."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % every_n == 0:
            timestamp = frame_idx / fps
            frames.append({
                "frame": frame_idx,
                "timestamp": f"{int(timestamp // 60)}:{timestamp % 60:05.2f}",
                "image": frame,
            })
        frame_idx += 1

    cap.release()
    return frames, fps, total_frames


def detect_people(model, frame):
    """Run YOLO detection and return people with bounding boxes."""
    results = model(frame, verbose=False, classes=[0], device="cpu")  # class 0 = person
    people = []

    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            conf = float(box.conf[0])
            people.append({
                "bbox": [x1, y1, x2, y2],
                "center": [cx, cy],
                "confidence": round(conf, 3),
            })

    return people


def calc_distances(people):
    """Calculate pixel distances between all pairs."""
    distances = []
    for i in range(len(people)):
        for j in range(i + 1, len(people)):
            c1 = people[i]["center"]
            c2 = people[j]["center"]
            dist = math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)
            distances.append({
                "from": i + 1,
                "to": j + 1,
                "pixels": round(dist, 1),
            })
    return distances


def draw_annotations(frame, people, distances):
    """Draw bounding boxes, IDs, and distance lines."""
    annotated = frame.copy()

    # Draw bounding boxes
    for i, p in enumerate(people):
        x1, y1, x2, y2 = p["bbox"]
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"P{i + 1} ({p['confidence']:.0%})"
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(annotated, (x1, y1 - h - 8), (x1 + w, y1), (0, 255, 0), -1)
        cv2.putText(annotated, label, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    # Draw distance lines
    for d in distances:
        p1 = people[d["from"] - 1]["center"]
        p2 = people[d["to"] - 1]["center"]
        cv2.line(annotated, p1, p2, (0, 0, 255), 1)
        mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
        cv2.putText(annotated, f"{d['pixels']:.0f}px", mid, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

    # Count display
    cv2.putText(annotated, f"People: {len(people)}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

    return annotated


def compile_video(frames_dir: Path, output_path: Path, fps: float, every_n: int):
    """Compile annotated frames into an MP4 video."""
    frame_files = sorted(frames_dir.glob("frame_*.jpg"))
    if not frame_files:
        return

    first = cv2.imread(str(frame_files[0]))
    h, w = first.shape[:2]

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    # Use original fps divided by every_n for playback speed
    out_fps = fps / every_n
    writer = cv2.VideoWriter(str(output_path), fourcc, out_fps, (w, h))

    for f in frame_files:
        img = cv2.imread(str(f))
        writer.write(img)

    writer.release()
    print(f"  Video saved: {output_path}")


def create_comparison_video(video1_path: str, video2_path: str, output_path: Path, every_n: int):
    """Create side-by-side comparison video."""
    cap1 = cv2.VideoCapture(video1_path)
    cap2 = cv2.VideoCapture(video2_path)

    w1 = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
    h1 = int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))
    w2 = int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
    h2 = int(cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Match heights for side-by-side
    target_h = max(h1, h2)
    scale1 = target_h / h1
    scale2 = target_h / h2
    target_w1 = int(w1 * scale1)
    target_w2 = int(w2 * scale2)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = min(cap1.get(cv2.CAP_PROP_FPS), cap2.get(cv2.CAP_PROP_FPS))
    writer = cv2.VideoWriter(str(output_path), fourcc, fps / every_n, (target_w1 + target_w2, target_h))

    frame_idx = 0
    while True:
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()
        if not ret1 or not ret2:
            break

        if frame_idx % every_n == 0:
            # Resize to match heights
            f1 = cv2.resize(frame1, (target_w1, target_h))
            f2 = cv2.resize(frame2, (target_w2, target_h))

            # Add labels
            cv2.putText(f1, "Video 1", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            cv2.putText(f2, "Video 2", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            # Concatenate side by side
            combined = np.hstack((f1, f2))
            writer.write(combined)

        frame_idx += 1

    cap1.release()
    cap2.release()
    writer.release()
    print(f"  Comparison video saved: {output_path}")


def analyze_video(video_path: str, output_dir: Path, model, every_n: int = 30):
    """Analyze a single video."""
    video_name = Path(video_path).stem
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    print(f"Extracting frames from {video_name}...")
    frames, fps, total_frames = extract_frames(video_path, every_n)
    print(f"  {len(frames)} frames extracted (every {every_n} frames, {fps} fps, {total_frames} total)")

    frame_results = []
    annotated_frames = []
    for i, f in enumerate(frames):
        people = detect_people(model, f["image"])
        distances = calc_distances(people)
        annotated = draw_annotations(f["image"], people, distances)

        # Save annotated frame
        frame_path = frames_dir / f"frame_{f['frame']:04d}.jpg"
        cv2.imwrite(str(frame_path), annotated)
        annotated_frames.append(annotated)

        frame_result = {
            "frame": f["frame"],
            "timestamp": f["timestamp"],
            "people_count": len(people),
            "people": people,
            "distances": distances,
        }
        frame_results.append(frame_result)

        print(f"  Frame {f['frame']:4d} ({f['timestamp']}): {len(people)} people")

    # Compile video from annotated frames
    video_output = output_dir / f"{video_name}_annotated.mp4"
    compile_video(frames_dir, video_output, fps, every_n)

    # Save per-video results
    results_path = output_dir / "results.json"
    counts = [r["people_count"] for r in frame_results]
    video_results = {
        "video": video_name,
        "fps": fps,
        "total_frames": total_frames,
        "sampled_frames": len(frame_results),
        "every_n_frames": every_n,
        "stats": {
            "min_people": min(counts) if counts else 0,
            "max_people": max(counts) if counts else 0,
            "avg_people": round(sum(counts) / len(counts), 2) if counts else 0,
        },
        "frames": frame_results,
    }
    results_path.write_text(json.dumps(video_results, indent=2))
    print(f"  Results saved to {results_path}")

    return video_results


def main():
    if len(sys.argv) < 3:
        print("Usage: python analyze_videos.py video1.mp4 video2.mp4", file=sys.stderr)
        sys.exit(1)

    video1_path = sys.argv[1]
    video2_path = sys.argv[2]

    # Create output dirs
    base_dir = OUTPUT_DIR
    (base_dir / Path(video1_path).stem).mkdir(parents=True, exist_ok=True)
    (base_dir / Path(video2_path).stem).mkdir(parents=True, exist_ok=True)

    # Load YOLO model
    print("Loading YOLOv8n...")
    model = YOLO(str(MODEL_PATH))

    # Analyze both videos
    results1 = analyze_video(video1_path, base_dir / Path(video1_path).stem, model)
    results2 = analyze_video(video2_path, base_dir / Path(video2_path).stem, model)

    # Comparison
    comparison = {
        "video1": {
            "name": results1["video"],
            "sampled_frames": results1["sampled_frames"],
            "stats": results1["stats"],
        },
        "video2": {
            "name": results2["video"],
            "sampled_frames": results2["sampled_frames"],
            "stats": results2["stats"],
        },
    }

    comparison_path = base_dir / "comparison.json"
    comparison_path.write_text(json.dumps(comparison, indent=2))

    # Create side-by-side comparison video
    print("\nCreating comparison video...")
    comparison_video_path = base_dir / "comparison_side_by_side.mp4"
    create_comparison_video(video1_path, video2_path, comparison_video_path, 30)

    print(f"\nComparison saved to {comparison_path}")
    print(f"\n{'='*50}")
    print(f"Video 1: {results1['video']}")
    print(f"  Avg people: {results1['stats']['avg_people']}")
    print(f"  Min/Max: {results1['stats']['min_people']}/{results1['stats']['max_people']}")
    v1_output = base_dir / results1["video"] / f"{results1['video']}_annotated.mp4"
    print(f"  Output: {v1_output}")
    print(f"Video 2: {results2['video']}")
    print(f"  Avg people: {results2['stats']['avg_people']}")
    print(f"  Min/Max: {results2['stats']['min_people']}/{results2['stats']['max_people']}")
    v2_output = base_dir / results2["video"] / f"{results2['video']}_annotated.mp4"
    print(f"  Output: {v2_output}")
    print(f"Comparison: {comparison_video_path}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
