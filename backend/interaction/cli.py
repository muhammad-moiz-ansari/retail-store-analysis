"""Standalone video runner; deliberately not wired into the existing backend."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2

from .config import InteractionConfig
from .pipeline import InteractionPipeline
from .renderer import draw_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run employee/customer interaction analytics on a video.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path, default=Path("interaction_output.mp4"))
    parser.add_argument("--roles", type=Path, help="YOLO role model trained on the bib-labelled dataset")
    parser.add_argument("--every", type=int, default=1, help="Score roles and write output on every Nth frame")
    parser.add_argument("--track-every", type=int, default=1, help="Run the tracker on every Nth frame (3 = 10 fps on 30 fps video)")
    parser.add_argument("--device", default="cpu", help="Inference device, e.g. cpu or cuda:0")
    args = parser.parse_args()
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video: {args.video}")
    fps, width, height = cap.get(cv2.CAP_PROP_FPS), int(cap.get(3)), int(cap.get(4))
    writer = cv2.VideoWriter(str(args.output), cv2.VideoWriter_fourcc(*"mp4v"), fps or 25, (width, height))
    pipeline = InteractionPipeline(InteractionConfig(role_model=args.roles, device=args.device))
    frame_number, all_events, tracks, detections = 0, [], {}, []
    started = time.perf_counter()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_number % max(1, args.every) == 0:
            result = pipeline.process_frame(frame, frame_number / (fps or 25))
            all_events.extend(result["interactions"])
            detections.append({"frame": frame_number, "timestamp": round(result["timestamp"], 2), "people": result["people"]})
            for person in result["people"]:
                track = tracks.setdefault(person["track_id"], {"first_seen": result["timestamp"], "factors": []})
                track["last_seen"] = result["timestamp"]
                track["factors"].append(person["role_evidence"]["factors"])
                segments = track.setdefault("role_segments", [])
                if segments and segments[-1]["role"] == person["role"]:
                    segments[-1]["to"] = result["timestamp"]
                    segments[-1]["frames"] += 1
                else:
                    segments.append({"role": person["role"], "from": result["timestamp"], "to": result["timestamp"], "frames": 1})
            writer.write(draw_result(frame, result))
        elif frame_number % max(1, args.track_every) == 0:
            # Keep the tracker fed between scored frames so IDs survive crossings.
            pipeline.tracker.detect_and_track(frame, frame_number / (fps or 25))
        frame_number += 1
    cap.release()
    elapsed, duration = time.perf_counter() - started, frame_number / (fps or 25)
    print(f"processed {duration:.1f}s of video in {elapsed:.1f}s ({duration / elapsed:.2f}x realtime)")
    writer.release()
    args.output.with_suffix(".json").write_text(json.dumps(all_events, indent=2), encoding="utf-8")
    args.output.with_suffix(".detections.json").write_text(json.dumps(detections, indent=2), encoding="utf-8")
    people = [
        {"track_id": track_id, "first_seen": round(t["first_seen"], 2), "last_seen": round(t["last_seen"], 2),
         "frames_observed": len(t["factors"]), **pipeline.classifier.agent.classify_person(t["factors"]),
         # Final role = the held (3 s debounced) role this ID kept the longest; segments expose ID swaps.
         "role": max(("employee", "customer"), key=lambda r: sum(s["frames"] for s in t["role_segments"] if s["role"] == r)),
         "role_segments": t["role_segments"]}
        for track_id, t in sorted(tracks.items())
    ]
    args.output.with_suffix(".people.json").write_text(
        json.dumps({"weights": pipeline.classifier.agent.weights, "threshold": pipeline.classifier.agent.threshold, "people": people}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
