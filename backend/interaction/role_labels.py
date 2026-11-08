"""Turn reviewed per-person roles into per-track role labels for one pipeline run (B1 -> B2 role accuracy, B3 refit).

`benchmarks/persons.json` holds, per clip, every CVAT `person` track (keyframe boxes, CVAT interpolation) and the
person's reviewed role. Track IDs change whenever tracking changes, so roles are stored per person, not per track:
each run track takes the role of the person its boxes overlap most. Then the clip in the spec gets
`"roles": {"<track_id>": role}` and `"people_file"` (a copy of the run's people.json kept beside the spec).

python -m backend.interaction.role_labels benchmarks/benchmark.json --runs backend/output/role_runs
expects <runs>/<clip stem>.detections.json and .people.json from
`python -m backend.interaction.cli <clip> --every N --track-every N --judge off --output <runs>/<clip stem>.mp4`
run with the spec's every / track_every, so track IDs match the benchmark's own run.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .benchmark import ROOT
from .geometry import iou

PERSONS = Path(__file__).parent / "benchmarks" / "persons.json"
MIN_IOU = 0.3  # a track box this close to a person box is that person in that frame
MIN_SHARE = 0.5  # a track needs this share of its frames on one person, or it stays unlabelled


def box_at(keyframes: list[list[float]], frame: int) -> list[float] | None:
    """CVAT track interpolation: linear between keyframes, absent from an `outside` keyframe to the next one."""
    before = [k for k in keyframes if k[0] <= frame]
    if not before or before[-1][1]:
        return None
    k = before[-1]
    after = next((n for n in keyframes if n[0] > frame), None)
    if after is None:
        return k[2:]
    t = (frame - k[0]) / (after[0] - k[0])
    return [a + t * (b - a) for a, b in zip(k[2:], after[2:])]


def track_roles(detections: list[dict], persons: list[dict]) -> dict[str, str]:
    """{track_id: role} for tracks that sit on one person in at least MIN_SHARE of their frames."""
    votes: dict[int, dict[int, int]] = {}
    for frame in detections:
        for det in frame["people"]:
            scores = [(iou(det["bbox"], box), i) for i, p in enumerate(persons) if (box := box_at(p["keyframes"], frame["frame"]))]
            best = max(scores, default=(0.0, None))
            track = votes.setdefault(det["track_id"], {})
            track[best[1]] = track.get(best[1], 0) + 1 if best[0] >= MIN_IOU else track.get(best[1], 0)
            track[-1] = track.get(-1, 0) + 1  # frames seen
    roles = {}
    for track_id, v in sorted(votes.items()):
        seen = v.pop(-1)
        person, count = max(((p, c) for p, c in v.items() if p is not None), key=lambda pc: pc[1], default=(None, 0))
        if person is not None and count >= MIN_SHARE * seen:
            roles[str(track_id)] = persons[person]["role"]
    return roles


def stem(path: str) -> str:
    return Path(path).stem.replace("Copy of ", "").replace(" ", "_")


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-track role labels from reviewed per-person roles.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--persons", type=Path, default=PERSONS)
    args = parser.parse_args()
    persons = json.loads(args.persons.read_text(encoding="utf-8"))
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    copies = args.spec.parent / "role_runs"
    copies.mkdir(exist_ok=True)
    for video in spec["videos"]:
        run = args.runs / stem(video["path"])
        if video["path"] not in persons or not run.with_suffix(".detections.json").exists():
            print(f"skip {video['path']}: no persons or no run")
            continue
        detections = json.loads(run.with_suffix(".detections.json").read_text(encoding="utf-8"))
        video["roles"] = track_roles(detections, persons[video["path"]])
        people = shutil.copy(run.with_suffix(".people.json"), copies / f"{stem(video['path'])}.people.json")
        video["people_file"] = Path(people).resolve().relative_to(ROOT).as_posix()
        tracks = len({d["track_id"] for f in detections for d in f["people"]})
        print(f"{stem(video['path'])}: {len(video['roles'])} of {tracks} tracks labelled")
    args.spec.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
