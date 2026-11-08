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

## Event schema v1 (shared contract 1)

`backend/events/schema.sql`: eight tables (`tracks`, `role_decisions`, `interactions`, `zone_dwell`, `footfall`,
`queue_samples`, `unattended_episodes`, `pipeline_health`). Every row has `event_id` (stable, `<run>:<kind>:<camera>:<key>`),
`run_id`, `store_id`, `camera_id`, `zone_id`, `ts_start`, `ts_end` (UTC ISO 8601; instants have `ts_end = ts_start`).
Zone and camera ids are the ones seeded in `store_core.py` (`z1`–`z6`, `c1`–`c3`). Indexed on `(store_id, zone_id, ts_start)`.

- **Ingest a CV run** (idempotent on `run_id`):
  `python -m backend.events.ingest backend/output/run1/interaction --run-id run1 --camera c2 --zone z2 --start 2026-11-03T09:00:00+00:00`
  (default DB `backend/events.sqlite3`, or `EVENTS_DB_PATH`).
- **Straight from the CLI**: add `--camera c2` (zone from the camera settings, or `--zone`), optionally `--start <UTC ISO>`
  (default: when processing starts, which is right for live runs) and `--run-id`. `POST /interaction/runs` and
  `POST /interaction/live` take an optional `"camera": "c2"` and pass it on.
- **unattended_episodes** is derived, not detected: a customer whose wait from first sighting to their first confirmed
  interaction (or exit) is ≥ N s, N = settings `thresholds.unattendedWaitMinutes` × 60. `helped` says which ended it.
- **Fixture day** for tools/agents/UI: `python -m backend.events.fixtures` → `backend/events/fixture.sqlite3`
  (seeded, identical every run; not committed since `*.sqlite3` is ignored). 09:00–21:00 UTC, planted patterns:
  17:00–19:00 rush, understaffed `z3`, camera `c2` blocked 14:00–14:40 (`pipeline_health.frozen_or_dark = 1`).
- **Zones and dwell (B4.2)**: the camera's `--config` JSON may hold `floor_zones` (normalised polygons keyed by store
  `zone_id`), `zone_hold_seconds` (1.0) and `heatmap_grid` ([32, 18]). A track's foot point picks its zone (outside every
  polygon = the camera's zone); `zone_dwell` has one row per visit, ordered visits of a track are its zone transitions,
  `tracks.zone_id` is the zone it spent longest in and `interactions.zone_id` is the customer's zone at the start.
- **heatmaps** (additive to v1): one row per camera per wall-clock hour, `cells` = JSON `rows` x `cols` foot-point counts.
- **footfall (B4.3)**: entrance camera config sets `entrance_line` (normalised x of a vertical line) and
  `entrance_in_direction` ("right"/"left"). A track that ends on the other side from where it started is one row at
  its last crossing time (net, so jitter on the line counts once; walking in and back out within one track counts 0).
- **queue_samples (B4.4)**: counter camera config sets `queue_zone` (normalised polygon) and `queue_sample_seconds` (5).
  Every sample counts customers (not staff, not unknown) whose feet are in the polygon; `est_wait_s` = length x the
  run's mean interaction duration (NULL when the run has no interactions).
- **pipeline_health.frozen_or_dark (B4.5)**: the CLI flags each processed frame (`frozen_or_dark` in detections.json):
  mean grey < `dark_brightness` (20), or the picture unchanged (< `frozen_change`) for `frozen_seconds` (2 s). The minute
  is 1 when most of its frames are flagged; NULL for runs recorded before the check existed.
- **Contract test**: `backend/events/test_events.py` checks the fixture and every local CV run under `backend/output/`
  with `ingest.validate`.
