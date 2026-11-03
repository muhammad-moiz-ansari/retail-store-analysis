"""Role-weight refit: leave-one-clip-out logistic regression mapped back onto the agent's weights."""

import json

import numpy as np

from .refit import as_agent, evaluate, fit, load_clips


def clip(rnd, n=20):
    factors, labels = [], []
    for i in range(n):
        employee = i % 4 == 0
        factors.append({"yolo": rnd.uniform(0.3, 0.9) * (1 if employee else -1) if rnd.random() > 0.2 else rnd.uniform(-0.5, 0.5),
                        "bib_colour": rnd.uniform(0.4, 1.0) if employee else rnd.uniform(0.0, 0.3),
                        "staff_zone": rnd.random(), "stationary": rnd.random(), "reference": None})
        labels.append(int(employee))
    return {"name": "clip", "factors": factors, "labels": labels}


def test_fit_separates_and_maps_onto_the_agent_rule() -> None:
    import random

    rnd = random.Random(1)
    clips = [clip(rnd) for _ in range(3)]
    x = np.array([[f.get(k) or 0.0 for k in ("reference", "yolo", "bib_colour", "staff_zone", "stationary")] for f in clips[0]["factors"]])
    w, b = fit(x, np.array(clips[0]["labels"]))
    weights, threshold = as_agent(w, b)
    agent_says = [sum(weights[k] * (f.get(k) or 0.0) for k in weights) >= threshold for f in clips[0]["factors"]]
    assert agent_says == list(x @ w + b >= 0)
    assert weights["bib_colour"] > abs(weights["staff_zone"]) and weights["reference"] == 0  # never seen, L2 keeps it at 0
    report = evaluate(clips)
    assert report["clips"] == 3 and report["fitted"]["tracks"] == 60
    assert report["fitted"]["accuracy"] >= 0.9


def test_load_clips_reads_labelled_runs_only(tmp_path, monkeypatch) -> None:
    from . import refit

    people = tmp_path / "a.people.json"
    people.write_text(json.dumps({"people": [{"track_id": 1, "factors": {"yolo": 0.8}}, {"track_id": 2, "factors": {"yolo": -0.5}}]}))
    monkeypatch.setattr(refit, "ROOT", tmp_path)
    spec = {"videos": [{"path": "a.mp4", "people_file": "a.people.json", "roles": {"1": "employee", "2": "unknown", "7": "customer"}},
                       {"path": "b.mp4"}]}
    assert load_clips(spec) == [{"name": "a.mp4", "factors": [{"yolo": 0.8}], "labels": [1]}]
