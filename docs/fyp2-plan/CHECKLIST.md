# FYP-2 Checklist

## Current decision — 11 November 2026

The [combined team plan](RetailPulse_FYP2_Implementation_Plan.md) governs current work and ownership. Implement camera/CV first, then register the supplied map, then render live role occupancy and confirmed-interaction layers. Exactly four dynamic occupancy categories are allowed: **Customer, Employee, Customer–employee both, No one**. They are not fixed permitted-role polygons. Invalid/missing/unknown observation is separate quality metadata, never a fifth category or a false No one. Historical z1–z6, staff zones, queue/counter geometries and hot/gray terminology below are legacy technical references, not additional category requirements. No existing runtime/schema/fixture has been migrated by this documentation update.

Integration branch: `fyp-2` (cut from `stage`). Each item gets its own branch off `fyp-2`
and merges back into `fyp-2` when its "Done when" in [FUTURE_WORK.md](FUTURE_WORK.md) holds.

## Phase A: FYP-2 core

- [x] **A0** Model consolidation (COCO tracks, best.pt labels): `feature/fyp2-a0-model-consolidation`
- [ ] **A1** Analytics module + `.summary.json`: `feature/fyp2-a1-analytics`
- [ ] **A2** Analytics API + dashboard binding: `feature/fyp2-a2-dashboard-binding`
- [ ] **A3** Real events → alerts → dispatch: `feature/fyp2-a3-real-alerts`
- [ ] **A4** Evaluation + threshold sweep (labelling is manual): `feature/fyp2-a4-evaluation`

## Phase B: agents and product features

- [ ] **B1** Employee Activity Agent: `feature/fyp2-b1-employee-activity`
- [ ] **B2** Track → account linkage, safe dispatch: `feature/fyp2-b2-dispatch-linkage`
- [ ] **B3** Insight Narration + report export: `feature/fyp2-b3-reports`
- [ ] **B4** Orchestrator + real system status: `feature/fyp2-b4-system-status`
- [ ] **B5** Query Agent: `feature/fyp2-b5-query-agent`
- [ ] **B6** Remaining page bindings: `feature/fyp2-b6-page-bindings`

## Phase C: testing, hardening, docs

- [ ] **C1** Planned test cases: written inside each feature branch above, gaps closed in `fyp-2`
- [ ] **C2** Security and privacy: `feature/fyp2-c2-security`
- [ ] **C3** Performance evidence: `feature/fyp2-c3-performance`
- [ ] **C4** Report and docs update: directly on `fyp-2` at the end

## Phase D: post-FYP (branch cut only when started)

- [ ] D1 camera handoff · D2 metric distance · D3 foot locator · D4 depth spike
- [ ] D5 shelf interaction · D6 promotion effect · D7 real-time · D8 multi-store · D9 pilot

## Order and how

1. **A0** done: `best.pt` missed most people outside store footage, so COCO tracks and `best.pt` labels roles.
2. **A1**: `analytics.py` as pure functions plus `test_analytics.py` with hand-built tracks,
   then the CLI writes `.summary.json`. A1 is cut from `fyp-2` after A0 is merged.
3. **A2 → A3 → B1**: each needs the summary from A1, so each is cut after the previous merge.
4. **B2–B6, C2, C3**: independent of each other once A3 is in.
5. **A4 labelling** is yours (no code) and can start now; the benchmark changes land on the A4 branch.

## Plan B (CV signals and evaluation) status

Branch `feature/fyp2-b0-event-store` (B0 to B5 code). Contract details in [CONTRACTS.md](CONTRACTS.md).

- [x] **B0** `backend/events/`: schema v1 (+ `heatmaps`), idempotent ingestion, derived unattended episodes,
      seeded fixture day (`python -m backend.events.fixtures`), contract test over fixture and local runs.
      CI coordination is Ruhab's C1; Saqib supplies backend checks and Moiz frontend checks.
- [x] **B1** Labelling: 11 tuning clips (`benchmark.json`, 13 interactions) and 14 held-out clips (`benchmark_set_b.json`,
      17 interactions, 9 pass-bys, reviewed in CVAT) with `"people"`, `"roles"` and `"people_file"` (`role_labels.py`, `persons.json`).
      Open: labeller re-checks IMG_8838 p2 / IMG_8830; second annotator for the 11 clips. Zone-dwell clips dropped (no polygons).
- [x] **B2** Benchmark on both sets: set B F1 0.462 with judge (headline), 11 clips 0.867 (tuned). Error analysis done.
      To do: speed on an idle machine (0.87x realtime on CPU is the only clean figure).
- [x] **B3** `python -m backend.interaction.refit`: leave-one-clip-out role accuracy hand-set 0.960 / 0.915 (11 clips / set B),
      fitted 1.000 / 1.000; fitted on the 11 clips scores set B 59/59. Fitted weights as a store config:
      `benchmarks/store_roles_fitted.json` (uncalibrated cameras only; reference factor absent from all clips).
