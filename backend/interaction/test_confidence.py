"""Clip-level bootstrap intervals for interaction P/R/F1."""

from .benchmark import scores
from .confidence import confidence_intervals


def _report(*clips):
    """Each clip is (tp, fp, fn), used for both modes."""
    videos = [{m: {"tp": tp, "fp": fp, "fn": fn} for m in ("proximity_only", "with_judge")} for tp, fp, fn in clips]
    return {"videos": videos}


def test_point_matches_pooled_and_interval_contains_it() -> None:
    clips = [(2, 1, 0), (0, 2, 3), (1, 0, 1), (3, 1, 0), (0, 1, 1)]
    pooled = scores({"tp": 6, "fp": 5, "fn": 5})
    result = confidence_intervals(_report(*clips))
    for mode in ("proximity_only", "with_judge"):
        for metric in ("precision", "recall", "f1"):
            m = result[mode][metric]
            assert m["point"] == pooled[metric]
            assert m["ci95"][0] <= m["point"] <= m["ci95"][1] and m["ci95"][0] < m["ci95"][1]


def test_fixed_seed_is_reproducible() -> None:
    report = _report((2, 1, 0), (0, 2, 3), (1, 0, 1))
    assert confidence_intervals(report, seed=7) == confidence_intervals(report, seed=7)


def test_perfect_clips_give_exactly_one() -> None:
    result = confidence_intervals(_report((2, 0, 0), (1, 0, 0), (4, 0, 0)), resamples=500)
    for metric in ("precision", "recall", "f1"):
        assert result["with_judge"][metric]["ci95"] == [1.0, 1.0]


def test_undefined_resamples_are_left_out_and_counted() -> None:
    # Clip 2 predicts nothing: a resample of only clip 2 has no precision (and so no F1), but recall 0.
    result = confidence_intervals(_report((1, 1, 0), (0, 0, 1)), resamples=2000)["with_judge"]
    assert 0 < result["precision"]["undefined"] < 2000 and result["f1"]["undefined"] == result["precision"]["undefined"]
    assert result["recall"]["undefined"] == 0 and result["recall"]["ci95"][0] == 0.0
    # Nothing predicted anywhere: precision is never measured, and says so instead of reporting 0.
    none = confidence_intervals(_report((0, 0, 2), (0, 0, 1)), resamples=100)["with_judge"]
    assert none["precision"] == {"point": None, "ci95": None, "undefined": 100}
