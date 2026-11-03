"""Model KPIs: detector accuracy on the held-out split, interaction accuracy and speed on annotated videos.

python -m backend.interaction.benchmark backend/interaction/benchmarks/benchmark.json --output report.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path

from .config import DEVICE

ROOT = Path(__file__).resolve().parents[2]


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def interval_iou(a: tuple[float, float], b: tuple[float, float]) -> float:
    overlap = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return overlap / union if union > 0 else 0.0


def match_events(predicted: list[tuple[float, float]], truth: list[tuple[float, float]], min_iou: float) -> dict:
    """One-to-one greedy matching by temporal IoU, best pairs first."""
    pairs = sorted(((interval_iou(p, t), i, j) for i, p in enumerate(predicted) for j, t in enumerate(truth)), reverse=True)
    used_p, used_t, errors = set(), set(), []
    for iou, i, j in pairs:
        if iou < min_iou or i in used_p or j in used_t:
            continue
        used_p.add(i), used_t.add(j)
        errors.append((abs(predicted[i][0] - truth[j][0]), abs(predicted[i][1] - truth[j][1])))
    tp = len(errors)
    return {"tp": tp, "fp": len(predicted) - tp, "fn": len(truth) - tp,
            "start_error_s": statistics.mean(e[0] for e in errors) if errors else None,
            "end_error_s": statistics.mean(e[1] for e in errors) if errors else None}


def scores(counts: dict) -> dict:
    precision, recall = ratio(counts["tp"], counts["tp"] + counts["fp"]), ratio(counts["tp"], counts["tp"] + counts["fn"])
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else (0.0 if precision is not None and recall is not None else None)
    return {**counts, "precision": precision, "recall": recall, "f1": f1}


def role_counts(predicted: dict[int, str], truth: dict[str, str]) -> dict:
    """Per-role tp/fp/fn over the labelled tracks; an `unknown` prediction is a miss, not a false alarm."""
    labelled = [(predicted.get(int(track_id), "unseen"), role) for track_id, role in truth.items()]
    counts = {role: {"tp": sum(p == t == role for p, t in labelled), "fp": sum(p == role != t for p, t in labelled),
                     "fn": sum(t == role != p for p, t in labelled)} for role in ("employee", "customer")}
    return {**counts, "tracks": len(labelled), "correct": sum(p == t for p, t in labelled),
            "unknown": sum(p == "unknown" for p, _ in labelled)}


def timing_error(matches: list[dict]) -> dict:
    """Start/end error over every matched interaction, each video weighted by its true positives."""
    tp = sum(m["tp"] for m in matches if m["start_error_s"] is not None)
    mean = lambda key: sum(m[key] * m["tp"] for m in matches if m[key] is not None) / tp if tp else None
    return {"start_error_s": mean("start_error_s"), "end_error_s": mean("end_error_s")}


def tracking_kpis(track_roles: dict[int, list[str]], minutes: float, people: int | None) -> dict:
    """Track stability without per-frame ground truth. With the reviewed number of distinct people in the clip,
    every extra track ID is a fragment (an ID switch or a lost-and-new track); role flips count held-role changes."""
    flips = sum(sum(a != b for a, b in zip(roles, roles[1:])) for roles in track_roles.values())
    per_min = lambda n: n / minutes if minutes else None
    return {"tracks": len(track_roles), "minutes": minutes, "people": people, "role_flips_per_min": per_min(flips),
            "id_switches_per_min": per_min(max(0, len(track_roles) - people)) if people is not None else None}


def detector_kpis(spec: dict, device: str) -> dict:
    """Ultralytics val on a YOLO-format folder (labels next to images)."""
    from ultralytics import YOLO

    images = Path(spec["dataset"]).expanduser() / "obj_train_data"
    names = (images.parent / "obj.names").read_text().split()
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data.yaml"
        data.write_text(json.dumps({"path": str(images), "train": str(images), "val": str(images), "names": dict(enumerate(names))}))
        model = YOLO(str(ROOT / spec["model"]), task="detect")
        result = model.val(data=str(data), imgsz=spec.get("imgsz", 640), batch=1, device=device, plots=False,
                           project=tmp, verbose=False)
    box = result.box
    return {"model": spec["model"], "dataset": spec["dataset"], "images": len(list(images.glob("*.jpg"))),
            "map50": box.map50, "map50_95": box.map, "precision": box.mp, "recall": box.mr,
            "classes": {name: dict(zip(("precision", "recall", "map50", "map50_95"), box.class_result(i)))
                        for i, name in enumerate(names) if i < len(box.ap_class_index)},
            "inference_ms_per_image": result.speed.get("inference")}


def video_kpis(spec: dict, judge: str, device: str, min_iou: float) -> dict:
    import cv2

    from .cli import analyse
    from .config import InteractionConfig
    from .pipeline import InteractionPipeline
    from .types import CONFIRMED

    # A per-video store/camera config (e.g. with or without role_references) measures cross-store generalisation.
    config = InteractionConfig.from_json(spec.get("config") and ROOT / spec["config"], device=device, interaction_judge=judge)
    pipeline = InteractionPipeline(config)
    judge_times: list[float] = []
    if pipeline.judge:
        classify = pipeline.judge.classify_interaction

        def timed(*args, **kwargs):
            started = time.perf_counter()
            try:
                return classify(*args, **kwargs)
            finally:
                judge_times.append(time.perf_counter() - started)
        pipeline.judge.classify_interaction = timed
    cap = cv2.VideoCapture(str(ROOT / spec["path"]))
    if not cap.isOpened():
        raise SystemExit(f"Cannot open video: {spec['path']}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    started = time.perf_counter()
    role_frames: dict[int, dict[str, int]] = {}
    track_roles: dict[int, list[str]] = {}  # role sequence per track, for flips

    def tally(_frame_number, _frame, result):
        for person in result["people"]:
            frames = role_frames.setdefault(person["track_id"], {})
            frames[person["role"]] = frames.get(person["role"], 0) + 1
            track_roles.setdefault(person["track_id"], []).append(person["role"])
    run = analyse(cap, fps, pipeline, spec.get("every", 1), spec.get("track_every", 1), tally)
    elapsed = time.perf_counter() - started
    cap.release()
    events = list(run["interactions"].values())
    interval = lambda e: (e["started_at"], e["last_seen_at"])
    latencies = sorted(run["latencies"])
    # A video without reviewed "interactions" is not labelled yet: speed only, no accuracy.
    truth = [(t["start"], t["end"]) for t in spec["interactions"]] if "interactions" in spec else None
    return {
        "path": spec["path"], "duration_s": run["frames"] / fps,
        # Proximity alone = every candidate the judge saw; with judge = the ones it kept.
        "proximity_only": None if truth is None else match_events([interval(e) for e in events], truth, min_iou),
        "with_judge": None if truth is None else match_events([interval(e) for e in events if e["verdict"] in CONFIRMED], truth, min_iou),
        # "roles": {"<track_id>": "employee" | "customer"} from a reviewed run with the same settings.
        "roles": role_counts({t: max(f, key=f.get) for t, f in role_frames.items()}, spec["roles"]) if "roles" in spec else None,
        # "people": distinct people a reviewer counted in the clip; extra track IDs are fragments.
        "tracking": tracking_kpis(track_roles, run["frames"] / fps / 60, spec.get("people")),
        "candidates": [{"start": round(e["started_at"], 1), "end": round(e["last_seen_at"], 1), "verdict": e["verdict"]} for e in events],
        "speed": {"realtime_factor": run["frames"] / fps / elapsed,
                  "frame_ms_p50": 1000 * latencies[len(latencies) // 2] if latencies else None,
                  "frame_ms_p95": 1000 * latencies[int(len(latencies) * 0.95)] if latencies else None,
                  "judge_calls": len(judge_times),
                  "judge_ms_mean": 1000 * statistics.mean(judge_times) if judge_times else None},
    }


def check_targets(report: dict, targets: dict) -> list[str]:
    failures = []
    for name, limit in targets.items():
        value = report
        for part in name.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if value is None:
            failures.append(f"{name}: not measured")
        elif value < limit:
            failures.append(f"{name}: {value:.3f} < {limit}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the detector, the interaction judge and pipeline speed.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output", type=Path, default=Path("benchmark_report.json"))
    parser.add_argument("--judge", choices=("pose", "off"), default="pose")
    parser.add_argument("--device", default=DEVICE)
    parser.add_argument("--skip-detector", action="store_true")
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    min_iou = spec.get("temporal_iou", 0.5)
    report: dict = {"judge": args.judge, "device": args.device}
    if not args.skip_detector:
        report["detector"] = detector_kpis(spec["detector"], args.device)
    videos = [video_kpis(video, args.judge, args.device, min_iou) for video in spec["videos"]]
    total = lambda key: {k: sum(v[key][k] for v in videos if v[key]) for k in ("tp", "fp", "fn")}
    report["interactions"] = {key: {**scores(total(key)), **timing_error([v[key] for v in videos if v[key]])}
                              for key in ("proximity_only", "with_judge")}
    tracked = [v["tracking"] for v in videos]
    minutes, counted = sum(t["minutes"] for t in tracked), [t for t in tracked if t["people"] is not None]
    report["tracking"] = {"role_flips_per_min": ratio(sum(t["role_flips_per_min"] * t["minutes"] for t in tracked), minutes),
                          "id_switches_per_min": ratio(sum(t["id_switches_per_min"] * t["minutes"] for t in counted),
                                                       sum(t["minutes"] for t in counted)) if counted else None}
    labelled_roles = [v["roles"] for v in videos if v["roles"]]
    if labelled_roles:
        tracks = sum(r["tracks"] for r in labelled_roles)
        report["roles"] = {**{role: scores({k: sum(r[role][k] for r in labelled_roles) for k in ("tp", "fp", "fn")})
                              for role in ("employee", "customer")},
                           "accuracy": ratio(sum(r["correct"] for r in labelled_roles), tracks),
                           "unknown_rate": ratio(sum(r["unknown"] for r in labelled_roles), tracks), "tracks": tracks}
    report["speed"] = {"realtime_factor": min(v["speed"]["realtime_factor"] for v in videos)}  # worst video
    report["videos"] = videos
    report["target_failures"] = check_targets(report, spec.get("targets", {}))
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    show = lambda v: "n/a" if v is None else f"{v:.3f}"
    if "detector" in report:
        d = report["detector"]
        print(f"detector {d['model']} on {d['images']} held-out images: mAP50 {show(d['map50'])}  mAP50-95 {show(d['map50_95'])}  "
              f"P {show(d['precision'])}  R {show(d['recall'])}  {show(d['inference_ms_per_image'])} ms/img")
        for name, c in d["classes"].items():
            print(f"  {name:9} P {show(c['precision'])}  R {show(c['recall'])}  mAP50 {show(c['map50'])}")
    labelled = sum(v["proximity_only"] is not None for v in videos)
    print(f"interaction accuracy from {labelled} of {len(videos)} videos (the rest are not labelled yet)")
    for name, s in report["interactions"].items():
        print(f"interactions {name:15} P {show(s['precision'])}  R {show(s['recall'])}  F1 {show(s['f1'])}  (tp {s['tp']} fp {s['fp']} fn {s['fn']})"
              f"  start err {show(s['start_error_s'])} s  end err {show(s['end_error_s'])} s")
    t = report["tracking"]
    print(f"tracking: ID switches {show(t['id_switches_per_min'])}/min (videos with a people count), role flips {show(t['role_flips_per_min'])}/min")
    if "roles" in report:
        r = report["roles"]
        print(f"roles on {r['tracks']} labelled tracks: accuracy {show(r['accuracy'])}  unknown {show(r['unknown_rate'])}  "
              f"employee P {show(r['employee']['precision'])} R {show(r['employee']['recall'])}  "
              f"customer P {show(r['customer']['precision'])} R {show(r['customer']['recall'])}")
    for v in videos:
        sp = v["speed"]
        print(f"speed {v['path']}: {sp['realtime_factor']:.2f}x realtime, frame p50 {show(sp['frame_ms_p50'])} ms "
              f"p95 {show(sp['frame_ms_p95'])} ms, judge {sp['judge_calls']} calls x {show(sp['judge_ms_mean'])} ms")
    print("targets: " + ("all met" if not report["target_failures"] else "; ".join(report["target_failures"])))


if __name__ == "__main__":
    main()
