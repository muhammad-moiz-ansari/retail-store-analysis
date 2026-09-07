#!/usr/bin/env python3
"""Compare people count between two videos at the same timestamps.

For each sampled frame, counts people in both videos, splits them into
employees and customers per aisle, calculates customer/employee ratios,
and generates redistribution verdicts.

Usage:
    python compare_people.py video1.mp4 video2.mp4 [frame_interval]
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
NUM_AISLES = 4
EMPLOYEE_RATIO = 0.35  # ~35% of detected people are employees


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


def detect_people(model, frame) -> list[dict]:
    """Return person centers and boxes for one sampled frame."""
    results = model(frame, verbose=False, classes=[0], device="cpu")
    people = []
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            people.append({
                "center": (round((x1 + x2) / 2), round((y1 + y2) / 2)),
                "bbox": [round(x1), round(y1), round(x2), round(y2)],
            })
    return people


def calc_ratio(employees: int, customers: int) -> float:
    if employees == 0:
        return float(customers) if customers else 0.0
    return round(customers / employees, 2)


def classify_aisles(people: list[dict], frame_width: int, frame_height: int) -> list[dict]:
    """Assign detections to four spatial aisles and classify by image position."""
    aisles = [{"aisle": index + 1, "employees": 0, "customers": 0} for index in range(NUM_AISLES)]
    for person in people:
        center_x, center_y = person["center"]
        aisle_index = min(NUM_AISLES - 1, int((center_x / max(1, frame_width)) * NUM_AISLES))
        if center_y / max(1, frame_height) > 0.6:
            aisles[aisle_index]["customers"] += 1
        else:
            aisles[aisle_index]["employees"] += 1
    for aisle in aisles:
        aisle["ratio"] = calc_ratio(aisle["employees"], aisle["customers"])
    return aisles


def generate_redistribution(aisles: list[dict]) -> dict:
    """Suggest one-person moves from lower to higher customer/employee ratios."""
    updated = [dict(aisle) for aisle in aisles]
    moves = []
    while True:
        source = min(updated, key=lambda aisle: aisle["ratio"])
        target = max(updated, key=lambda aisle: aisle["ratio"])
        if source["aisle"] == target["aisle"] or source["employees"] <= 1 or target["ratio"] <= source["ratio"]:
            break
        old_source_ratio = source["ratio"]
        old_target_ratio = target["ratio"]
        source["employees"] -= 1
        target["employees"] += 1
        source["ratio"] = calc_ratio(source["employees"], source["customers"])
        target["ratio"] = calc_ratio(target["employees"], target["customers"])
        moves.append({
            "from_aisle": source["aisle"],
            "to_aisle": target["aisle"],
            "count": 1,
            "reason": f"Aisle {target['aisle']} ratio ({old_target_ratio}) > Aisle {source['aisle']} ratio ({old_source_ratio})",
        })
        if len(moves) >= NUM_AISLES:
            break
    return {
        "aisles": updated,
        "moves": moves,
        "summary": f"Move {sum(move['count'] for move in moves)} employee(s) across {len(moves)} aisle(s)" if moves else "No redistribution needed",
    }


def process_video_samples(video_path: str, frame_indices: set[int], model, label: str):
    """Sample a video and link nearby detections into local tracks."""
    cap = cv2.VideoCapture(video_path)
    counts = {}
    unique_track_ids = set()
    active_tracks = {}
    aisle_results = {}
    next_track_id = 1
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx in frame_indices:
            people = detect_people(model, frame)
            assigned = set()
            current_track_ids = []
            for person in people:
                center = person["center"]
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
            counts[frame_idx] = len(people)
            aisle_data = classify_aisles(people, int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            unique_track_ids.update(current_track_ids)
            print(f"  {label} frame {frame_idx:4d}: {len(people)} people")
            aisle_results[frame_idx] = aisle_data
        frame_idx += 1

    cap.release()
    return counts, unique_track_ids, aisle_results


def split_into_aisles(total_people: int, num_aisles: int = NUM_AISLES) -> list[dict]:
    """Distribute detected people across aisles as employees and customers."""
    if total_people == 0:
        return [{"aisle": i + 1, "employees": 0, "customers": 0} for i in range(num_aisles)]

    remaining = total_people
    aisles = []
    for i in range(num_aisles):
        if i == num_aisles - 1:
            count = remaining
        else:
            count = max(0, round(remaining * random.uniform(0.15, 0.40)))
            count = min(count, remaining)
        remaining -= count

        emp = max(0, round(count * EMPLOYEE_RATIO))
        cust = count - emp
        aisles.append({"aisle": i + 1, "employees": emp, "customers": cust})

    return aisles


def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_people.py video1.mp4 video2.mp4 [frame_interval]", file=sys.stderr)
        sys.exit(1)

    video1_path = sys.argv[1]
    video2_path = sys.argv[2]
    frame_interval = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    fps1, total1, dur1 = get_video_info(video1_path)
    fps2, total2, dur2 = get_video_info(video2_path)
    common_frames = min(total1, total2)

    print(f"Video 1: {video1_path} ({dur1/1000:.1f}s, {total1} frames, {fps1:.1f} fps)")
    print(f"Video 2: {video2_path} ({dur2/1000:.1f}s, {total2} frames, {fps2:.1f} fps)")
    print(f"Common frames: {common_frames}")
    print(f"Sampling every {frame_interval}th frame...\n")

    print("Loading YOLOv8n...")
    model = YOLO(str(MODEL_PATH))

    frame_indices = list(range(0, common_frames, frame_interval))
    num_samples = len(frame_indices)

    # Process each video independently so local track IDs cannot overlap.
    results = []
    start = time.time()

    frame_index_set = set(frame_indices)
    counts1, tracks1, aisles1 = process_video_samples(video1_path, frame_index_set, model, "V1")

    counts2, tracks2, aisles2 = process_video_samples(video2_path, frame_index_set, model, "V2")

    for i, frame_idx in enumerate(frame_indices):
        ts_ms = (frame_idx / fps1) * 1000
        ts_s = ts_ms / 1000

        if frame_idx not in counts1 or frame_idx not in counts2:
            print(f"{i+1:>7} | {frame_idx:>7} | {ts_s:>9.3f}s | {'SKIP':>9} | {'SKIP':>9} |")
            continue

        c1 = counts1[frame_idx]
        c2 = counts2[frame_idx]
        diff = c1 - c2

        aisles_v1 = aisles1[frame_idx]
        aisles_v2 = aisles2[frame_idx]

        results.append({
            "sample": i + 1,
            "frame": frame_idx,
            "timestamp_s": round(ts_s, 3),
            "v1_count": c1,
            "v2_count": c2,
            "diff": diff,
            "verdict": "V1 needs +1" if diff < 0 else "V2 needs +1" if diff > 0 else "Equal",
            "v1_aisles": aisles_v1,
            "v2_aisles": aisles_v2,
            "v1_redistribution": generate_redistribution(aisles_v1),
            "v2_redistribution": generate_redistribution(aisles_v2),
        })

        print(f"{i+1:>7} | {frame_idx:>7} | {ts_s:>9.3f}s | {c1:>3} | {c2:>3} | V1: {aisles_v1}")

    elapsed = time.time() - start
    valid = len(results)

    print("-" * 90)
    print(f"\nCompleted in {elapsed:.1f}s ({valid}/{num_samples} samples)")
    print(f"\nUnique tracked people:")
    print(f"  Video 1: {len(tracks1)}")
    print(f"  Video 2: {len(tracks2)}")
    print(f"\nAverage per frame:")
    average1 = sum(item["v1_count"] for item in results) / valid if valid else 0
    average2 = sum(item["v2_count"] for item in results) / valid if valid else 0
    print(f"  Video 1: {average1:.2f}" if valid else "  Video 1: N/A")
    print(f"  Video 2: {average2:.2f}" if valid else "  Video 2: N/A")

    # Aggregate aisle stats
    agg_v1 = [{"aisle": i + 1, "total_employees": 0, "total_customers": 0} for i in range(NUM_AISLES)]
    agg_v2 = [{"aisle": i + 1, "total_employees": 0, "total_customers": 0} for i in range(NUM_AISLES)]
    for r in results:
        for a in r["v1_aisles"]:
            agg_v1[a["aisle"] - 1]["total_employees"] += a["employees"]
            agg_v1[a["aisle"] - 1]["total_customers"] += a["customers"]
        for a in r["v2_aisles"]:
            agg_v2[a["aisle"] - 1]["total_employees"] += a["employees"]
            agg_v2[a["aisle"] - 1]["total_customers"] += a["customers"]

    final_v1_aisles = []
    for a in agg_v1:
        ratio = calc_ratio(a["total_employees"], a["total_customers"])
        final_v1_aisles.append({**a, "ratio": ratio})

    final_v2_aisles = []
    for a in agg_v2:
        ratio = calc_ratio(a["total_employees"], a["total_customers"])
        final_v2_aisles.append({**a, "ratio": ratio})

    final_redist_v1 = generate_redistribution([dict(a) for a in final_v1_aisles])
    final_redist_v2 = generate_redistribution([dict(a) for a in final_v2_aisles])

    output = {
        "count_mode": "unique_local_tracks_with_aisles",
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
        "final_aisles": {"video1": final_v1_aisles, "video2": final_v2_aisles},
        "final_redistribution": {"video1": final_redist_v1, "video2": final_redist_v2},
        "samples": results,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = OUTPUT_DIR / "people_comparison.json"
    json_path.write_text(json.dumps(output, indent=2))
    print(f"\nJSON saved to {json_path}")

    csv_path = OUTPUT_DIR / "people_comparison.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sample", "frame", "timestamp_s", "v1_count", "v2_count", "diff", "verdict",
                "v1_aisles", "v2_aisles", "v1_redistribution", "v2_redistribution",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        for result in results:
            row = dict(result)
            row["v1_aisles"] = json.dumps(row["v1_aisles"], separators=(",", ":"))
            row["v2_aisles"] = json.dumps(row["v2_aisles"], separators=(",", ":"))
            row["v1_redistribution"] = json.dumps(row["v1_redistribution"], separators=(",", ":"))
            row["v2_redistribution"] = json.dumps(row["v2_redistribution"], separators=(",", ":"))
            writer.writerow(row)
    print(f"CSV saved to {csv_path}")


if __name__ == "__main__":
    main()
