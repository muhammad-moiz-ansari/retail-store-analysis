"""Teach a camera its store's staff appearance from a few labelled tracks; no retraining.

Run the CLI once, look at the annotated video, then name a few employee and customer track IDs:
python -m backend.interaction.calibrate out.people.json --employee 3 7 --customer 1 2 --config store-cam1.json
and pass `--config store-cam1.json` to later runs. Repeat with other runs to add references (several uniforms,
lighting); at least two per role is advisable. Other settings already in the config file are kept.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def add_references(config: dict, people: list[dict], labels: dict[str, list[int]]) -> dict:
    """Return `config` with each labelled track's appearance appended to role_references."""
    by_id = {person["track_id"]: person for person in people}
    references = {role: list(vectors) for role, vectors in config.get("role_references", {}).items()}
    for role, track_ids in labels.items():
        for track_id in track_ids:
            appearance = by_id.get(track_id, {}).get("appearance")
            if not appearance:
                raise SystemExit(f"track {track_id} is not in the people file or has no appearance (re-run the CLI)")
            references.setdefault(role, []).append(appearance)
    return {**config, "role_references": references}


def main() -> None:
    parser = argparse.ArgumentParser(description="Add labelled tracks as few-shot role references to a camera config.")
    parser.add_argument("people", type=Path, help="<output>.people.json from a CLI run on this camera")
    parser.add_argument("--employee", type=int, nargs="*", default=[], help="Track IDs that are staff")
    parser.add_argument("--customer", type=int, nargs="*", default=[], help="Track IDs that are customers")
    parser.add_argument("--config", type=Path, required=True, help="Camera config JSON to create or extend")
    args = parser.parse_args()
    if not args.employee and not args.customer:
        parser.error("label at least one track with --employee or --customer")
    people = json.loads(args.people.read_text(encoding="utf-8"))["people"]
    config = json.loads(args.config.read_text(encoding="utf-8")) if args.config.exists() else {}
    config = add_references(config, people, {"employee": args.employee, "customer": args.customer})
    args.config.write_text(json.dumps(config, indent=2), encoding="utf-8")
    counts = {role: len(config["role_references"].get(role, [])) for role in ("employee", "customer")}
    print(f"{args.config}: {counts['employee']} employee and {counts['customer']} customer references"
          + ("" if all(counts.values()) else " (the reference factor stays off until both roles have one)"))


if __name__ == "__main__":
    main()
