"""Score a camera_handoff.py run against labelled crossings (B5).

Labels JSON (track IDs from a reviewed run with the same settings):
{"crossings": [{"source_track_id": 3, "target_track_id": 7}, ...]}
Every cam1 exit not listed is a person who never reached cam2.

python -m backend.handoff_eval backend/output/camera_handoff.json labels.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def evaluate(handoffs: list[dict[str, Any]], crossings: list[dict[str, Any]]) -> dict[str, Any]:
    """Status rates over cam1 exits, and how right the confirmed (auto-merged) and uncertain pairs are.
    A wrong confirmed pair merges two people into one master_id, the costly error."""
    truth = {(c["source_track_id"], c["target_track_id"]) for c in crossings}
    exits = [h for h in handoffs if h["source_event_id"] is not None]
    by_status = {s: [h for h in exits if h["status"] == s] for s in ("confirmed", "uncertain", "unmatched")}
    correct = lambda hs: sum((h["source_track_id"], h["target_track_id"]) in truth for h in hs)
    ratio = lambda a, b: a / b if b else None
    return {
        "exits": len(exits), "labelled_crossings": len(truth),
        "rates": {s: ratio(len(hs), len(exits)) for s, hs in by_status.items()},
        "confirmed_precision": ratio(correct(by_status["confirmed"]), len(by_status["confirmed"])),
        "confirmed_recall": ratio(correct(by_status["confirmed"]), len(truth)),
        "wrong_merges": len(by_status["confirmed"]) - correct(by_status["confirmed"]),
        "uncertain_correct": ratio(correct(by_status["uncertain"]), len(by_status["uncertain"])),
        "missed_crossings": len(truth) - correct(by_status["confirmed"]) - correct(by_status["uncertain"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate camera handoff against labelled crossings.")
    parser.add_argument("run", type=Path, help="camera_handoff.json from camera_handoff.py")
    parser.add_argument("labels", type=Path)
    args = parser.parse_args()
    run = json.loads(args.run.read_text(encoding="utf-8"))
    report = evaluate(run["handoffs"], json.loads(args.labels.read_text(encoding="utf-8"))["crossings"])
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
