# Data Contracts

## What the pipeline writes today

`python -m backend.interaction.cli <video> --output backend/output/<run>/interaction.mp4`
writes these files next to the video:

| File | Shape |
|---|---|
| `interaction.detections.json` | `[{frame, timestamp, interaction_active, people: [{track_id, bbox:[x1,y1,x2,y2], center:[x,y], confidence, role, role_confidence, role_evidence}]}]` |
| `interaction.interactions.json` | confirmed events: `[{employee_track_id, customer_track_id, started_at, last_seen_at, start_time, verdict, ...}]` |
| `interaction.rejected_interactions.json` | same shape, events the pose judge rejected (only written with `--judge pose`) |
| `interaction.people.json` | `{weights, threshold, people: [{track_id, first_seen, last_seen, frames_observed, role, employee_score, factors, contributions, role_segments}]}` |

All coordinates are pixels of the source frame; times are seconds from the clip start.

## New: `interaction.summary.json` (Step 1)

Written by the CLI after the files above, computed by `backend/interaction/analytics.py`
from those same files only.

```json
{
  "run": "ShopAssistant1cor",
  "duration_s": 120.0,
  "footfall": {"in": 14, "out": 11},
  "people": {"customers": 17, "employees": 3},
  "interactions": {"count": 6, "mean_duration_s": 18.4, "mean_approach_s": 9.2},
  "unattended": [{"customer_track_id": 7, "from": 31.0, "to": 95.0, "waited_s": 64.0}],
  "employee_idle": [{"employee_track_id": 2, "idle_s": 40.5, "share": 0.34}],
  "zone_dwell": [{"zone": "staff_zone_0", "customer_s": 120.0, "employee_s": 310.0}],
  "heatmap": {"cols": 32, "rows": 18, "frame": [1280, 720], "counts": [[0, 1, 0]]}
}
```

Definitions:

- **footfall**: a track's `center` crossing the configured entrance line; direction from the sign change.
- **approach time**: customer `first_seen` → `started_at` of that customer's first confirmed interaction.
- **unattended**: a customer present longer than `unattended_after_s` with no confirmed interaction in that window.
- **employee idle**: employee time with no confirmed interaction and centre movement below `idle_move_px` over `idle_window_s`.
- **zone dwell**: seconds the track centres spend inside each zone rectangle (same frame-coordinate
  rectangles as `InteractionConfig.staff_zones`; store zones in SQLite have no geometry).
- **heatmap**: 2D histogram of all `center` points (`numpy.histogram2d`).

New config fields on `InteractionConfig` (defaults in brackets): `entrance_line` [None, footfall skipped],
`unattended_after_s` [60], `idle_window_s` [30], `idle_move_px` [40], `heatmap_grid` [(32, 18)].

## New API (Step 2)

`GET /analytics/runs` (manager): `[{"run": "<name>", "duration_s": ..., "created_at": ...}]`
from every `*.summary.json` under `backend/output/` (recorded runs go to `--output`, live runs to
`backend/output/live-<time>.*`). `run` is the path relative to `backend/output/` without `.summary.json`.

`GET /analytics/summary?run=<name>` (manager): that run's summary JSON; latest run when `run` is omitted.
404 when no summary exists. `run` must match an entry from `/analytics/runs` exactly (no path traversal).

Both are reached from the frontend through the existing `/api/backend/[...path]` proxy.

## New alerts (Step 3)

One row in the existing `alerts` table per unattended event:

| column | value |
|---|---|
| `category` | `unattended_customer` |
| `severity` | `high` if `waited_s` ≥ 2 × `unattended_after_s`, else `medium` |
| `title` | `Customer waited 64 s without assistance` |
| `context` | run name + time window |
| `source` | `vision` |
| `evidence_json` | the unattended entry plus the run name |
| `id` | `vision:<run>:<customer_track_id>:<from>` so re-importing a run does not duplicate alerts |
