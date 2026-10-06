"""Run one bounded SmolVLM role/interaction smoke test on a CCTV clip.

Usage (from the repository root):
  PYTHONPATH=. HF_HOME=vlm_runtime/hf_cache \
    vlm_runtime/.venv/bin/python vlm_runtime/run_smoke.py backend/videos/cam1.mp4
"""

import argparse
import json
from pathlib import Path

import av

from backend.interaction.vlm import SmolVLMClassifier


def read_frames(path: str, count: int = 3):
    with av.open(path) as container:
        stream = container.streams.video[0]
        frames = []
        for frame in container.decode(stream):
            frames.append(frame.to_ndarray(format="bgr24"))
            if len(frames) == count:
                break
        return frames


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--frames", type=int, default=3)
    args = parser.parse_args()
    frames = read_frames(str(args.video), max(1, min(args.frames, 8)))
    if not frames:
        raise RuntimeError("Video contains no decodable frames")
    vlm = SmolVLMClassifier(max_new_tokens=4)
    result = {
        "video": str(args.video),
        "frames": len(frames),
        "role": vlm.classify_role(frames[0]).__dict__,
        "interaction": vlm.classify_interaction(frames).__dict__,
    }
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
