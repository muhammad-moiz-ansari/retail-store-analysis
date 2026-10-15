"""Standalone video runner; deliberately not wired into the existing backend."""

from __future__ import annotations

import argparse
import json
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
    parser.add_argument("--every", type=int, default=1, help="Process every Nth frame")
    args = parser.parse_args()
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video: {args.video}")
    fps, width, height = cap.get(cv2.CAP_PROP_FPS), int(cap.get(3)), int(cap.get(4))
    writer = cv2.VideoWriter(str(args.output), cv2.VideoWriter_fourcc(*"mp4v"), fps or 25, (width, height))
    pipeline = InteractionPipeline(InteractionConfig(role_model=args.roles))
    frame_number, all_events = 0, []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_number % max(1, args.every) == 0:
            result = pipeline.process_frame(frame, frame_number / (fps or 25))
            all_events.extend(result["interactions"])
            writer.write(draw_result(frame, result))
        frame_number += 1
    cap.release()
    writer.release()
    args.output.with_suffix(".json").write_text(json.dumps(all_events, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
