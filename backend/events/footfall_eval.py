"""Score directional footfall against hand labels (S-B4-REALFEED validation).

python -m backend.events.footfall_eval --run-id RUN --labels labels.csv --start 2026-11-15T10:00:00+00:00 [--out report.json]

labels.csv: `seconds,direction` per line (seconds from the first frame of the clip, direction in|out), optional header.
A label and a recorded crossing match when the direction is equal and the times are within `tolerance_s`; each side is used once.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

DIRECTIONS = ("in", "out")


def load_labels(path: Path) -> list[tuple[float, str]]:
    labels = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if not row or row[0].strip().lower() == "seconds":
                continue
            seconds, direction = float(row[0]), row[1].strip().lower()
            if direction not in DIRECTIONS or seconds < 0:
                raise ValueError(f"Bad label row {row!r}: need nonnegative seconds and in|out")
            labels.append((seconds, direction))
    return labels


def match(labels: list[tuple[float, str]], recorded: list[tuple[float, str]], tolerance_s: float = 1.0) -> dict:
    """Greedy one-to-one matching in time order, per direction. Precision = matched / recorded, recall = matched / labelled."""
    report: dict = {"tolerance_s": tolerance_s}
    for direction in DIRECTIONS:
        truth = sorted(t for t, d in labels if d == direction)
        seen = sorted(t for t, d in recorded if d == direction)
        used, matched = set(), 0
        for t in truth:
            best = min((i for i in range(len(seen)) if i not in used and abs(seen[i] - t) <= tolerance_s),
                       key=lambda i: abs(seen[i] - t), default=None)
            if best is not None:
                used.add(best)
                matched += 1
        report[direction] = {"labelled": len(truth), "recorded": len(seen), "matched": matched,
                             "missed": len(truth) - matched, "extra": len(seen) - matched,
                             "precision": matched / len(seen) if seen else None,
                             "recall": matched / len(truth) if truth else None}
    return report


def recorded_crossings(conn, run_id: str, start: datetime) -> list[tuple[float, str]]:
    rows = conn.execute("SELECT ts_start, direction FROM footfall WHERE run_id = %s ORDER BY ts_start", (run_id,)).fetchall()
    return [((row["ts_start"] - start).total_seconds(), row["direction"]) for row in rows]


def main() -> None:
    from ..database import connect

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--start", type=datetime.fromisoformat, required=True, help="The --start given to the CV CLI (UTC time of the first frame)")
    parser.add_argument("--tolerance", type=float, default=1.0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.start.tzinfo is None:
        parser.error("--start needs a UTC offset")
    with connect() as conn:
        recorded = recorded_crossings(conn, args.run_id, args.start)
    report = {"run_id": args.run_id, **match(load_labels(args.labels), recorded, args.tolerance)}
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
