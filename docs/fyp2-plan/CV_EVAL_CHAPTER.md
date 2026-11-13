# CV Evaluation: results sheet (B6 evidence for the chapter)

Every number below comes from the file or command beside it. Two sets: the **11 tuning clips** (rules were tuned on them, so their numbers are optimistic) and **set B, 14 held-out clips** (the headline; looked at once during tuning, for the span merge, which the chapter must say). Interaction matching is one-to-one at temporal IoU ≥ 0.5. All speed figures are CPU only.

## Current decision — 11 November 2026

The [combined team plan](RetailPulse_FYP2_Implementation_Plan.md) governs current work and ownership. Implement camera/CV first, then register the supplied map, then render live role occupancy and confirmed-interaction layers. Exactly four dynamic occupancy categories are allowed: **Customer, Employee, Customer–employee both, No one**. They are not fixed permitted-role polygons. Invalid/missing/unknown observation is separate quality metadata, never a fifth category or a false No one. Historical z1–z6, staff zones, queue/counter geometries and hot/gray terminology below are legacy technical references, not additional category requirements. No existing runtime/schema/fixture has been migrated by this documentation update.

## 1. Dataset and splits
- Interaction clips: 25 (11 tuning, `benchmarks/benchmark.json`; 14 held out, `benchmarks/benchmark_set_b.json`). Labelled interactions 30 (13 + 17) against a target of 30; pass-bys 13 (4 + 9) against a target of 15. Labels drafted and reviewed in CVAT (`backend/interaction/cvat_import.py`); the 11-clip labels have no second annotator.
- Roles: reviewed persons for all 25 clips in `benchmarks/persons.json`; a run track takes the role of the person it overlaps most (IoU ≥ 0.3 in ≥ 50 % of its frames, `role_labels.py`). 109 of 113 tracks labelled.
- Detector split is by recording (`~/data/split/split_manifest.csv`). Set B uses only test/val recordings, so no set-B frame was seen in detector training. Most of the 11 tuning clips are training recordings.
- Provenance audit (CV-PROVENANCE, 13 Nov): set B has **9** pass-bys in `benchmark_set_b.json` (an earlier note said 10; that was a counting error). The "random 6" reports (`report_random6_hand.json`, `report_random6_fitted.json`) use 4 tuning clips (8886, 8893, 8894, 8895 p2) and 2 set-B clips (8884, 8838 p2) with the labels from those two specs, so they are **not** an independent test set; quote them only as a hand-vs-fitted roles comparison.
- Zone-dwell labels: not made. No camera has zone polygons and the supplied map is not registered yet (MAP-2), so there is nothing to score dwell against.

## 2. Stage results
Commands: `python -m backend.interaction.benchmark <spec> --output <report>`; intervals: `python -m backend.interaction.confidence <report>` (clip bootstrap, 10 000 resamples, seed 0).

| Stage | Metric | Set B (held out) | 11 clips (tuned) | Source |
| --- | --- | --- | --- | --- |
| Detector (best_320 OpenVINO, 455 test images) | mAP50 / mAP50-95 / P / R | 0.969 / 0.896 / 0.963 / 0.953 | same | `report_set_b_merged.json` |
| Interactions, proximity only | P / R / F1 | 0.360 / 0.529 / 0.429 (tp 9 fp 16 fn 8) | 0.619 / 1.000 / 0.765 | `report_set_b_merged.json`, `report_11_merged.json` |
| Interactions, with pose judge | P / R / F1 | **0.409 / 0.529 / 0.462** (tp 9 fp 13 fn 8) | 0.765 / 1.000 / 0.867 (tp 13 fp 4 fn 0) | same |
| F1 95 % CI, with judge | | [0.267, 0.645] | [0.788, 0.960] | `confidence` |
| F1 95 % CI, proximity only | | [0.245, 0.600] | [0.625, 0.917] | `confidence` |
| Per-second overlap, with judge | P / R / F1 | 0.521 / 0.943 / 0.671 | 0.711 / 0.904 / 0.796 | `benchmark.overlap_seconds` on the reports' saved spans |
| Timing, with judge | start / end error (s) | 1.16 / 2.93 | 1.15 / 1.96 | reports above |
| Roles | accuracy per track | 1.000 (59 tracks, fitted roles) | | `report_set_b_roles_hand.json` |
| Tracking | ID switches per minute | 1.82 | 2.29 | reports above |
| Speed | CPU realtime factor | 0.87× (clean run, 7 Nov) | | `report_set_b.json`; later runs (0.09–0.48×) shared the CPU with other jobs and are not valid speed figures |

