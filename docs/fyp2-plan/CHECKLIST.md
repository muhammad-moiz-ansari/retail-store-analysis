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
      CI wiring is Member 3's C1.
- [x] **B1** Labelling: 11 tuning clips (`benchmark.json`, 13 interactions) and 14 held-out clips (`benchmark_set_b.json`,
      17 interactions, reviewed in CVAT) with `"people"`, `"roles"` and `"people_file"` (`role_labels.py`, `persons.json`).
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
