import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.floor_evaluation import evaluate, metrics_coverage

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Evaluate independent floor points and known separations, or metric coverage")
    p.add_argument("--calibration", type=Path)
    p.add_argument("--annotations", type=Path)
    p.add_argument("--metrics", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if bool(args.calibration) != bool(args.annotations) or not (args.metrics or args.annotations):
        p.error("Supply --metrics and/or both --calibration and --annotations")
    try:
        result = {}
        if args.annotations:
            result["accuracy"] = evaluate(json.loads(args.calibration.read_text(encoding="utf-8")), json.loads(args.annotations.read_text(encoding="utf-8")))
        if args.metrics:
            result["runtime_coverage"] = metrics_coverage(args.metrics)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps(result))
    except (ValueError, KeyError, OSError) as exc:
        p.exit(1, f"Error: {exc}\n")
