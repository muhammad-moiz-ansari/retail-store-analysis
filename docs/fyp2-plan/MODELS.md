# Model Consolidation

## What is loaded today

| Weights | Loaded by | Purpose |
|---|---|---|
| `backend/models/best.pt` (+ `best_320_openvino_model/`) | `interaction/pipeline.py` | Trained employee/customer detector (mAP50 0.969) |
| `backend/models/yolov8n-pose.pt` | `interaction/pose.py` via `config.pose_model` | Pose judge (precision 0.50 → 1.00) |
| `backend/yolov8n.pt` | `analyze_frame.py`, `compare_people.py`, `camera_service.py`, `camera_handoff.py` (via `vision_inference.py`) | Generic COCO person detector |
| `yolo26n-cls.pt` (repo root) | nothing; listed in `.gitignore` | Unused |
| optional `--roles` model | `interaction/pipeline.py` (`config.role_model`) | Off unless passed on the CLI |

## Target: one detector + pose

Keep `best.pt` and `yolov8n-pose.pt`. Drop `yolov8n.pt` and `yolo26n-cls.pt`.

`best.pt` already detects every person, labelled as employee or customer, so it replaces the
generic COCO detector.

### Changes

1. Point `MODEL_PATH` at `backend/models/best.pt` in `analyze_frame.py`, `compare_people.py`,
   `camera_service.py` (default for `CAMERA_MODEL_PATH`) and the `--model` default in `camera_handoff.py`.
2. **Remove the `classes=[0]` filter** at `analyze_frame.py:178`, `compare_people.py:46` and
   `camera_handoff.py:161`. In COCO class 0 is "person"; in `best.pt` class 0 is one of the two
   roles, so keeping the filter would silently drop half the people. Both classes are people,
   so no filter is needed.
3. Anything that reads `results[0].names[...]` expecting `"person"` now gets
   `"employee"`/`"customer"`. Grep before merging: `grep -rn "names\[" backend`.
4. Delete `backend/yolov8n.pt` and the root `yolo26n-cls.pt`.
5. Leave `--roles` alone. It is off by default and costs nothing unless used.

### Done when

- `grep -rn "yolov8n.pt\|yolo26n" backend` returns nothing.
- `/api/analyze-frame` and `/api/compare-people` still return people on a sample frame.
- The `camera_handoff.py` script still runs on the two sample clips.
- Existing tests pass: `python -m pytest backend`.

### Risk

`best.pt` was trained on store footage; generic photos uploaded to analyze-frame may detect
slightly worse than with COCO weights. Acceptable for the prototype; note it in the report.
