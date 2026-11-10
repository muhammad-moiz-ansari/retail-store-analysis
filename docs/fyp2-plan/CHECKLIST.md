# FYP-2 Checklist

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
- [ ] **B1** Labelling (manual): 1 of 11 clips reviewed; the other 10 have `candidates_to_review` in `benchmark.json`.
      Also add `"people"` (distinct people), `"roles"` and `"people_file"` per clip. 3 zone-dwell clips not started.
      Detector split is already by recording.
- [~] **B2** Benchmark: P/R/F1 proximity vs judge, start/end error, role accuracy, ID switches/min (needs `"people"`),
      CPU realtime factor. To do: GPU throughput run, error analysis write-up.
- [~] **B3** `python -m backend.interaction.refit`: leave-one-clip-out logistic regression vs hand-set, sweep plot.
      Waits on B1 labels.
- [x] **B4** CLI `--camera` writes runs to the store; `floor_zones` dwell/transitions/heatmaps, `entrance_line` footfall,
      `queue_zone` queue length/wait, frozen-or-dark frame check. Each camera still needs its polygons drawn in a `--config` file.
- [~] **B5** `python -m backend.handoff_eval run.json labels.json`. Waits on labelled crossings.

## Moiz tools/graph phases (separate from legacy A/B checklist numbering)

Ownership and actual evidence: [PLAN.md](PLAN.md), [PROGRESS.md](PROGRESS.md), [PENDING.md](PENDING.md).

- [x] **M-P1-CONTRACTS / M-P1-FIXTURE / M-P1-DOCS (Moiz)** Typed contracts and five callable interfaces, UTC/filter/result/evidence validation, unchanged Saqib fixture/schema, test-only second store and shared publication. Offline verified; no SQL readers or real-agent claim.
- [ ] **M-P2-TOOLS (Moiz)** Concrete scoped read-only implementations and hand-calculated query tests.
- [ ] **M-P3-GRAPH (Moiz)** Injectable LangGraph, grounded claims, scoped traces and Ruhab specialist hooks; trusted identity/store binding before public routes.
- [ ] **M-P4-HOOK (Moiz adapter; Saqib operations)** Isolated fake dispatch adapter and integration handoff; no production delivery.
- [ ] **R-BUSINESS-AGENTS / R-UX-NARRATION-QA (Ruhab)** Real business logic, fine-tuning, interface refinement, Narration/Digest/Clip Review and acceptance; Protocols do not complete these tasks.
- [ ] **S-B0-VERDICT / S-B4-REALFEED / S-DEPLOY-INTEGRATION (Saqib)** Unattended verdict review, real feeds/configuration, operational assignment/voice and deployment.

The historical B1/B2/B3/B5 status above is not a fresh label/benchmark audit. Existing labelled/benchmark commits are present; remaining labels, refit validation, throughput/error analysis and handoff evaluation retain independent pending status. No large evaluation rerun was performed in Moiz Phase 1.
