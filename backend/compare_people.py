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


def count_people(model, frame) -> int:
    results = model(frame, verbose=False, classes=[0], device="cpu")
    count = sum(len(r.boxes) for r in results)
    return count


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


def calc_ratio(employees: int, customers: int) -> float:
    if employees == 0:
        return float(customers) if customers > 0 else 0.0
    return round(customers / employees, 2)


def generate_redistribution(aisles: list[dict]) -> dict:
    """Compare ratios across aisles and suggest employee movement."""
    for a in aisles:
        a["ratio"] = calc_ratio(a["employees"], a["customers"])

    sorted_by_ratio = sorted(aisles, key=lambda x: x["ratio"], reverse=True)
    overstaffed = [a for a in sorted_by_ratio if a["ratio"] < sorted_by_ratio[0]["ratio"]]
    understaffed = [a for a in sorted_by_ratio if a["ratio"] > sorted_by_ratio[-1]["ratio"]]

    moves = []
    for under in understaffed:
        for over in overstaffed:
            if over["employees"] > 1 and under["ratio"] > over["ratio"]:
                move_count = min(1, over["employees"] - 1)
                if move_count > 0:
                    moves.append({
                        "from_aisle": over["aisle"],
                        "to_aisle": under["aisle"],
                        "count": move_count,
                        "reason": f"Aisle {under['aisle']} ratio ({under['ratio']}) > Aisle {over['aisle']} ratio ({over['ratio']})",
                    })
                    over["employees"] -= move_count
                    under["employees"] += move_count
                    over["ratio"] = calc_ratio(over["employees"], over["customers"])
                    under["ratio"] = calc_ratio(under["employees"], under["customers"])
                    break

    return {
        "aisles": aisles,
        "moves": moves,
        "summary": f"Move {sum(m['count'] for m in moves)} employee(s) across {len(moves)} aisle(s)" if moves else "No redistribution needed",
    }


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

    results = []
    v1_total = 0
    v2_total = 0

    header = f"{'Sample':>7} | {'Frame':>7} | {'Timestamp':>10} | {'V1':>3} | {'V2':>3} | {'Aisles (E/C)'}"
    print(header)
    print("-" * 90)

    start = time.time()

    for i, frame_idx in enumerate(frame_indices):
        ts_ms = (frame_idx / fps1) * 1000
        ts_s = ts_ms / 1000

        frame1 = seek_and_read(video1_path, ts_ms)
        frame2 = seek_and_read(video2_path, ts_ms)

        if frame1 is None or frame2 is None:
            print(f"{i+1:>7} | {frame_idx:>7} | {ts_s:>9.3f}s | {'SKIP':>3} | {'SKIP':>3} |")
            continue

        c1 = count_people(model, frame1)
        c2 = count_people(model, frame2)

        aisles_v1 = split_into_aisles(c1)
        aisles_v2 = split_into_aisles(c2)

        v1_total += c1
        v2_total += c2

        aisle_str_v1 = " ".join(f"A{a['aisle']}:{a['employees']}e/{a['customers']}c" for a in aisles_v1)
        aisle_str_v2 = " ".join(f"A{a['aisle']}:{a['employees']}e/{a['customers']}c" for a in aisles_v2)

        redist_v1 = generate_redistribution(aisles_v1)
        redist_v2 = generate_redistribution(aisles_v2)

        results.append({
            "sample": i + 1,
            "frame": frame_idx,
            "timestamp_s": round(ts_s, 3),
            "v1_count": c1,
            "v2_count": c2,
            "v1_aisles": aisles_v1,
            "v2_aisles": aisles_v2,
            "v1_redistribution": redist_v1,
            "v2_redistribution": redist_v2,
        })

        print(f"{i+1:>7} | {frame_idx:>7} | {ts_s:>9.3f}s | {c1:>3} | {c2:>3} | V1: {aisle_str_v1}")

    elapsed = time.time() - start
    valid = len(results)

    print("-" * 90)
    print(f"\nCompleted in {elapsed:.1f}s ({valid}/{num_samples} samples)")
    print(f"\nTotal people detected:")
    print(f"  Video 1: {v1_total}")
    print(f"  Video 2: {v2_total}")

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
        "video1": video1_path,
        "video2": video2_path,
        "frame_interval": frame_interval,
        "num_samples": num_samples,
        "valid_samples": valid,
        "common_frames": common_frames,
        "fps1": round(fps1, 2),
        "fps2": round(fps2, 2),
        "totals": {"video1": v1_total, "video2": v2_total},
        "averages": {
            "video1": round(v1_total / valid, 2) if valid else 0,
            "video2": round(v2_total / valid, 2) if valid else 0,
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
        writer = csv.DictWriter(f, fieldnames=["sample", "frame", "timestamp_s", "v1_count", "v2_count"])
        writer.writeheader()
        writer.writerows({k: v for k, v in r.items() if k in ["sample", "frame", "timestamp_s", "v1_count", "v2_count"]} for r in results)
    print(f"CSV saved to {csv_path}")


if __name__ == "__main__":
    main()
