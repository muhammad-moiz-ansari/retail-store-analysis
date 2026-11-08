"""Refit the role agent's hand-set weights on labelled tracks, validated by leave-one-clip-out (B3).

Each benchmark video with reviewed `"roles": {"<track_id>": "employee" | "customer"}` also names the CLI run those
IDs came from: `"people_file": "backend/output/<run>.people.json"`. The per-track mean factors there are the features.

python -m backend.interaction.refit backend/interaction/benchmarks/benchmark.json --output backend/interaction/benchmarks/refit
writes refit.json (hand-set vs fitted on held-out clips, the fitted weights as a --config snippet) and sweep.png.

A logistic regression's boundary w.x + b = 0 is the agent's own rule after scaling by s = sum|w|:
employee when sum((w/s) * x) >= -b/s, so the fit maps straight back onto role_weights and the threshold.
A missing factor counts as 0 in the fit, whereas the agent hands a missing appearance factor's weight on, so the
fitted config holds for cameras with the same factors present as the labelled clips (all calibrated, or none).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .cust_emp_classifier import DEFAULT_WEIGHTS, CustEmpClassifier

ROOT = Path(__file__).resolve().parents[2]
FACTORS = list(DEFAULT_WEIGHTS)


def load_clips(spec: dict) -> list[dict]:
    """[{name, factors: [per-track factor dicts], labels: [1 employee / 0 customer]}] for each labelled video."""
    clips = []
    for video in spec["videos"]:
        if not video.get("roles") or not video.get("people_file"):
            continue
        people = {p["track_id"]: p for p in json.loads((ROOT / video["people_file"]).read_text(encoding="utf-8"))["people"]}
        rows = [(people[int(t)]["factors"], int(role == "employee")) for t, role in video["roles"].items()
                if role in ("employee", "customer") and int(t) in people]
        clips.append({"name": video["path"], "factors": [r[0] for r in rows], "labels": [r[1] for r in rows]})
    return clips


def features(factors: list[dict]) -> np.ndarray:
    return np.array([[f.get(name) or 0.0 for name in FACTORS] for f in factors], dtype=float)


def fit(x: np.ndarray, y: np.ndarray, l2: float = 0.01, steps: int = 3000, rate: float = 0.5) -> tuple[np.ndarray, float]:
    """Plain L2 logistic regression by gradient descent; classes reweighted so a few employees still count."""
    w, b = np.zeros(x.shape[1]), 0.0
    balance = np.where(y == 1, len(y) / (2 * max(y.sum(), 1)), len(y) / (2 * max(len(y) - y.sum(), 1)))
    for _ in range(steps):
        error = balance * (1 / (1 + np.exp(-(x @ w + b))) - y)
        w -= rate * (x.T @ error / len(y) + l2 * w)
        b -= rate * error.mean()
    return w, b


def as_agent(w: np.ndarray, b: float) -> tuple[dict[str, float], float]:
    """The fit as the agent's role_weights and employee_score_threshold."""
    scale = np.abs(w).sum() or 1.0
    return {name: round(float(v / scale), 4) for name, v in zip(FACTORS, w)}, round(float(-b / scale), 4)


def metrics(predicted: list[int], truth: list[int]) -> dict:
    tp = sum(p == t == 1 for p, t in zip(predicted, truth))
    fp = sum(p == 1 != t for p, t in zip(predicted, truth))
    fn = sum(t == 1 != p for p, t in zip(predicted, truth))
    return {"tracks": len(truth), "accuracy": sum(p == t for p, t in zip(predicted, truth)) / len(truth) if truth else None,
            "employee_precision": tp / (tp + fp) if tp + fp else None, "employee_recall": tp / (tp + fn) if tp + fn else None}


def evaluate(clips: list[dict]) -> dict:
    """Hand-set agent vs a fit on every other clip, scored on each held-out clip."""
    agent = CustEmpClassifier()
    hand, fitted, truth = [], [], []
    for held_out in clips:
        train = [c for c in clips if c is not held_out]
        w, b = fit(features([f for c in train for f in c["factors"]]), np.array([y for c in train for y in c["labels"]]))
        weights, threshold = as_agent(w, b)
        hand += [agent.decide(f)[1] for f in held_out["factors"]]
        # Shifted so the fitted threshold sits at the agent's, which puts both curves on one sweep axis.
        fitted += [sum(weights[n] * (f.get(n) or 0.0) for n in FACTORS) - threshold + agent.threshold for f in held_out["factors"]]
        truth += held_out["labels"]
    weights, threshold = as_agent(*fit(features([f for c in clips for f in c["factors"]]), np.array([y for c in clips for y in c["labels"]])))
    return {"clips": len(clips), "hand_set": {**metrics([int(s >= agent.threshold) for s in hand], truth),
                                              "weights": agent.weights, "threshold": agent.threshold},
            "fitted": {**metrics([int(s >= agent.threshold) for s in fitted], truth),
                       "config": {"role_weights": weights, "employee_score_threshold": threshold}},
            "scores": {"hand_set": hand, "fitted": fitted, "truth": truth}}


def sweep(scores: list[float], truth: list[int], thresholds: np.ndarray) -> tuple[list, list]:
    precision, recall = [], []
    for t in thresholds:
        m = metrics([int(s >= t) for s in scores], truth)
        precision.append(m["employee_precision"]), recall.append(m["employee_recall"])
    return precision, recall


def main() -> None:
    parser = argparse.ArgumentParser(description="Refit role weights on labelled tracks (leave-one-clip-out).")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output", type=Path, default=Path("refit"))
    args = parser.parse_args()
    clips = load_clips(json.loads(args.spec.read_text(encoding="utf-8")))
    if len(clips) < 2 or not any(y for c in clips for y in c["labels"]):
        raise SystemExit(f"need >= 2 clips with \"roles\" and \"people_file\" and at least one employee (found {len(clips)} clips)")
    report = evaluate(clips)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "refit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    thresholds = np.linspace(0, 1, 41)
    for name, style in (("hand_set", "-"), ("fitted", "--")):
        precision, recall = sweep(report["scores"][name], report["scores"]["truth"], thresholds)
        plt.plot(thresholds, [np.nan if p is None else p for p in precision], style, label=f"{name} precision")
        plt.plot(thresholds, [np.nan if r is None else r for r in recall], style, label=f"{name} recall")
    plt.axvline(0.45, color="grey", linewidth=0.8)
    plt.xlabel("employee score threshold (held-out clips)"), plt.ylabel("employee precision / recall"), plt.legend()
    plt.savefig(args.output / "sweep.png", dpi=150, bbox_inches="tight")

    show = lambda v: "n/a" if v is None else f"{v:.3f}"
    for name in ("hand_set", "fitted"):
        m = report[name]
        print(f"{name:9} on {m['tracks']} held-out tracks: accuracy {show(m['accuracy'])}  "
              f"employee P {show(m['employee_precision'])} R {show(m['employee_recall'])}")
    print(f"fitted config (all clips): {json.dumps(report['fitted']['config'])}")
    print(f"wrote {args.output / 'refit.json'} and {args.output / 'sweep.png'}")


if __name__ == "__main__":
    main()
