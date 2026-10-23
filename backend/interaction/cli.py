"""Standalone video runner; deliberately not wired into the existing backend."""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from pathlib import Path

import cv2

from .config import DEVICE, InteractionConfig
from .pipeline import InteractionPipeline
from .renderer import draw_result
from .types import CONFIRMED


def center_square(frame):
    """Middle square of a frame; phone camera apps only stream 4:3/16:9 sizes."""
    height, width = frame.shape[:2]
    side = min(height, width)
    top, left = (height - side) // 2, (width - side) // 2
    return frame[top:top + side, left:left + side]


class CameraSwitch:
    """Live feed that flips between the laptop webcam and the phone cam when 's' is pressed in the preview window."""

    def __init__(self, sources: dict[str, str], start: str, raw: Path | None = None, keys=None, square=False):
        self.sources, self.name, self.lock, self.square = sources, start, threading.Lock(), square
        # Key source: the preview window by default; headless runs (the web UI) pass their own.
        self.keys = keys or (lambda: cv2.waitKey(1) & 0xFF)
        self.raw, self.raw_writer = raw, None
        cap = self._open(start)
        if cap is None:
            raise SystemExit(f"Cannot open {start} camera: {sources[start]}")
        self._watch(cap)

    def _open(self, name: str):
        source = self.sources[name]
        # A digit is a Windows camera index (phone apps like DroidCam/Iriun add a virtual webcam); anything else is a stream URL.
        cap = cv2.VideoCapture(int(source)) if source.isdigit() else cv2.VideoCapture(source)
        return cap if cap.isOpened() else None

    def _watch(self, cap) -> None:
        with self.lock:
            self.cap, self.latest, self.fresh = cap, (False, None), threading.Event()
        self.reader = threading.Thread(target=self._drain, args=(cap,), daemon=True)
        self.reader.start()

    def _drain(self, cap) -> None:
        # Pull frames as fast as the camera sends them and keep only the newest, so a slow pipeline
        # never backs up the stream (DroidCam drops frames and the preview lags when it does).
        while True:
            ok, frame = cap.read()
            if ok and self.square:
                frame = center_square(frame)
            with self.lock:
                if cap is not self.cap:
                    break
                self.latest = ok, frame
                self.fresh.set()
                if ok and self.raw:
                    self._record(cap, frame)
            if not ok:
                break
        # Released here, not by the switcher: releasing mid-read from another thread can crash OpenCV.
        cap.release()

    def _record(self, cap, frame) -> None:
        # Every camera frame, not just the ones the pipeline gets to. Sized by the first camera, like the annotated output.
        if self.raw_writer is None:
            self.raw_size = frame.shape[1], frame.shape[0]
            self.raw_writer = cv2.VideoWriter(str(self.raw), cv2.VideoWriter_fourcc(*"mp4v"),
                                              cap.get(cv2.CAP_PROP_FPS) or 25, self.raw_size)
        self.raw_writer.write(cv2.resize(frame, self.raw_size))

    def get(self, prop):
        return self.cap.get(prop)

    def switch(self) -> None:
        other = next(name for name in self.sources if name != self.name)
        cap = self._open(other)
        if cap is None:
            print(f"cannot open {other} camera ({self.sources[other]}), staying on {self.name}")
            return
        self._watch(cap)  # the old reader sees it is stale and releases its camera
        self.name = other
        print(f"switched to {other} camera")

    def read(self):
        key = self.keys()
        if key == ord("q"):
            return False, None
        if key == ord("s"):
            self.switch()
        if not self.fresh.wait(timeout=5):  # stream went silent
            return False, None
        with self.lock:
            self.fresh.clear()
            return self.latest

    def peek(self):
        """Newest camera frame without consuming it (for the web preview)."""
        with self.lock:
            return self.latest[1]

    def release(self) -> None:
        with self.lock:
            self.cap = None
            if self.raw_writer:
                self.raw_writer.release()


