"""Aisle relay, live CV: one split-screen video holds two aisle cameras; each frame goes through YOLO once and the
detections are split back into the two feeds before the watcher sees them.

  find_split         locates the white gutter between the two feeds (left = Aisle 1, right = Aisle 2).
  SplitFeedDetector  ONE person-tracking pass (YOLO + ByteTrack) over the whole frame; each person is handed to the
                     aisle whose half holds the centre of their box, and boxes over the gutter are dropped. The
                     employee/customer role model gets both halves in one batched call: it is a 320 px model, and
                     shrinking the whole 1920 px frame into it mislabelled customers (measured on multirow.mp4).
  LiveRelayRun       reads the video in a background thread, paced like a live camera (frames the CV cannot keep up
                     with are dropped, not queued), and feeds per-aisle counts to the same AisleWatcher + StoreBridge
                     as the replay, so a "need" becomes a real alert, dispatch decision and employee task while the
                     video plays. Publishes an annotated JPEG per sample (the manager page's MJPEG view) and, at the
                     end, annotated.webm + trace.json in its output folder (the trace can be replayed later).

Used by backend.aisle_relay's routes (POST /aisle-relay/start with mode "live") and by scripts/aisle_relay_demo.py
(offline, every sampled frame, no pacing).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from fractions import Fraction
from types import SimpleNamespace
from typing import Any, Callable, Protocol

import cv2
import numpy as np

from .aisle_relay import RelayBase, WatchPolicy, aisle_label

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIDEO = ROOT / "backend" / "videos" / "multirow.mp4"
FITTED = ROOT / "backend" / "interaction" / "benchmarks" / "store_roles_fitted.json"
AISLES = ("aisle-1", "aisle-2")
PREVIEW_WIDTH = 1280
COLORS = {"employee": (60, 200, 60), "customer": (0, 150, 255), "unknown": (180, 180, 180)}


# ---------------------------------------------------------------------------------------------------------------
# Splitting one frame into two feeds
# ---------------------------------------------------------------------------------------------------------------

def find_split(frame: np.ndarray, white: float = 240.0) -> dict:
    """{"gutter": [x0, x1], "crops": {"aisle-1": [0, x0], "aisle-2": [x1, w]}} from the bright column band nearest the
    centre (searched in the middle 40% of the frame). Without a gutter the frame is halved."""
    w = frame.shape[1]
    bright = frame.mean(axis=(0, 2)) > white
    lo, hi = int(w * 0.3), int(w * 0.7)
    runs, start = [], None
    for x in range(lo, hi + 1):
        on = x < hi and bright[x]
        if on and start is None:
            start = x
        elif not on and start is not None:
            runs.append((start, x))
            start = None
    if runs:
        gx0, gx1 = min(runs, key=lambda r: abs((r[0] + r[1]) / 2 - w / 2))
    else:
        gx0 = gx1 = w // 2
    return {"gutter": [int(gx0), int(gx1)], "crops": {"aisle-1": [0, int(gx0)], "aisle-2": [int(gx1), int(w)]}}


def aisle_of(box: list[int] | tuple[int, ...], crops: dict[str, list[int]]) -> str | None:
    cx = (box[0] + box[2]) / 2
    for aisle, (x0, x1) in crops.items():
        if x0 <= cx < x1:
            return aisle
    return None  # over the gutter


def split_people(people: list[dict], crops: dict[str, list[int]]) -> dict[str, dict]:
    """Whole-frame detections -> per-aisle feeds with counts. Each box is clipped to its own half."""
    feeds: dict[str, dict] = {a: {"customers": 0, "employees": 0, "people": []} for a in crops}
    for p in people:
        aisle = aisle_of(p["box"], crops)
        if aisle is None:
            continue
        x0, x1 = crops[aisle]
        box = [max(p["box"][0], x0), p["box"][1], min(p["box"][2], x1), p["box"][3]]
        feeds[aisle]["people"].append({**p, "id": f"{aisle[-1]}-{p['track']}", "box": box})
        if p["role"] == "customer":
            feeds[aisle]["customers"] += 1
        elif p["role"] == "employee":
            feeds[aisle]["employees"] += 1
    return feeds


# ---------------------------------------------------------------------------------------------------------------
# Detector: one YOLO pass per frame for both feeds
# ---------------------------------------------------------------------------------------------------------------

class Detector(Protocol):
    description: dict

    def __call__(self, frame: np.ndarray, t: float) -> list[dict]:
        """People in the whole frame: [{"track", "box": [x0, y0, x1, y1], "conf", "role", "score", "yolo_role"}]."""


class _PerFeedRoleModel:
    """Stands in for the role model inside RoleClassifier: one batched call over both halves, boxes mapped back to
    whole-frame coordinates, in the result shape RoleClassifier reads (boxes with xyxy/cls/conf, names)."""

    def __init__(self, model, crops: dict[str, list[int]]):
        self.model, self.crops = model, list(crops.values())

    def __call__(self, frame: np.ndarray, **kwargs):
        halves = [frame[:, x0:x1] for x0, x1 in self.crops]
        merged, names = [], {}
        for result, (x0, _) in zip(self.model(halves, **kwargs), self.crops):
            names = result.names
            if result.boxes is None:
                continue
            for xyxy, cls, conf in zip(result.boxes.xyxy.cpu().numpy(), result.boxes.cls.cpu().numpy(),
                                       result.boxes.conf.cpu().numpy()):
                merged.append(SimpleNamespace(xyxy=np.array([[xyxy[0] + x0, xyxy[1], xyxy[2] + x0, xyxy[3]]]),
                                              cls=np.array([cls]), conf=np.array([conf])))
        return [SimpleNamespace(boxes=merged, names=names)]


class SplitFeedDetector:
    def __init__(self, split: dict, imgsz: int = 640, conf: float = 0.35):
        from ultralytics import YOLO

        from .device import DEVICE
        from .interaction.config import InteractionConfig
        from .interaction.role_classifier import RoleClassifier

        self.cfg = InteractionConfig.from_json(FITTED)
        self.imgsz, self.conf, self.device = imgsz, conf, DEVICE
        self.tracker = YOLO(str(self.cfg.person_model))
        role_model = YOLO(str(self.cfg.role_model), task="detect") if self.cfg.role_model else None
        self.roles = RoleClassifier(self.cfg, _PerFeedRoleModel(role_model, split["crops"]) if role_model else None)
        self.description = {
            "person_tracker": Path(self.cfg.person_model).name + " (COCO, ByteTrack, one pass over both feeds)",
            "role_model": (Path(self.cfg.role_model).name if self.cfg.role_model else "bib colour")
                          + " (employee/customer, both feeds in one batch)",
            "role_weights": self.cfg.role_weights, "employee_threshold": self.cfg.employee_score_threshold,
        }

    def __call__(self, frame: np.ndarray, t: float) -> list[dict]:
        res = self.tracker.track(frame, persist=True, classes=[0], imgsz=self.imgsz, conf=self.conf, verbose=False,
                                 tracker="bytetrack.yaml", device=self.device)[0]
        people = []
        if res.boxes is None or res.boxes.id is None:
            return people
        for box, tid, conf in zip(res.boxes.xyxy.cpu().numpy(), res.boxes.id.int().cpu().tolist(),
                                  res.boxes.conf.cpu().tolist()):
            bx = tuple(int(v) for v in box)
            role, score, ev = self.roles.classify(frame, bx, tid, t)  # the role model runs at most once per frame
            people.append({"track": tid, "box": list(bx), "conf": round(conf, 2), "role": role,
                           "score": round(score, 3), "yolo_role": ev["yolo_role"]})
        return people


# ---------------------------------------------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------------------------------------------

def draw(frame: np.ndarray, feeds: dict[str, dict], crops: dict[str, list[int]], t: float, requested: list[str]) -> np.ndarray:
    canvas = frame.copy()
    for aisle, (x0, x1) in crops.items():
        s = feeds[aisle]
        for p in s["people"]:
            x, y, X, Y = p["box"]
            col = COLORS.get(p["role"], COLORS["unknown"])
            cv2.rectangle(canvas, (x, y), (X, Y), col, 4)
            tag = f"{p['role']} {p['id']}"
            cv2.rectangle(canvas, (x, max(0, y - 40)), (x + 22 * len(tag), max(40, y)), col, -1)
            cv2.putText(canvas, tag, (x + 6, max(30, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
        if aisle in requested:
            state, col = "HELP SENT", (0, 140, 255)
        elif s["customers"] and not s["employees"]:
            state, col = "UNCOVERED", (40, 40, 230)
        else:
            state, col = ("COVERED", (60, 160, 60)) if s["employees"] else ("IDLE", (120, 120, 120))
        cv2.rectangle(canvas, (x0, 0), (x1, 70), (25, 25, 25), -1)
        cv2.putText(canvas, f"{aisle_label(aisle).upper()}  C:{s['customers']} E:{s['employees']}", (x0 + 20, 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3)
        cv2.putText(canvas, state, (x1 - 30 - 24 * len(state), 48), cv2.FONT_HERSHEY_SIMPLEX, 1.3, col, 3)
    cv2.putText(canvas, f"{t:5.1f}s", (crops["aisle-1"][1] - 160, canvas.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 1.4,
                (255, 255, 255), 3)
    return canvas


class _VideoOut:
    """annotated.webm: VP8 through PyAV (plays in every current browser, including Chromium builds without H.264),
    realtime encoder settings so it keeps up with the CV. Without PyAV, OpenCV's mp4v (saved, not playable)."""

    def __init__(self, folder: Path, fps: float, size: tuple[int, int]):
        self.count, self.container = 0, None
        try:
            import av

            self.path = folder / "annotated.webm"
            self.rate = Fraction(fps).limit_denominator(1000)
            self.container = av.open(str(self.path), "w")
            self.stream = self.container.add_stream("libvpx", rate=self.rate)
            self.stream.width, self.stream.height, self.stream.pix_fmt = size[0], size[1], "yuv420p"
            self.stream.bit_rate = 2_500_000
            self.stream.options = {"deadline": "realtime", "cpu-used": "8"}
            self.frame_type = av.VideoFrame
        except ImportError:
            self.path = folder / "annotated.mp4"
            self.writer = cv2.VideoWriter(str(self.path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)

    def write(self, frame: np.ndarray) -> None:
        if self.container is None:
            self.writer.write(frame)
            return
        packet = self.frame_type.from_ndarray(frame, format="bgr24")
        packet.pts, packet.time_base = self.count, 1 / self.rate
        self.count += 1
        self.container.mux(self.stream.encode(packet))

    def close(self) -> None:
        if self.container is None:
            self.writer.release()
            return
        self.container.mux(self.stream.encode())
        self.container.close()


# ---------------------------------------------------------------------------------------------------------------
# The live run
# ---------------------------------------------------------------------------------------------------------------

class LiveRelayRun(RelayBase):
    mode = "live"

    def __init__(self, video: Path, connect: Callable[[], Any] | None, out_dir: Path, zones: dict[str, str] | None = None,
                 policy: WatchPolicy | None = None, stride: int = 4, realtime: bool = True, speed: float = 1.0,
                 max_seconds: float | None = None, detector: Callable[[dict], Detector] | None = None,
                 write_video: bool = True, log: Callable[[str], None] | None = None):
        self.video = Path(video)
        cap = cv2.VideoCapture(str(self.video))
        ok, probe = cap.read()
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        if not ok:
            raise ValueError(f"cannot read frames from {self.video.name}")
        self.frame_size = [int(probe.shape[1]), int(probe.shape[0])]
        self.split = find_split(probe)
        super().__init__(connect, zones, policy, speed)
        self.out_dir = Path(out_dir)
        self.stride, self.realtime, self.max_seconds = max(1, stride), realtime, max_seconds
        self.make_detector = detector or SplitFeedDetector
        self.write_video, self.log = write_video, log or (lambda line: None)
        self.models: dict = {}
        self.samples: list[dict] = []
        self.tracks: dict[str, dict] = {}
        self.dropped = 0  # sampled frames skipped because the CV fell behind the clock
        self.preview: bytes | None = None
        self.preview_seq = 0
        self.processing_s = 0.0
        self.video_path: Path | None = None

    @property
    def duration(self) -> float:
        full = self.frames / self.fps if self.frames else 0.0
        return round(min(full, self.max_seconds) if self.max_seconds else full, 2)

    def source_info(self) -> dict:
        busy = self.processing_s or (time.time() - self.started_at if self.started_at else 0.0)
        return {"video": self.video.name, "models": self.models, "split": self.split, "frameSize": self.frame_size,
                "fps": self.fps, "stride": self.stride, "realtime": self.realtime,
                "samples": len(self.samples), "droppedSamples": self.dropped,
                "processingFps": round(len(self.samples) / busy, 2) if busy else None,
                "processingSeconds": round(busy, 1)}

    def snapshot(self) -> dict:
        return {**super().snapshot(), "preview": self.preview_seq if self.preview else None}

    def _run(self) -> None:
        self.state = "loading models"
        detect = self.make_detector(self.split)
        self.models = dict(getattr(detect, "description", {}))
        self.out_dir.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(str(self.video))
        w, h = self.frame_size
        vw, vh = PREVIEW_WIDTH, int(round(PREVIEW_WIDTH * h / w / 2) * 2)
        out = _VideoOut(self.out_dir, self.fps / self.stride, (vw, vh)) if self.write_video else None
        crops = self.split["crops"]
        self.state = "running"
        clock = time.time()  # the live clock starts once the models are loaded
        self.started_at = clock
        pos = 0  # index of the next frame the capture will return
        k = 0  # index of the next frame to analyse
        try:
            while not self._stop.is_set() and (not self.frames or k < self.frames):
                if self.realtime:
                    live = int((time.time() - clock) * self.speed * self.fps) // self.stride * self.stride
                    if self.frames:
                        live = min(live, self.frames)  # the clock can run past the last frame; nothing is dropped there
                    if live > k:  # behind: a live camera does not wait, skip to the newest sampled frame
                        self.dropped += -(-(live - k) // self.stride)
                        k = live
                        if self.frames and k >= self.frames:
                            break
                    wait = clock + k / self.fps / self.speed - time.time()
                    if wait > 0 and self._stop.wait(wait):
                        break
                t = k / self.fps
                if self.max_seconds is not None and t > self.max_seconds:
                    break
                while pos < k and cap.grab():
                    pos += 1
                ok, frame = cap.read()
                if not ok:
                    break
                pos += 1
                feeds = split_people(detect(frame, t), crops)
                self.step(t, {a: {"customers": f["customers"], "employees": f["employees"]} for a, f in feeds.items()})
                requested = self.requested()
                self._record(t, feeds, requested)
                small = cv2.resize(draw(frame, feeds, crops, t, requested), (vw, vh), interpolation=cv2.INTER_AREA)
                ok, jpeg = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if ok:
                    self.preview, self.preview_seq = jpeg.tobytes(), self.preview_seq + 1
                if out:
                    out.write(small)
                if len(self.samples) % 50 == 0:
                    self.log(f"t={t:5.1f}s  {len(self.samples)} samples  {self.dropped} dropped  "
                             f"{time.time() - clock:5.1f}s wall")
                k += self.stride
        finally:
            cap.release()
            self.processing_s = round(time.time() - clock, 1)
            if out:
                out.close()
                self.video_path = out.path
            self._write_trace()

    def _record(self, t: float, feeds: dict[str, dict], requested: list[str]) -> None:
        for aisle, f in feeds.items():
            for p in f["people"]:
                tr = self.tracks.setdefault(p["id"], {"aisle": aisle, "first": round(t, 2), "roles": {}})
                tr["last"] = round(t, 2)
                tr["roles"][p["role"]] = tr["roles"].get(p["role"], 0) + 1
        self.samples.append({"t": round(t, 2), "aisles": feeds, "requested": requested})

    def _write_trace(self) -> None:
        tracks = {k: {**v, "role": max(v["roles"], key=v["roles"].get)} for k, v in self.tracks.items()}
        trace = {
            "video": self.video.name, "fps": self.fps, "frames": self.frames, "stride": self.stride,
            "sample_fps": round(self.fps / self.stride, 2), "duration_s": round(self.t, 2) or self.duration,
            "frame_size": self.frame_size, "split": self.split, "models": self.models, "realtime": self.realtime,
            "dropped_samples": self.dropped, "policy": self.snapshot()["policy"], "processing_s": self.processing_s,
            "tracks": tracks, "steps": self.steps, "samples": self.samples,
        }
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / "trace.json").write_text(json.dumps(trace))

    def video_dir(self) -> Path:
        return self.out_dir


# ---------------------------------------------------------------------------------------------------------------
# Command line: the offline CV pass (every sampled frame, no pacing)
# ---------------------------------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Two-aisle relay CV pass over a split-screen clip (one YOLO pass per frame).")
    ap.add_argument("video", type=Path, nargs="?", default=DEFAULT_VIDEO)
    ap.add_argument("--out", type=Path, default=ROOT / "dummyoutputs" / "multirow")
    ap.add_argument("--stride", type=int, default=4, help="analyse every Nth frame (60 fps / 4 = 15 fps)")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--dispatch", action="store_true", help="send need/arrived signals to the store database as they happen")
    ap.add_argument("--realtime", action="store_true", help="pace like a live camera and drop frames the CV cannot keep up with")
    ap.add_argument("--max-seconds", type=float, help="stop after this much video (quick checks)")
    a = ap.parse_args(argv)
    connect = None
    if a.dispatch:
        from .database import connect
    run = LiveRelayRun(a.video, connect, a.out, stride=a.stride, realtime=a.realtime, max_seconds=a.max_seconds,
                       detector=lambda split: SplitFeedDetector(split, imgsz=a.imgsz), log=lambda line: print(line, flush=True)).start()
    seen = 0
    while run._thread.is_alive():
        time.sleep(0.2)
        for s in run.steps[seen:]:
            o = s.get("outcome") or {}
            print(f"{s['t']:6.2f}s {s['kind']:8} {s['text']}" + (f"  -> {o.get('decision')}" if o else ""), flush=True)
        seen = len(run.steps)
    print(json.dumps({"state": run.state, "error": run.error, "signals": len(run.steps), "tracks": len(run.tracks),
                      "processing_s": run.processing_s, "dropped": run.dropped, "video": str(run.video_path)}))


if __name__ == "__main__":
    main()
