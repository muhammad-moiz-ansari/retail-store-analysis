# Models

## Current decision — 11 November 2026

The [combined team plan](RetailPulse_FYP2_Implementation_Plan.md) governs current work and ownership. Implement camera/CV first, then register the supplied map, then render live role occupancy and confirmed-interaction layers. Exactly four dynamic occupancy categories are allowed: **Customer, Employee, Customer–employee both, No one**. They are not fixed permitted-role polygons. Invalid/missing/unknown observation is separate quality metadata, never a fifth category or a false No one. Historical z1–z6, staff zones, queue/counter geometries and hot/gray terminology below are legacy technical references, not additional category requirements. No existing runtime/schema/fixture has been migrated by this documentation update.

## What is loaded

| Weights | Loaded by | Purpose |
|---|---|---|
| `backend/yolov8n.pt` (COCO) | `interaction/pipeline.py` (`person_model`), `analyze_frame.py`, `compare_people.py`, `camera_service.py`, `camera_handoff.py` | Finds and tracks people |
| `backend/models/best.pt` (+ `best_320_openvino_model/`) | `interaction/role_classifier.py` (`role_model`) | Employee/customer label only |
| `backend/models/yolov8n-pose.pt` | `interaction/pose.py` via `config.pose_model` | Pose judge |

## Why COCO tracks and best.pt only labels (A0, 2026-10-24)

The original plan was to replace COCO with `best.pt` everywhere. Measured before switching:

- On 46 frames sampled from `ShopAssistant1cor.mp4` and `OneShopOneWait1cor.mp4` (CAVIAR corridor
  footage), COCO found 140 people and `best.pt` 53–56, missing clearly visible people at 0.06–0.21
  confidence. `best.pt` does well only on footage like its training data.
- `analyze_frame`, `compare_people` and `camera_handoff` never use the model's role, so they stay on COCO.

In the interaction pipeline COCO tracks every person and `best.pt` labels roles:

1. A new track gets `best.pt` labels during its first `role_model_seconds` (1 s). Its role is kept after that.
2. Each track is rechecked every `role_recheck_seconds` (2 s). Without the recheck, an ID switch at 34 s in
   `IMG_8829` passed the employee's locked label to the customer and the benchmark lost its only interaction.
3. When every visible track has a fresh label, `best.pt` does not run at all.

Benchmark (`benchmarks/benchmark.json`, CPU, judge on): with-judge F1 1.0 (unchanged), interaction start
1.9 s late instead of 0.3 s (the recheck delay), 1.6–1.9x realtime per clip against 1.2–1.5x before.

`yolo26n-cls.pt` is not in the repo. Ultralytics downloads it for BoT-SORT ReID only when the tracker
runs an OpenVINO model; the COCO `.pt` tracker reuses its own features.

## Refit status reconciliation

Saqib reports completed role/refit work at d6783b2 and candidate fitted weights (0.61 YOLO, 0.36 bib, 0.03 stationary; threshold 0.094). That commit, role_labels.py and candidate artifact are not present here. These numbers are reported candidates, not adopted defaults. Ruhab retains model fine-tuning/validation ownership; Saqib supplies branch evidence. Adoption requires a user/team decision and matched before/after benchmarks. Missing reference/staff-zone factors mean unobserved in those clips, not proof of irrelevance; fixed staff-only zone categories are not part of the new map model.