- [x] **B4** CLI `--camera` writes runs to the store; `floor_zones` dwell/transitions/heatmaps, `entrance_line` footfall,
      `queue_zone` queue length/wait, frozen-or-dark frame check. Zone polygons not drawn by decision: interactions use
      person-to-person distance, so zone signals stay off until a camera has a `--config` with polygons.
- [~] **B5** `python -m backend.handoff_eval run.json labels.json`. Waits on labelled crossings.

## Moiz tools/graph phases (separate from legacy A/B checklist numbering)

Ownership and actual evidence: [PLAN.md](PLAN.md), [PROGRESS.md](PROGRESS.md), [PENDING.md](PENDING.md).

- [x] **M-P1-CONTRACTS / M-P1-FIXTURE / M-P1-DOCS (Moiz)** Typed contracts and five callable interfaces, UTC/filter/result/evidence validation, unchanged Saqib fixture/schema, test-only second store and shared publication. Offline verified; no SQL readers or real-agent claim.
- [x] **M-P2-TOOLS / M-P2-CONTEXTUAL / M-P2-REGISTRY (Moiz)** Five concrete read-only tools, trusted-scope registry, manual-answer query tests, health-aware union coverage and seeded replay. Synthetic/offline verified; production identity/store/configuration binding remains pending.
- [x] **M-P3-GRAPH / M-P3-GROUNDING / M-P3-TRACES / M-P3-HANDOFF (Moiz)** Callable injectable LangGraph, exact metric/evidence grounding with one repair, scoped bounded development traces and Ruhab registration hooks, verified offline. Actual business agents, durable/live-provider validation and trusted identity/store binding before public routes remain pending.
- [x] **M-P4-ADAPTER / M-P4-ISOLATION / M-P4-HANDOFF (Moiz)** Isolated internal typed event/handler adapter, fake assigned/no-eligible/duplicate/unavailable/error checks, query isolation and seeded teammate replay. No production task delivery or real eligibility/idempotency acceptance claim; Saqib's implementation and Ruhab's policy remain pending.
- [~] **R-BUSINESS-AGENTS / R-UX-NARRATION-QA (Ruhab)** Customer Behavior / Employee Activity agents, signal policy and Narration digest are implemented and fixture-tested on `fyp2-ruhab`. Clip Review logic, CI workflow, acceptance plan and dashboard QA notes are also done. Real-data validation, fine-tuning, real-footage Clip Review and acceptance runs remain.
- [ ] **S-B0-VERDICT / S-B4-REALFEED / S-DEPLOY-INTEGRATION (Saqib)** Unattended verdict review, real feeds/configuration, operational assignment/voice and deployment.

The historical B1/B2/B3/B5 status above is not a fresh label/benchmark audit. Existing labelled/benchmark commits are present; remaining labels, refit validation, throughput/error analysis and handoff evaluation retain independent pending status. No large evaluation rerun was performed in Moiz Phase 1.

## Current camera/map sequence

Separate Moiz UI sequence (not tool/graph phase numbering):

- [x] M-UI-P1: typed validated provider, five synthetic display scenarios and offline tests; 16 provider tests plus frontend typecheck/targeted lint/legacy regression passed. No page binding.
- [x] M-UI-P2: fixture-bound dashboard, fabricated analytics replaced, provenance/quality/freshness visible, refresh/cancellation/expiry checked; 27 tests plus lint/typecheck/build and isolated Chrome scenario/route/mobile checks passed. No real analytics integration.
- [x] M-UI-P3 connection: backend provider, active-account/server-config membership, scoped read-tool snapshot routes and explicit source selection; 155 backend tests/1 existing skip, 34 frontend tests, lint/typecheck/build and actual-login synthetic browser checks passed.
- [ ] M-UI-P3 acceptance (Saqib config/deployment, Ruhab outputs/QA, Moiz support): verified real memberships/CV/source context, known real metric answers and deployed integration. No real values installed by the connection implementation.

M-UI-P1/P2/P3 connection does not complete legacy A2/B6 real-data acceptance, real business agents, map registration or the following camera/map acceptance items. The graph's HTTP authority/durable traces and actual dispatch remain separate.

- [ ] MAP-1 (Saqib): real camera/CV/event/health verification.
- [ ] MAP-2 (Saqib spatial/backend, Moiz binding, Ruhab QA): supplied-map registration and visibility metadata.
- [~] MAP-3 (Ruhab semantics, Saqib feeds, Moiz readers/rendering): exactly four dynamic categories and separate customer/employee/confirmed-interaction layers. Ruhab's classifier/hysteresis/layers are implemented and fixture-tested; real projected feeds and rendering remain.
- [ ] TEAM-ACCEPTANCE: observe category transitions and genuine empty space without turning blocked/unknown observations into No one; complete actual dispatch/employee/manager workflow.

These are planned, not implemented by this documentation reconciliation. Existing six-zone fixtures are historical test data, not the new category schema.
