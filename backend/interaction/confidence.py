"""95% confidence intervals for interaction precision, recall and F1 from a saved benchmark report.

Clip-level bootstrap: resample the report's videos with replacement, pool their tp/fp/fn, score, repeat.
Clips are the unit because interactions inside one clip are not independent.
A resample whose metric is undefined (no predictions for precision, no truth for recall, either for F1)
is left out of that metric's interval, the same "not measured" rule `benchmark.scores` uses; the count
left out is reported as `undefined`.

python -m backend.interaction.confidence backend/interaction/benchmarks/report_set_b_merged.json
"""

from __future__ import annotations

import json
import sys

import numpy as np

from .benchmark import scores

MODES = ("proximity_only", "with_judge")
METRICS = ("precision", "recall", "f1")


def confidence_intervals(report: dict, resamples: int = 10_000, seed: int = 0) -> dict:
    videos = report["videos"]
    picks = np.random.default_rng(seed).integers(0, len(videos), (resamples, len(videos)))
    result = {}
    for mode in MODES:
        counts = np.array([[v[mode][k] for k in ("tp", "fp", "fn")] for v in videos])
        point = scores(dict(zip(("tp", "fp", "fn"), counts.sum(axis=0).tolist())))
        boot = [scores(dict(zip(("tp", "fp", "fn"), row))) for row in counts[picks].sum(axis=1).tolist()]
        result[mode] = {"clips": len(videos), "tp": point["tp"], "fp": point["fp"], "fn": point["fn"]}
        for metric in METRICS:
            values = [s[metric] for s in boot if s[metric] is not None]
            interval = [float(x) for x in np.percentile(values, [2.5, 97.5])] if values else None
            result[mode][metric] = {"point": point[metric], "ci95": interval, "undefined": resamples - len(values)}
    return result


def main() -> None:
    with open(sys.argv[1]) as f:
        result = confidence_intervals(json.load(f))
    for mode, r in result.items():
        print(f"{mode}  ({r['clips']} clips, tp {r['tp']} fp {r['fp']} fn {r['fn']}; 10000 clip resamples, seed 0)")
        for metric in METRICS:
            m = r[metric]
            point = "n/a" if m["point"] is None else f"{m['point']:.3f}"
            interval = "n/a" if m["ci95"] is None else f"[{m['ci95'][0]:.3f}, {m['ci95'][1]:.3f}]"
            print(f"  {metric:<9} {point}  95% CI {interval}  (undefined resamples: {m['undefined']})")


if __name__ == "__main__":
    main()
