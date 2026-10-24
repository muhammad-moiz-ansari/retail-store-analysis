# Implementation Plan

Order matters: each step uses the output of the one before it. Shapes are in [CONTRACTS.md](CONTRACTS.md).

## Step 0: Model consolidation (half a day)

Swap the generic `yolov8n.pt` for `best.pt` and delete unused weights. Details in [MODELS.md](MODELS.md).

**Files:** `backend/analyze_frame.py`, `backend/compare_people.py`, `backend/camera_service.py`,
`backend/camera_handoff.py`.
**Done when:** no `yolov8n.pt`/`yolo26n` references remain, existing tests pass, and analyze-frame still finds people.

## Step 1: Analytics from existing tracks (2–3 days)

New module `backend/interaction/analytics.py`: pure functions, no model, no I/O beyond what the
caller passes in.

```python
summarise(detections, interactions, people, config) -> dict   # the summary.json shape
```

Built from small pieces: `footfall`, `approach_times`, `unattended`, `employee_idle`, `zone_dwell`,
`heatmap`. Each is a loop over `detections` or `interactions`; the heatmap is one `numpy.histogram2d`.

**Files:**
- `backend/interaction/analytics.py` (new)
- `backend/interaction/config.py`: add `entrance_line`, `unattended_after_s`, `idle_window_s`,
  `idle_move_px`, `heatmap_grid`
- `backend/interaction/cli.py`: after the existing JSON writes (around line 196), also write
  `.summary.json` from `analytics.summarise(...)`
- `backend/interaction/test_analytics.py` (new): hand-built detections for one line crossing,
  one unattended customer, one idle employee, and one heatmap cell count

**Done when:** running the CLI on `backend/videos/` clips produces `interaction.summary.json` and
`python -m pytest backend/interaction/test_analytics.py` passes.

## Step 2: Real data on the dashboard (2–3 days)

**Backend** (`backend/app.py`): `GET /analytics/runs` and `GET /analytics/summary`, both behind
`require_manager`. They read the `*.summary.json` files under `backend/output/`. Validate `run`
against that listing; never join a raw user string into a path.

**Frontend:** replace the hardcoded arrays with a fetch to `/api/backend/analytics/summary`.

| Page | Hardcoded today | Bound to |
|---|---|---|
| `customer-info/page.tsx` | `ATTENDANCE_DATA`, `INTERACTION_SPARKLINE`, `UNATTENDED_EVENTS`, `ZONE_DWELL`, `HOURLY_TRAFFIC` | `footfall`, `interactions`, `unattended`, `zone_dwell` |
| `dashboard/page.tsx` | KPI tiles | `footfall`, `interactions.count`, `interactions.mean_approach_s`, `unattended.length` |
| `employee-info/page.tsx` | idle/engagement figures | `employee_idle`, `interactions` |
| `spatial-analytics/page.tsx` | heatmap | `heatmap` |

Keep `BEHAVIOR_DATA` and `TOP_PATHS` as labelled demo data (no path analytics in Step 1).
Every remaining demo value gets a visible "demo data" badge, as the report promises
("keeping prototype data explicitly labelled").

**Done when:** after one CLI run the four pages show that run's numbers; with no runs they show an
empty state instead of fake numbers.

## Step 3: Alerts on real events (1 day)

When the summary endpoint first reads a run, insert one `alerts` row per `unattended` entry
(shape in CONTRACTS.md). Use a deterministic id with `INSERT OR IGNORE` so repeat reads do not duplicate.
Use the existing store helpers in `backend/store_core.py`.

Remove the `ALERTS` fallback array from `alerts/page.tsx` once real rows exist.

**Done when:** a run with an unattended customer shows up on `/alerts`, can be resolved, and is
not recreated on the next load.

## Step 4: Evaluation (ongoing, start now in parallel)

Label the 10 waiting clips and run the benchmark. See [EVALUATION.md](EVALUATION.md).
This needs no code and fixes the report's weakest number, so start it in parallel with Step 0.

## Timeline against report Table 9.2

| Report weeks | Report activity | This plan |
|---|---|---|
| 1–3 | Detection and footfall integration | Step 0, Step 1 |
| 4–6 | Classification and engagement integration | Step 1 (idle, unattended), Step 3 |
| 7–9 | Trajectory, narration, dashboard binding | Step 2 |
| 10–12 | Labelled evaluation and tuning | Step 4 (labelling starts week 1) |
| 13–14 | Hardening, security, documentation | path validation on `/analytics/*`, role checks on new routes |
| 15–16 | Final testing, demo, report | rerun all benchmarks, record CPU throughput |

## Risks

| Risk | Mitigation |
|---|---|
| ID switches split one customer, inflating footfall and unattended counts | Report them in evaluation; only count tracks seen ≥ N frames |
| Moving camera makes zone rectangles and the entrance line meaningless | Run footfall/dwell only on static-camera clips; mark the rest "n/a" |
| Thresholds (`unattended_after_s`, idle) are store-specific (the proposal-defence "Gucci" comment) | They are config values per store; say so in the report as the answer to the generalisability critique |
| CPU too slow for long clips | `--track-every 3` already exists; report both speeds |
