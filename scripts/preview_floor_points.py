"""Run from the repository root with the existing .venv Python."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.floor_video import common_parser, preview

if __name__ == "__main__":
    parser = common_parser("Preview trained person detections and box-bottom points without calibration")
    try:
        preview(parser.parse_args())
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")
