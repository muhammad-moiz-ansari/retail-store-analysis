"""Dataset inventory and leakage checks. Unknown provenance is never guessed."""

from pathlib import Path

from .models import fingerprint

USES = {"train": ["training"], "calibration": ["prototypes"],
        "development": ["thresholds", "model_selection"], "held_out": ["frozen_evaluation"],
        "unassigned": []}


def inventory(root):
    import av
    records = []
    for path in sorted(Path(root).rglob("*")):
        if path.suffix.lower() not in {".mp4", ".avi", ".mov", ".mkv"}:
            continue
        record = {"source_id": fingerprint(path), "path": str(path), "split": "unassigned",
                  "camera_id": None, "recording_day": None, "leakage_group": None,
                  "utc_anchor": None, "utc_anchor_provenance": None, "annotation_version": None,
                  "conditions": [], "permitted_uses": [], "pts_validation": "pending",
                  "derived_media": any(word in path.stem.lower() for word in ("tracked", "annotated"))}
        try:
            with av.open(str(path)) as container:
                stream = container.streams.video[0]
                record["media"] = {"width": stream.width, "height": stream.height,
                    "codec": stream.codec_context.name, "frames": stream.frames,
                    "duration_seconds": float(stream.duration * stream.time_base) if stream.duration else None}
        except Exception as exc:
            record["error"] = type(exc).__name__
        records.append(record)
    return {"schema_version": 1, "dataset_version": "inventory-v1", "evaluation_scope": "existing_calibrated_cameras",
            "status": "provenance_and_annotations_required", "sources": records}


def validate_manifest(manifest, required_splits=()):
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported dataset schema")
    groups, sources, camera_days, splits = {}, {}, {}, set()
    for source in manifest["sources"]:
        split = source["split"]
        if split not in USES or source["permitted_uses"] != USES[split]:
            raise ValueError("Split permitted uses mismatch")
        if split == "unassigned":
            continue
        if source.get("derived_media") or source.get("error"):
            raise ValueError("Derived or unreadable media cannot enter a release dataset")
        for key in ("camera_id", "recording_day", "leakage_group", "annotation_version"):
            if not source.get(key):
                raise ValueError(f"Assigned sources require {key}")
        for registry, key in ((groups, source["leakage_group"]), (sources, source["source_id"]),
                              (camera_days, (source["camera_id"], source["recording_day"]))):
            if key in registry and registry[key] != split:
                raise ValueError("Recording/day/content leakage across splits")
            registry[key] = split
        splits.add(split)
    if not set(required_splits).issubset(splits):
        raise ValueError("Required dataset splits are missing")
    return manifest