def analyse(cap, fps: float, pipeline: InteractionPipeline, every: int = 1, track_every: int = 1, on_result=None, clock=None) -> dict:
    """Run the pipeline over a video; returns one record per interaction (its last snapshot) and per-frame latencies.
    Live feeds pass a wall-clock `clock`, since a camera's nominal FPS is not its delivered rate."""
    frame_number, interactions, latencies = 0, {}, []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        timestamp = clock() if clock else frame_number / (fps or 25)
        if frame_number % max(1, every) == 0:
            started = time.perf_counter()
            result = pipeline.process_frame(frame, timestamp)
            latencies.append(time.perf_counter() - started)
            for event in result["interactions"]:
                # One record per interaction: later snapshots overwrite earlier ones with the final state.
                interactions[(event["employee_track_id"], event["customer_track_id"], event["started_at"])] = event
            if on_result:
                on_result(frame_number, frame, result)
        elif frame_number % max(1, track_every) == 0:
            # Keep the tracker fed between scored frames so IDs survive crossings.
            pipeline.tracker.detect_and_track(frame, timestamp)
        frame_number += 1
    return {"interactions": interactions, "frames": frame_number, "latencies": latencies}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run employee/customer interaction analytics on a video.")
    parser.add_argument("video", type=Path, nargs="?", help="Recorded video; omit with --live")
    parser.add_argument("--live", choices=("laptop", "phone"),
                        help="Analyse a live camera instead, starting on this one; press s to switch, q to stop")
    parser.add_argument("--laptop-cam", default="0", help="Laptop webcam index")
    parser.add_argument("--phone-cam", default="1",
                        help="Phone camera: the virtual webcam index its app adds, or its stream URL (e.g. http://<phone-ip>:4747/video)")
    parser.add_argument("--output", type=Path, default=Path("interaction_output.mp4"))
    parser.add_argument("--roles", type=Path, help="YOLO role model trained on the bib-labelled dataset")
    parser.add_argument("--every", type=int, default=1, help="Score roles and write output on every Nth frame")
    parser.add_argument("--track-every", type=int, default=1, help="Run the tracker on every Nth frame (3 = 10 fps on 30 fps video)")
    parser.add_argument("--device", default=DEVICE, help="Inference device, e.g. cpu or cuda:0")
    parser.add_argument("--judge", choices=("pose", "off"), default="pose",
                        help="Second model that confirms each proximity interaction")
    parser.add_argument("--judge-device", help="Device for the judge, defaults to --device")
    parser.add_argument("--square", action="store_true", help="Live: crop each camera frame to its centre square")
    parser.add_argument("--stop-file", type=Path,
                        help="Live without a preview window (for the web UI): stop when this file appears; "
                             "the newest camera frame, with the latest detections drawn, is kept at <output>.preview.jpg")
    args = parser.parse_args()
    headless = args.stop_file is not None
    preview = args.output.with_suffix(".preview.jpg")
    if args.live:
        keys = (lambda: ord("q") if args.stop_file.exists() else -1) if headless else None
        cap = CameraSwitch({"laptop": args.laptop_cam, "phone": args.phone_cam}, args.live,
                           args.output.with_suffix(".raw.mp4"), keys, args.square)
    elif args.video:
        cap = cv2.VideoCapture(str(args.video))
        if not cap.isOpened():
            raise SystemExit(f"Cannot open video: {args.video}")
    else:
        parser.error("give a video path or --live")
    latest_result, preview_done = {}, threading.Event()

    def write_preview():
        # Camera rate, not model rate: the newest frame with the newest detections drawn on it, so the
        # web view stays smooth while boxes update as fast as the model runs (~3 fps on CPU).
        while not preview_done.wait(1 / 15):
            frame = cap.peek()
            if frame is None:
                continue
            result = latest_result.get("result")
            # Write then rename, so the web UI never reads a half-written JPEG.
            cv2.imwrite(str(preview.with_suffix(".tmp.jpg")), draw_result(frame, result) if result else frame)
            os.replace(preview.with_suffix(".tmp.jpg"), preview)

    if args.live and headless:  # started before the models load, so the camera shows up straight away
        threading.Thread(target=write_preview, daemon=True).start()
    fps, width, height = cap.get(cv2.CAP_PROP_FPS), int(cap.get(3)), int(cap.get(4))
    if args.live and args.square:  # the camera reports its stream size, not the cropped one
        width = height = min(width, height)
    writer = cv2.VideoWriter(str(args.output), cv2.VideoWriter_fourcc(*"mp4v"), fps or 25, (width, height))
    pipeline = InteractionPipeline(InteractionConfig(role_model=args.roles, device=args.device,
                                                     interaction_judge=args.judge, judge_device=args.judge_device))
    tracks, detections = {}, []

    def record(frame_number, frame, result):
        detections.append({"frame": frame_number, "timestamp": round(result["timestamp"], 2),
                           "interaction_active": result["interaction_active"], "people": result["people"]})
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
        latest_result["result"] = result
        annotated = draw_result(frame, result)
        if args.live:
            if not headless:
                cv2.imshow("interaction (s: switch camera, q: quit)", annotated)
            # The two cameras can differ in resolution; the writer needs one size.
            annotated = cv2.resize(annotated, (width, height))
        writer.write(annotated)

    started = time.perf_counter()
    clock = (lambda: time.perf_counter() - started) if args.live else None
    try:
        run = analyse(cap, fps, pipeline, args.every, args.track_every, record, clock)
    finally:
        preview_done.set()
        cap.release()
        if args.live and not headless:
            cv2.destroyAllWindows()
    interactions, frame_number = run["interactions"], run["frames"]
    elapsed, duration = time.perf_counter() - started, frame_number / (fps or 25)
    if args.live:  # stale frames are skipped, so frame count is not video time; throughput is what matters
        print(f"live: {elapsed:.1f}s, {frame_number} frames processed ({frame_number / elapsed:.1f} fps)")
    else:
        print(f"processed {duration:.1f}s of video in {elapsed:.1f}s ({duration / elapsed:.2f}x realtime)")
    writer.release()
    kept = [event for event in interactions.values() if event["verdict"] in CONFIRMED]
    rejected = [event for event in interactions.values() if event["verdict"] not in CONFIRMED]
    args.output.with_suffix(".interactions.json").write_text(json.dumps(kept, indent=2), encoding="utf-8")
    if pipeline.judge:
        args.output.with_suffix(".rejected_interactions.json").write_text(json.dumps(rejected, indent=2), encoding="utf-8")
        print(f"{args.judge} judge kept {len(kept)} of {len(interactions)} proximity interactions")
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
