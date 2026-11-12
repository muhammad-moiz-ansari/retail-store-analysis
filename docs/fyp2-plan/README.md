# FYP-2 Implementation Plan

## Current decision — 11 November 2026

RetailPulse now uses PostgreSQL for application records, CV events, dashboard reads, and camera identity records. Set the Python backend's `DATABASE_URL` and follow [PostgreSQL setup and legacy import](POSTGRESQL_SETUP.md). Earlier phase evidence below records the database used at those checkpoints.

The [combined team plan](RetailPulse_FYP2_Implementation_Plan.md) governs current work and ownership. Implement camera/CV first, then register the supplied map, then render live role occupancy and confirmed-interaction layers. Exactly four dynamic occupancy categories are allowed: **Customer, Employee, Customer–employee both, No one**. They are not fixed permitted-role polygons. Invalid/missing/unknown observation is separate quality metadata, never a fifth category or a false No one. Historical z1–z6, staff zones, queue/counter geometries and hot/gray terminology below are legacy technical references, not additional category requirements. No existing runtime/schema/fixture has been migrated by this documentation update.

The tracked combined plan is the teammate-readable source of truth; the identical local extra-docs copy is ignored. Historical workstream detail is retained in LEGACY_WORKSTREAM_DETAILS.md. Saqib's Nov-10 snapshot predates Moiz's foundation and includes unintegrated refit evidence; see the combined evidence matrix before continuing.

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
| [FRONTEND_DEPLOYMENT.md](FRONTEND_DEPLOYMENT.md) | Vercel root/branch/build settings and local dependency consistency |
| [FUTURE_WORK.md](FUTURE_WORK.md) | Every remaining and out-of-scope item from the report, phased with step guides |
| [ACCEPTANCE.md](ACCEPTANCE.md) | Ruhab's team acceptance scenarios and threshold review sheet |
| [QA_DASHBOARD.md](QA_DASHBOARD.md) | Ruhab's dashboard QA findings for Moiz |
| [SECURITY_REVIEW.md](SECURITY_REVIEW.md) | Ruhab's C6 security review, with an owner per finding |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | Ruhab's demo script with evidence and a fallback per step |

## Current team/tool foundation (2026-11-10)

**Dashboard update (11 Nov, Moiz):** M-UI-P1/P2/P3 connection is implemented: validated provider, fixture preview and configured backend read-tool routes behind active-account/server-membership checks. Dashboard defaults to Configured backend; preview requires explicit choice. 155 backend tests/1 existing real-output skip, 34 frontend checks, typecheck/lint/build and synthetic actual-login Chrome integration passed. Real feed/config/agent/deployment acceptance remains pending. See [backend setup](DASHBOARD_BACKEND_SETUP.md), [provider contracts](CONTRACTS.md#dashboard-presentation-provider--m-ui-p1-moiz), [UI phases](PLAN.md#dashboard-providerbinding-phases--current-moiz-ui-work) and PROGRESS/PENDING. No DB migration, map/agent implementation or live-data acceptance is claimed.

The older Steps 0–4 and report-gap tables below remain the original plan. The active tool/graph phases and member responsibilities are tracked in [PLAN.md](PLAN.md). Saqib's committed event foundation is reused; Moiz Phase 1 published typed contracts; Phase 2 implements five scoped read-only tools and a fixed-name registry; Phase 3 adds callable LangGraph routing/grounding and scoped development traces; Phase 4 adds an isolated internal operational adapter verified only with fake handlers. Dashboard-only HTTP/membership integration is now supplied by M-UI-P3. Real business agents, graph HTTP/internal producer binding, actual dispatch/idempotency/voice, durable/provider acceptance and wider real-output UI binding remain pending.

- [PROGRESS.md](PROGRESS.md): owner-tagged implementation versus verified/synthetic/real-data status, sources and exact checks.
- [PENDING.md](PENDING.md): remaining Moiz/Saqib/Ruhab work, dependencies and semantic limitations.
- [CONTRACTS.md](CONTRACTS.md#agent-read-tool-contracts--moiz-phase-1-2026-11-10): five typed callable interfaces and runnable reader/registry examples, UTC/evidence conventions, trusted observation context, graph/service registration examples and data-availability notes for Ruhab.

Ignore local assistant handoffs under `docs/extra-docs/`; shared contracts/status remain tracked here. No report edits, CV training, production dispatch or later Moiz phases are part of the current tool implementation task.

The [internal operational contract](CONTRACTS.md#internal-operational-dispatch-contract-moiz-phase-4) includes Saqib's import/signature, exact field mapping and current endpoint gaps, Ruhab's signal/policy boundary, and a fake-only fixture replay command. Do not register the adapter in the manager query graph or call the legacy live endpoint from the example.

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
