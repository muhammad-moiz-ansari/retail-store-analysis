"""Turn one ingested real run into the two files the demo needs, so nothing is typed by hand (WP2).

python -m backend.prepare_demo --run-id RUN --manager-email you@example.com --video clip.mp4 --attest-fixed-derivation

Reads DATABASE_URL and the run's rows, then writes
- the analytics configuration the dashboard and `python -m backend.operations` read (it names the manager, so it goes to the
  ignored data/outputs/ folder by default; never commit it), and
- a run manifest (store, camera, run, zones, window, row counts, file hashes, commit) for docs/fyp2-plan/evidence/.

The configuration attests `synthetic: false`. Run this only against a database holding real footage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .database import connect
from .events.ingest import TABLES, validate

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ("zone_dwell", "interactions", "unattended_episodes")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def iso(stamp: datetime) -> str:
    return stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def describe_run(conn, run_id: str) -> dict:
    """Facts about one run read from the event store; raises SystemExit when the run cannot support a demo."""
    counts = {t: conn.execute(f"SELECT COUNT(*) AS n FROM {t} WHERE run_id = %s", (run_id,)).fetchone()["n"] for t in TABLES}
    if not counts["tracks"]:
        raise SystemExit(f"No tracks for run {run_id!r}. Ingest it first (python -m backend.interaction.cli ... --camera ...).")
    stores = [r["store_id"] for r in conn.execute("SELECT DISTINCT store_id FROM tracks WHERE run_id = %s", (run_id,))]
    cameras = [r["camera_id"] for r in conn.execute("SELECT DISTINCT camera_id FROM tracks WHERE run_id = %s ORDER BY 1", (run_id,))]
    if len(stores) != 1:
        raise SystemExit(f"Run {run_id!r} spans stores {stores}; the dashboard binds one store per manager.")
    zones = sorted({r["zone_id"] for t in ("tracks", "zone_dwell", "footfall") for r in conn.execute(f"SELECT DISTINCT zone_id FROM {t} WHERE run_id = %s", (run_id,))})
    home = conn.execute("SELECT zone_id, COUNT(*) AS n FROM pipeline_health WHERE run_id = %s GROUP BY zone_id ORDER BY n DESC, zone_id LIMIT 1", (run_id,)).fetchone()
    span = conn.execute("SELECT MIN(ts_start) AS first, MAX(ts_end) AS last FROM tracks WHERE run_id = %s", (run_id,)).fetchone()
    return {"store_id": stores[0], "camera_ids": cameras, "zone_ids": zones, "home_zone": home["zone_id"] if home else zones[0],
            "start": span["first"], "end": span["last"], "counts": counts}


def build_config(run: dict, run_id: str, manager_id: str, *, footfall_validated: bool, attest_fixed_derivation: bool) -> dict:
    window = {"start": iso(run["start"]), "end": iso(run["end"])}
    sources = [*DEFAULT_SOURCES, *(["footfall"] if footfall_validated else [])]
    config = {
        "version": 1,
        "synthetic": False,
        "memberships": [{
            "user_id": manager_id, "store_id": run["store_id"], "run_ids": [run_id],
            "camera_ids": run["camera_ids"], "zone_ids": run["zone_ids"],
            "default_request": {"storeId": run["store_id"], "window": window,
                                "filters": {"runId": run_id, "zoneId": run["home_zone"]}},
        }],
        # One context per zone, over the clip itself: the window is the footage that exists, not a store's opening hours.
        "contexts": [{"context_id": f"{run_id}-{zone}", "store_id": run["store_id"], "zone_id": zone,
                      "camera_ids": run["camera_ids"], "available_sources": sources, "operating_windows": [window]}
                     for zone in run["zone_ids"]],
    }
    if attest_fixed_derivation:
        config["verified_unattended_runs"] = [{"store_id": run["store_id"], "camera_id": c, "run_id": run_id} for c in run["camera_ids"]]
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the analytics configuration and run manifest for one ingested real run.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--manager-email", required=True, help="Email of an existing active Manager account")
    parser.add_argument("--video", type=Path, help="The clip that was analysed (hashed into the manifest)")
    parser.add_argument("--camera-config", type=Path, help="The camera --config JSON used for the run (hashed)")
    parser.add_argument("--weights", type=Path, nargs="*", default=[], help="Model and role-weight files used (hashed)")
    parser.add_argument("--footfall-validated", action="store_true", help="Declare the footfall feed available (only after the labelled-clip check)")
    parser.add_argument("--attest-fixed-derivation", action="store_true",
                        help="Attest the run was ingested after the unattended-verdict fix (any run ingested from this branch was)")
    parser.add_argument("--config-out", type=Path)
    parser.add_argument("--manifest-out", type=Path)
    args = parser.parse_args()

    from .agents.dashboard import DashboardConfig  # validates the file exactly as the backend will

    with connect() as conn:
        manager = conn.execute("SELECT id FROM users WHERE lower(email) = lower(%s) AND role = 'Manager' AND active = 1",
                               (args.manager_email,)).fetchone()
        if not manager:
            raise SystemExit(f"No active Manager account for {args.manager_email}. Create it with python -m backend.database --bootstrap-manager.")
        run = describe_run(conn, args.run_id)
        problems = validate(conn)
    config = build_config(run, args.run_id, manager["id"], footfall_validated=args.footfall_validated,
                          attest_fixed_derivation=args.attest_fixed_derivation)
    DashboardConfig.model_validate(config)

    config_out = args.config_out or ROOT / "data" / "outputs" / f"analytics_config_{args.run_id}.json"
    manifest_out = args.manifest_out or ROOT / "docs" / "fyp2-plan" / "evidence" / f"run_{args.run_id}.json"
    for path in (config_out, manifest_out):
        path.parent.mkdir(parents=True, exist_ok=True)
    config_out.write_text(json.dumps(config, indent=2), encoding="utf-8")

    hashed = {str(p): sha256(p) for p in [args.video, args.camera_config, *args.weights] if p}
    manifest = {
        "run_id": args.run_id, "store_id": run["store_id"], "camera_ids": run["camera_ids"], "zone_ids": run["zone_ids"],
        "window": {"start": iso(run["start"]), "end": iso(run["end"])}, "row_counts": run["counts"],
        "schema_violations": problems, "synthetic": False,
        "feeds_declared": config["contexts"][0]["available_sources"] if config["contexts"] else [],
        "file_sha256": hashed, "commit": git("rev-parse", "HEAD"), "working_tree_clean": git("status", "--porcelain") == "",
        "python": platform.python_version(), "prepared_at": iso(datetime.now(timezone.utc)),
        "source": "real footage: state who recorded it, where, and that its use was approved",
    }
    manifest_out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"configuration (ignored by Git, names the manager): {config_out}")
    print(f"manifest (commit this):                            {manifest_out}")
    print("row counts:", json.dumps(run["counts"]))
    if problems:
        print("SCHEMA VIOLATIONS:\n" + "\n".join(problems), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
