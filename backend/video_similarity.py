#!/usr/bin/env python3
"""Compare two videos frame-by-frame using SSIM and MSE.

Samples 300 random timestamps within the common duration of both videos,
seeks to each timestamp, and computes similarity metrics.

Usage:
    python video_similarity.py video1.mp4 video2.mp4
"""

import csv
import json
import random
import sys
import time
from pathlib import Path

import cv2
import numpy as np

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def compute_ssim(frame1: np.ndarray, frame2: np.ndarray) -> float:
    """Compute Structural Similarity Index (SSIM) between two frames.

    Simplified SSIM implementation without scikit-image.
    """
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    img1 = frame1.astype(np.float64)
    img2 = frame2.astype(np.float64)

    # Gaussian blur
    mu1 = cv2.GaussianBlur(img1, (11, 11), 1.5)
    mu2 = cv2.GaussianBlur(img2, (11, 11), 1.5)

    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.GaussianBlur(img1 ** 2, (11, 11), 1.5) - mu1_sq
    sigma2_sq = cv2.GaussianBlur(img2 ** 2, (11, 11), 1.5) - mu2_sq
    sigma12 = cv2.GaussianBlur(img1 * img2, (11, 11), 1.5) - mu1_mu2

    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
               ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))

    return float(ssim_map.mean())


def compute_mse(frame1: np.ndarray, frame2: np.ndarray) -> float:
    """Compute Mean Squared Error between two frames."""
    return float(np.mean((frame1.astype(np.float64) - frame2.astype(np.float64)) ** 2))


def get_video_info(video_path: str) -> dict:
    """Get video metadata."""
    cap = cv2.VideoCapture(video_path)
    info = {
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    info["duration_ms"] = (info["total_frames"] / info["fps"]) * 1000 if info["fps"] > 0 else 0
    cap.release()
    return info


def seek_and_read(video_path: str, timestamp_ms: float) -> np.ndarray | None:
    """Seek to timestamp and read a frame."""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)
    ret, frame = cap.read()
    cap.release()
    return frame if ret else None


def resize_to_match(frame1: np.ndarray, frame2: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Resize frame2 to match frame1 dimensions."""
    if frame1.shape == frame2.shape:
        return frame1, frame2
    h, w = frame1.shape[:2]
    return frame1, cv2.resize(frame2, (w, h))


def main():
    if len(sys.argv) < 3:
        print("Usage: python video_similarity.py video1.mp4 video2.mp4", file=sys.stderr)
        sys.exit(1)

    video1_path = sys.argv[1]
    video2_path = sys.argv[2]
    num_samples = 300

    # Get video info
    info1 = get_video_info(video1_path)
    info2 = get_video_info(video2_path)

    common_duration_ms = min(info1["duration_ms"], info2["duration_ms"])

    print(f"Video 1: {video1_path}")
    print(f"  Resolution: {info1['width']}x{info1['height']}, FPS: {info1['fps']:.1f}, Duration: {info1['duration_ms']/1000:.1f}s")
    print(f"Video 2: {video2_path}")
    print(f"  Resolution: {info2['width']}x{info2['height']}, FPS: {info2['fps']:.1f}, Duration: {info2['duration_ms']/1000:.1f}s")
    print(f"Common duration: {common_duration_ms/1000:.1f}s")
    print(f"Sampling {num_samples} random timestamps...\n")

    # Generate random timestamps
    random.seed(42)
    timestamps_ms = sorted(random.uniform(0, common_duration_ms) for _ in range(num_samples))

    # Process each sample
    results = []
    ssim_sum = 0.0
    mse_sum = 0.0

    print(f"{'Sample':>7} | {'Timestamp':>10} | {'MSE':>10} | {'SSIM':>8}")
    print("-" * 45)

    start_time = time.time()

    for i, ts_ms in enumerate(timestamps_ms):
        ts_s = ts_ms / 1000

        frame1 = seek_and_read(video1_path, ts_ms)
        frame2 = seek_and_read(video2_path, ts_ms)

        if frame1 is None or frame2 is None:
            print(f"{i+1:>7} | {ts_s:>9.3f}s | {'SKIP':>10} | {'SKIP':>8}")
            continue

        frame1, frame2 = resize_to_match(frame1, frame2)

        # Convert to grayscale for comparison
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        mse = compute_mse(gray1, gray2)
        ssim = compute_ssim(gray1, gray2)

        ssim_sum += ssim
        mse_sum += mse
        results.append({"sample": i + 1, "timestamp_s": round(ts_s, 3), "mse": round(mse, 2), "ssim": round(ssim, 4)})

        print(f"{i+1:>7} | {ts_s:>9.3f}s | {mse:>10.2f} | {ssim:>8.4f}")

    elapsed = time.time() - start_time
    valid_count = len(results)
    avg_ssim = ssim_sum / valid_count if valid_count > 0 else 0
    avg_mse = mse_sum / valid_count if valid_count > 0 else 0

    print("-" * 45)
    print(f"\nCompleted in {elapsed:.1f}s ({valid_count}/{num_samples} valid samples)")
    print(f"Average MSE:  {avg_mse:.2f}")
    print(f"Average SSIM: {avg_ssim:.4f}")

    # Save results
    output = {
        "video1": video1_path,
        "video2": video2_path,
        "num_samples": num_samples,
        "valid_samples": valid_count,
        "common_duration_s": round(common_duration_ms / 1000, 1),
        "avg_mse": round(avg_mse, 2),
        "avg_ssim": round(avg_ssim, 4),
        "samples": results,
    }

    out_path = OUTPUT_DIR / "video_similarity.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nJSON saved to {out_path}")

    # Save CSV
    csv_path = OUTPUT_DIR / "video_similarity.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["sample", "timestamp_s", "mse", "ssim"])
        writer.writeheader()
        writer.writerows(results)
    print(f"CSV saved to {csv_path}")


if __name__ == "__main__":
    main()
