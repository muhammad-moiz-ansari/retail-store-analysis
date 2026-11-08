"""Handoff evaluation against labelled crossings."""

from .handoff_eval import evaluate


def test_handoff_rates_precision_and_wrong_merges() -> None:
    pair = lambda status, s, t: {"status": status, "source_event_id": f"e{s}", "source_track_id": s, "target_track_id": t}
    handoffs = [pair("confirmed", 1, 11), pair("confirmed", 2, 13),  # right, then a wrong merge
                pair("uncertain", 3, 12), pair("unmatched", 4, None),
                {"status": "unmatched", "source_event_id": None, "source_track_id": None, "target_track_id": 14}]  # cam2-only entry
    report = evaluate(handoffs, [{"source_track_id": 1, "target_track_id": 11}, {"source_track_id": 2, "target_track_id": 12},
                                 {"source_track_id": 3, "target_track_id": 12}])
    assert report["exits"] == 4 and report["rates"] == {"confirmed": 0.5, "uncertain": 0.25, "unmatched": 0.25}
    assert (report["confirmed_precision"], report["wrong_merges"], report["uncertain_correct"]) == (0.5, 1, 1.0)
    assert round(report["confirmed_recall"], 3) == 0.333 and report["missed_crossings"] == 1
