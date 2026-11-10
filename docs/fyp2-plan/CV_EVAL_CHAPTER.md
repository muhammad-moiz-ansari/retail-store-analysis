# CV Evaluation Chapter: skeleton (B6)

## Current decision — 11 November 2026

The [combined team plan](RetailPulse_FYP2_Implementation_Plan.md) governs current work and ownership. Implement camera/CV first, then register the supplied map, then render live role occupancy and confirmed-interaction layers. Exactly four dynamic occupancy categories are allowed: **Customer, Employee, Customer–employee both, No one**. They are not fixed permitted-role polygons. Invalid/missing/unknown observation is separate quality metadata, never a fifth category or a false No one. Historical z1–z6, staff zones, queue/counter geometries and hot/gray terminology below are legacy technical references, not additional category requirements. No existing runtime/schema/fixture has been migrated by this documentation update.

Fill each `TODO` from the command's output once B1 labels exist. Do not write a number that was not produced by the command beside it.

## 1. Dataset and splits
- Clips, interactions, pass-bys labelled (target 30 / 15). TODO from `benchmark.json`.
- Detector split is by recording (`split_dataset.py`); state the train/test overlap check result. TODO
- Zone-dwell clips (3): person, zone, enter/exit. TODO

## 2. Stage results (`python -m backend.interaction.benchmark <spec> --output ...`)
| Stage | Metric | Value |
| --- | --- | --- |
| Detector | mAP50 | TODO |
| Interactions, proximity only (`--judge off`) | P / R / F1 | TODO |
| Interactions, with pose judge | P / R / F1 | TODO |
| Timing | start / end error (s) | TODO |
| Roles | accuracy per track | TODO |
| Tracking | ID switches per minute | TODO |
| Speed | CPU realtime factor; GPU if available | TODO |

Report confidence intervals if interactions < 30.

## 3. Role weights (`python -m backend.interaction.refit`)
- Hand-set (0.55/0.30/0.10/0.05, threshold 0.45) vs fitted, leave-one-clip-out. TODO table.
- Threshold sweep figure. TODO
- Decision: keep whichever wins on held-out clips.

## 4. Signals in the event store
Zones/dwell, footfall (entrance line), queue length/wait, pipeline health: what was validated, against which labels. TODO

## 5. Camera handoff (`python -m backend.handoff_eval run.json labels.json`)
Confirmed / uncertain / unmatched rates on labelled crossings. TODO

## 6. Error analysis
5–10 failure cases, each: clip, timestamp, frame, cause. TODO

## 7. Limitations
Small labelled set, single store, CPU-only throughput, per-camera polygons hand-drawn.