Per-second scores credit one long predicted span that covers several short labelled ones, which strict matching counts as a miss plus a false alarm (see section 6). Report both. GPU throughput: not measured (no GPU laptop run).

## 3. Role weights (`python -m backend.interaction.refit <spec>`)
Leave-one-clip-out logistic fit vs the hand-set weights (reference 0.55, bib colour 0.30, staff zone 0.10, stationary 0.05, threshold 0.45).

| Set | Hand-set accuracy | Hand-set employee recall | Fitted accuracy | Source |
| --- | --- | --- | --- | --- |
| 11 clips (50 tracks) | 0.960 | 0.889 | 1.000 | `refit_benchmark/refit.json` |
| Set B (59 tracks) | 0.915 | 0.815 (misses 5 of 27) | 1.000 | `refit_benchmark_set_b/refit.json` |

Fitted on the 11 clips and scored on set B: 59/59. Fitted weights ≈ yolo 0.61, bib colour 0.36, stationary 0.02–0.03, reference 0, staff zone 0, threshold 0.07–0.09 (`benchmarks/store_roles_fitted.json`). Reference and staff-zone are absent from every clip, so a weight of 0 means "not observed", not "useless". Threshold sweep: `refit_benchmark/sweep.png`, `refit_benchmark_set_b/sweep.png`. Decision (Ruhab, B3): which weights ship. Caveat: two cameras, few clips, so 100 % is not a general claim.

## 4. Signals in the event store
Every signal is written by `backend/events/ingest.py` (schema v1) and checked by the contract test (`backend/events/test_events.py`, `validate()`), which runs on the fixture day and on real CV runs.
- Real on any footage: interactions, per-track roles, unattended episodes, pipeline health (fps, confidence, unknown-role share, ID churn, frozen-or-dark), one heatmap grid per camera per hour (all people together, not split by role).
- Fixture only until the store map exists: named-zone dwell and transitions, entrance-line footfall, queue length and wait. Validated by unit tests against planted fixture patterns, not against labelled footage.
- Unattended episodes now reach direct dispatch automatically (`backend/dispatch.py`, tests in `backend/tests/test_dispatch.py`).

## 5. Camera handoff (`python -m backend.handoff_eval run.json labels.json`)
Not evaluated: no labelled crossings. Code and tests exist (`backend/test_handoff_eval.py`). Stretch item.

## 6. Error analysis (set B, with judge, `report_set_b_merged.json`)
13 false positives, 8 misses.
- **Span too long (4 FPs, 6 misses).** 155639 predicted 9.7–38.3 s covers labels 11.2–15.8, 19.5–28.4, 34.3–36.7; 8888 predicted 27.7–45.0 covers 26.7–32.5 and 36.3–42.2; also 8828 58.0–68.0 and 8834 40.7–53.0. Cause: the 4 s gap bridge and the merge join interactions the labels keep apart. The pair is found; the open question is the convention for a 4–6 s pause.
- **Duplicate from a customer ID switch (4 FPs).** 8884 27.3–30.7, 8831 51.0–61.3, 8839 7.7–18.7 and 23.7–28.3. A new customer ID defeats the same-customer merge. Fix belongs in tracking/re-ID, not merge rules.
- **No label nearby (5 FPs), checked frame by frame.** 8838 p2 20.3–34.7 and 8830 6.7–24.3 look like missed labels (face to face ~28 s; customer gesturing at seated employee). 8836 16.7–25.7: two employees talking, real FP (role flip or nearby customer). 8832 13.3–26.0 and 155639 54.0–65.3: probably real FPs (no engagement; side by side, not facing). If the labeller confirms both suspected misses in a blind re-check, the estimate is P ≈ 0.455, R ≈ 0.526, F1 ≈ 0.488; until then report 0.462.

## 7. Limitations
- Small labelled set (30 interactions, 25 clips, one store, two cameras); the CI on set B F1 spans 0.27–0.65.
- Set B was seen once during tuning (the span merge).
- Customer ID switches (1.8/min on set B) cause duplicate spans; no tracking fix was made, so it stays a limitation.
- CPU only; the one clean speed run is 0.87× realtime, so the demo runs on recorded footage.
- No zone polygons yet: zone-level signals are fixture-only.
- The 11-clip labels have no second annotator; pass-bys are judgement calls.
