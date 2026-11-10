# Implementation Plan

Order matters: each step uses the output of the one before it. Shapes are in [CONTRACTS.md](CONTRACTS.md).

## Current shared ownership and agent phases (2026-11-10)

This tracked table preserves the agreed member division independently of local/ignored handoffs. The Steps 0–4 below remain the original CV/dashboard implementation plan, not the same numbering as Moiz's four tool/graph phases. Current evidence and dependencies are in [PROGRESS.md](PROGRESS.md) and [PENDING.md](PENDING.md).

| Owner | Retained responsibility |
|---|---|
| Moiz Ansari | Read-only tools; LangGraph Orchestrator; Query and supporting reasoning (Anomaly/next-day planning); manager/dashboard analytics, data visualization, frontend binding/integration. Completed Interaction detection reused; data integration/evaluation/UI binding remain independent work. |
| Saqib Atif | Canonical CV/event schema, fixture generator and ingestion; backend/AI integration and CV feeds; labels/split audit, CV benchmarks and handoff evaluation; actual employee selection, source-zone safety, task persistence/idempotency, delivery/voice and deployment. |
| Ruhab Ahmad | Customer Behavior and Employee Activity business logic; model fine-tuning using Saqib's labels/factors; manager/employee interface refinement; Insight Narration/Digest and Clip Review; QA, documentation, presentation, output validation and acceptance. |

Finalized top-level architecture: Customer Behavior (Ruhab), Employee Activity (Ruhab), Interaction (Moiz, existing), Employee Task Assignment (Saqib), Insight Narration (Ruhab), Query (Moiz), Orchestrator (Moiz). Classification/tracking/zones are shared CV tools; supporting reasoning does not silently become extra top-level agents.

Moiz phases: **M-P1** typed contract/fixture foundation (implemented); **M-P2** five concrete read-only tools (implemented with fixture/security regression tests; production context/identity binding pending); **M-P3** callable injectable grounded LangGraph, scoped development traces and specialist hooks (offline implemented; actual business agents, HTTP auth binding, durable/provider evaluation pending); **M-P4** isolated internal operational adapter and teammate handoff (fake-only verified; actual producer auth, idempotency, assignment/voice and business policy remain pending). Wider A1 tools, real-agent/provider evaluation and frontend integration remain separate pending work. Moiz's Protocols/adapters do not complete Ruhab's business agents or Saqib's operational service.

Direct aisle dispatch requires no manager approval or manager-enabled auto mode. Separate next-day schedule/roster proposals can retain their own approval workflow. Metric floor calibration and POS analytics are not reopened by these phases.

## Step 0: Model consolidation (done)

COCO tracks people, `best.pt` only labels roles. See [MODELS.md](MODELS.md).

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
