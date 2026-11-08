"""Copy reviewed labels from a CVAT "CVAT for video 1.1" export into benchmark.json.

Labelling convention in CVAT (one task per clip, task name contains the video file name):
  - label `interaction`: one track per interaction; draw any box while it lasts (start/end = visible span).
  - label `pass_by`: same, for close pass-bys that are NOT assistance (kept in the clip note).
  - label `person`: one track per distinct person; the count becomes "people".
Usage: python -m backend.interaction.cvat_import export.xml [benchmark.json]
"""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = Path(__file__).parent / "benchmarks" / "benchmark.json"


def spans(track: ET.Element) -> list[tuple[int, int]]:
    """Visible [first, last] frame spans; a box with outside=1 ends the span."""
    out, start, last = [], None, None
    for box in sorted(track, key=lambda b: int(b.get("frame", 0))):
        frame = int(box.get("frame"))
        if box.get("outside") == "1":
            if start is not None:
                out.append((start, frame - 1))
            start = None
        else:
            start = frame if start is None else start
            last = frame
    if start is not None:
        out.append((start, last))
    return out


def import_labels(xml_path: Path, bench_path: Path = DEFAULT) -> list[str]:
    bench = json.loads(bench_path.read_text())
    root, done = ET.parse(xml_path).getroot(), []
    task = (root.findtext("meta/task/name") or xml_path.stem)
    video = next((v for v in bench["videos"] if Path(v["path"]).stem in task or Path(v["path"]).name in task), None)
    if video is None:
        raise SystemExit(f"No clip in benchmark.json matches CVAT task name {task!r}")
    cap = cv2.VideoCapture(str(ROOT / video["path"]))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    cap.release()
    tracks = {"interaction": [], "pass_by": [], "person": 0}
    for t in root.iter("track"):
        label = t.get("label")
        if label == "person":
            tracks["person"] += 1
        elif label in tracks:
            tracks[label] += [{"start": round(a / fps, 1), "end": round((b + 1) / fps, 1)} for a, b in spans(t)]
    video["interactions"] = sorted(tracks["interaction"], key=lambda i: i["start"])
    video["pass_bys"] = sorted(tracks["pass_by"], key=lambda i: i["start"])
    if tracks["person"]:
        video["people"] = tracks["person"]
    video.pop("candidates_to_review", None)
    if video.get("note", "").startswith("Not labelled yet"):
        video.pop("note")
    bench_path.write_text(json.dumps(bench, indent=2) + "\n")
    return [f"{video['path']}: {len(video['interactions'])} interactions, {len(video['pass_bys'])} pass-bys, people={video.get('people')}"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("xml", type=Path)
    ap.add_argument("benchmark", type=Path, nargs="?", default=DEFAULT)
    print("\n".join(import_labels(**{"xml_path": ap.parse_args().xml, "bench_path": ap.parse_args().benchmark})))
