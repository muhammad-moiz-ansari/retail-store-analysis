import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.floor_calibration import calibrate

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Fit a provisional floor homography from explicit landmarks")
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--timestamp", type=float, default=0)
    p.add_argument("--landmarks", type=Path, required=True, help="Editable JSON config with floor coordinates or rectangle measurements")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--headless", action="store_true", help="Use saved image points instead of clicking")
    try:
        calibrate(p.parse_args())
    except (ValueError, KeyError, RuntimeError, OSError) as exc:
        p.exit(1, f"Error: {exc}\n")
