import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.floor_video import common_parser, ROOT
from backend.floor_demo import run

if __name__ == "__main__":
    p = common_parser("Local provisional floor-distance demo using the trained role detector")
    p.set_defaults(output_dir=ROOT / "data/outputs/distance/demo")
    p.add_argument("--calibration", type=Path, required=True)
    p.add_argument("--motion-mode", choices=["monitor", "fixed", "snapshot"], default="monitor",
                   help="fixed and monitor both suppress unverified/shifted geometry; snapshot supports reference only")
    p.add_argument("--pair", nargs=2, type=int, metavar=("TRACK_A", "TRACK_B"))
    p.add_argument("--pixels-per-metre", type=float, default=200)
    try:
        args = p.parse_args()
        if args.pair and args.pair[0] == args.pair[1]:
            p.error("Select two distinct track IDs")
        run(args)
    except (ValueError, KeyError, RuntimeError, OSError) as exc:
        p.exit(1, f"Error: {exc}\n")
