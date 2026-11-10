# FYP-2 Implementation Plan

Derived from `FYP Report-main.pdf` (Ch. 8.11 Current Limitations, Ch. 9 Remaining FYP Plan),
checked against the code on branch `feature/interaction-live` (2026-10-23).

**Rule for everything here: no new models.** All new analytics are plain logic over the tracks
the interaction pipeline already produces.

| Doc | What it covers |
|-----|----------------|
| [PLAN.md](PLAN.md) | Ordered steps, files touched, done-when checks, timeline |
| [MODELS.md](MODELS.md) | Current YOLO weights and the consolidation to one detector + pose |
| [CONTRACTS.md](CONTRACTS.md) | Existing pipeline JSON shapes and the new summary/API shapes |
| [EVALUATION.md](EVALUATION.md) | Labelling the 10 clips, metrics to report, CPU throughput |
| [CHECKLIST.md](CHECKLIST.md) | Branch per item, status, order of work |
| [FUTURE_WORK.md](FUTURE_WORK.md) | Every remaining and out-of-scope item from the report, phased with step guides |

## Current team/tool foundation (2026-11-10)

The older Steps 0–4 and report-gap tables below remain the original plan. The active tool/graph phases and member responsibilities are tracked in [PLAN.md](PLAN.md). Saqib's committed event foundation is reused; Moiz Phase 1 published typed contracts; Phase 2 now implements five scoped read-only tools and a fixed-name registry. Business agents, graph, trusted application identity integration and UI binding remain separate pending work.

- [PROGRESS.md](PROGRESS.md): owner-tagged implementation versus verified/synthetic/real-data status, sources and exact checks.
- [PENDING.md](PENDING.md): remaining Moiz/Saqib/Ruhab work, dependencies and semantic limitations.
- [CONTRACTS.md](CONTRACTS.md#agent-read-tool-contracts--moiz-phase-1-2026-11-10): five typed callable interfaces and runnable reader/registry examples, UTC/evidence conventions, trusted observation context and data-availability notes for Ruhab.

Ignore local assistant handoffs under `docs/extra-docs/`; shared contracts/status remain tracked here. No report edits, CV training, production dispatch or later Moiz phases are part of the current tool implementation task.

## Report gaps this closes

| Report limitation / remaining item | Step |
|---|---|
| "Vision-derived dashboard metrics still use prototype or demo data" | 2, 3 |
| "Interaction results are available through the CLI; dashboard integration remains pending" | 2 |
| Footfall, zone dwell, heatmaps (in-scope analytics, not yet real) | 1 |
| Unattended-customer flags, employee idle time | 1, 3 |
| "Alerts on real events" (Iteration 3) | 3 |
| "Interaction accuracy is measured on one labelled clip only" | 4 |
| CPU throughput to record (deliverable 9.8) | 4 |

## Not in this plan

Everything outside Steps 0–4 (cross-camera handoff, shelf interaction, metric distance,
narration/query agents, real-time, multi-store, pilot) is phased in [FUTURE_WORK.md](FUTURE_WORK.md).
