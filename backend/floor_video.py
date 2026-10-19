"""Video IO and uncalibrated preview, deliberately independent of geometry."""
import argparse
import json
import math
from pathlib import Path

import cv2

from .vision_inference import PersonDetector, ROOT


def open_video(path):
    if not Path(path).is_file():
        raise ValueError(f"Video not found: {path}")
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    size = [int(cap.get(3)), int(cap.get(4))]
    if not cap.isOpened() or not math.isfinite(fps) or fps <= 0 or min(size) <= 0:
        cap.release()
        raise ValueError(f"Unreadable video or invalid dimensions/FPS: {path}")
    return cap, fps, size


def writer(path, fps, size):
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, tuple(size))
    if not out.isOpened():
        raise ValueError(f"mp4v output unavailable: {path}. Check codec support and output permissions.")
    return out


def draw_detections(frame, detections):
    for d in detections:
        color = (60, 200, 80) if d["role"] == "employee" else (255, 180, 50)
        x1, y1, x2, y2 = [round(v) for v in d["bbox_xyxy_px"]]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.circle(frame, tuple(round(v) for v in d["foot_px"]), 6, (0, 0, 255), -1)
        label = f'{d["role"]} {d["detector_confidence"]:.2f} ID:{d["track_id"]}'
        cv2.putText(frame, label, (x1, max(60, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, .6, color, 2)
    return frame


def common_parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--model", type=Path, default=ROOT / "models/best.pt")
    p.add_argument("--output-dir", type=Path, default=ROOT / "data/outputs/distance/preview")
    p.add_argument("--max-frames", type=int, default=0, help="Maximum processed frames, 0 = whole clip")
    p.add_argument("--sample-every", type=int, default=1)
    p.add_argument("--confidence", type=float, default=.25)
    p.add_argument("--headless", action="store_true")
    return p


def video_frames(cap, fps, sample_every=1, max_frames=0):
    if sample_every < 1 or max_frames < 0:
        raise ValueError("Require sample-every >= 1 and max-frames >= 0")
    i, processed, last_ts = 0, 0, -1.0
    expected_size = (int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
    while True:
        ok, frame = cap.read()
        if not ok:
            if i < int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1:
                raise ValueError(f"Video decoding failed prematurely at frame {i}")
            break
        if i % sample_every == 0:
            if frame.shape[:2] != expected_size:
                raise ValueError(f"Video geometry changed at frame {i}; recalibration is required")
            ts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if not math.isfinite(ts) or ts < 0 or (i > 0 and ts <= last_ts):
                raise ValueError(f"Invalid/non-monotonic video timestamp at frame {i}: {ts}")
            last_ts = ts
            yield i, ts, frame
            processed += 1
            if max_frames and processed >= max_frames:
                break
        i += 1


def preview(args):
    if args.sample_every < 1 or args.max_frames < 0 or not 0 < args.confidence <= 1:
        raise ValueError("Invalid sample-every, max-frames or confidence")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cap, fps, size = open_video(args.video)
    out = None
    count, detections_count = 0, 0
    try:
        detector = PersonDetector(args.model, args.confidence)
        out = writer(args.output_dir / "foot_points.mp4", fps / args.sample_every, size)
        with (args.output_dir / "detections.jsonl").open("w", encoding="utf-8") as stream:
            for index, ts, frame in video_frames(cap, fps, args.sample_every, args.max_frames):
                detections = detector(frame)
                record = {"frame_index": index, "timestamp_s": ts, "frame_size": size,
                          "status": "uncalibrated", "detections": detections}
                stream.write(json.dumps(record, allow_nan=False) + "\n")
                draw_detections(frame, detections)
                cv2.putText(frame, "Uncalibrated: foot-point preview", (15, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 220, 255), 2)
                out.write(frame)
                if count == 0:
                    cv2.imwrite(str(args.output_dir / "foot_points.jpg"), frame)
                count += 1
                detections_count += len(detections)
                if count % 100 == 0:
                    stream.flush()
                    print(f"Preview: {count} frames processed; video time {ts:.2f}s", flush=True)
                if not args.headless:
                    cv2.imshow("Foot points", frame)
                    if cv2.waitKey(1) & 255 == 27:
                        break
        summary = {"processed_frames": count, "detections": detections_count, "fps": fps,
                   "sample_every": args.sample_every, "frame_size": size, "model": str(args.model),
                   "classes": detector.model.names, "status": "uncalibrated"}
        (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary))
    finally:
        cap.release()
        if out is not None:
            out.release()
        if not args.headless:
            cv2.destroyAllWindows()
