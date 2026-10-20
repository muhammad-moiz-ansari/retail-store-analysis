"""KPI maths used by the benchmark."""

from .benchmark import check_targets, interval_iou, match_events, scores


def test_interval_iou() -> None:
    assert interval_iou((0, 10), (5, 15)) == 5 / 15
    assert interval_iou((0, 1), (2, 3)) == 0


def test_events_match_one_to_one_by_temporal_iou() -> None:
    truth = [(35.0, 44.0)]
    predicted = [(1.2, 15.5), (35.4, 43.9), (36.0, 43.0)]  # walk-by, the real one, a duplicate
    counts = match_events(predicted, truth, 0.5)
    assert (counts["tp"], counts["fp"], counts["fn"]) == (1, 2, 0)
    assert round(counts["start_error_s"], 2) == 0.4 and round(counts["end_error_s"], 2) == 0.1


def test_scores_and_targets() -> None:
    s = scores({"tp": 1, "fp": 1, "fn": 0})
    assert (s["precision"], s["recall"], round(s["f1"], 3)) == (0.5, 1.0, 0.667)
    assert scores({"tp": 0, "fp": 0, "fn": 0})["precision"] is None  # nothing predicted: not measured, not 0
    report = {"interactions": {"with_judge": s}}
    assert check_targets(report, {"interactions.with_judge.precision": 0.9, "detector.map50": 0.8}) == [
        "interactions.with_judge.precision: 0.500 < 0.9", "detector.map50: not measured"]
