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


def test_role_counts_treat_unknown_as_a_miss() -> None:
    from .benchmark import role_counts

    counts = role_counts({1: "employee", 2: "customer", 3: "unknown", 4: "employee"},
                         {"1": "employee", "2": "employee", "3": "customer", "4": "customer", "9": "customer"})
    assert counts["employee"] == {"tp": 1, "fp": 1, "fn": 1}
    assert counts["customer"] == {"tp": 0, "fp": 1, "fn": 3}  # 3 unknown, 4 wrong, 9 never seen
    assert (counts["tracks"], counts["correct"], counts["unknown"]) == (5, 1, 1)


def test_timing_error_and_tracking_kpis() -> None:
    from .benchmark import timing_error, tracking_kpis

    matches = [{"tp": 1, "start_error_s": 1.0, "end_error_s": 0.0}, {"tp": 3, "start_error_s": 3.0, "end_error_s": 2.0},
               {"tp": 0, "start_error_s": None, "end_error_s": None}]
    assert timing_error(matches) == {"start_error_s": 2.5, "end_error_s": 1.5}
    kpis = tracking_kpis({1: ["customer", "employee", "employee"], 2: ["customer"], 3: ["employee", "customer", "employee"]}, 2.0, 2)
    assert (kpis["role_flips_per_min"], kpis["id_switches_per_min"]) == (1.5, 0.5)
    assert tracking_kpis({}, 1.0, None)["id_switches_per_min"] is None


def test_per_second_overlap() -> None:
    from pytest import approx

    from .benchmark import event_kpis, overlap_seconds, second_scores

    exact = second_scores(overlap_seconds([(10.0, 20.0)], [(10.0, 20.0)]))
    assert (exact["precision"], exact["recall"], exact["f1"]) == (1.0, 1.0, 1.0)
    # One long prediction over two short labels: strict matching misses both, per second credits the overlap.
    long = event_kpis([(0.0, 30.0)], [(2.0, 8.0), (20.0, 26.0)], 0.5)
    assert (long["tp"], long["fp"], long["fn"]) == (0, 1, 2)
    assert long["per_second"]["overlap_s"] == 12.0 and long["per_second"]["precision"] == approx(0.4)
    assert long["per_second"]["recall"] == 1.0
    # Overlapping predictions are unioned, not double counted.
    assert overlap_seconds([(0.0, 10.0), (5.0, 15.0), (14.0, 16.0)], [(0.0, 20.0)]) == {
        "overlap_s": 16.0, "predicted_s": 16.0, "labelled_s": 20.0}
    none = second_scores(overlap_seconds([], [(0.0, 5.0)]))
    assert (none["precision"], none["recall"], none["f1"]) == (None, 0.0, None)
    unlabelled = second_scores(overlap_seconds([(0.0, 5.0)], []))
    assert (unlabelled["precision"], unlabelled["recall"], unlabelled["f1"]) == (0.0, None, None)
