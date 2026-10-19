# Provisional floor-distance prototype

The trained local `models/best.pt` is reused without retraining or replacement.
Its classes are `0: employee`, `1: customer`. The local clip is 1080 × 1080,
4421 frames, nominal 59.822989 FPS (about 74 seconds). Actual decoded timestamps
are exported; nominal FPS sets output playback while reference selection seeks
on the video's media time axis.

## Setup and verified commands

Run PowerShell from the repository root. Use the existing Python environment:

```powershell
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

The existing environment already supplied OpenCV, NumPy, Ultralytics and CPU
PyTorch. ByteTrack additionally needed `lap>=0.5.12`; `lap==0.5.13` was installed
with `uv --cache-dir data/outputs/uv-cache pip install --python .venv/Scripts/python.exe 'lap>=0.5.12'`.
No model weights or footage are downloaded or uploaded. Ultralytics settings are
kept in local `data/outputs/ultralytics`. `FLOOR_INFERENCE_THREADS` controls CPU
inference threads (default 2).

Preview without calibration (sampling covers the complete temporary clip):

```powershell
.venv/Scripts/python.exe scripts/preview_floor_points.py --video data/videos/raw/queue_temp.mp4 --sample-every 30 --headless
```

For every frame, omit `--sample-every 30`. For a quick smoke test, add
`--max-frames 10 --output-dir data/outputs/distance/smoke`.
`--max-frames` counts processed frames, not source frame indices.
Previews save `foot_points.mp4`, `foot_points.jpg`, `detections.jsonl` and
`summary.json` in `data/outputs/distance/preview/`. JSONL includes original
boxes, red bottom-centre points, role scores, existing ByteTrack IDs and timestamps.
Confidence is the detector's joint detection/class score, not two independently
estimated detector/role probabilities. No heuristic role classifier is introduced.

Regenerate the supplied provisional calibration:

```powershell
.venv/Scripts/python.exe scripts/calibrate_floor.py --video data/videos/raw/queue_temp.mp4 --timestamp 0 --landmarks data/calibration/queue_temp.landmarks.json --output data/calibration/queue_temp.json --headless
```

Run the distance demo:

```powershell
.venv/Scripts/python.exe scripts/run_floor_distance.py --video data/videos/raw/queue_temp.mp4 --calibration data/calibration/queue_temp.json --motion-mode monitor --sample-every 30 --headless
```

Outputs in `data/outputs/distance/demo/`: annotated `distance.mp4`, `top_down.mp4`,
first-frame JPEGs, `metrics.jsonl`, and a coverage/status `summary.json`.
Use `--pair 1 2` to select two distinct track IDs. Otherwise up to 100 pairs
per frame are exported. Distances use raw accepted metric observations;
the top-down display uses smoothed positions. Predicted positions are outlined
and never used as supported pair measurements. IDs are local to each run.

All paths accept explicit CLI overrides. Relative paths are interpreted from the
current working directory; the documented commands assume the repository root.
`--headless` avoids display windows. Press Esc to stop an interactive preview/demo.
Outputs use local `mp4v`; codec, video geometry, opening and timestamps are checked.

## Editable measurements and points

Real configuration remains local and ignored by Git:

- `data/calibration/queue_temp.landmarks.json`: editable input, source point
  provenance, four estimated edge lengths, rectangle measurements and quality settings.
- `data/calibration/queue_temp.json`: generated H, metre landmarks, residuals,
  version/camera/calibration IDs and physical-validation status.
- `data/calibration/queue_temp.reference.jpg`: actual video reference frame.
- `data/calibration/queue_temp/`: reference, floor-grid and top-down diagnostics.

The owner's corrected perimeter order is **A → B → D → C**:
AB = DC = 3.13225 ft; BD = CA = 4.2075 ft. The assumed rectangle is therefore
0.9547098 m wide and 1.282446 m deep. Right angles and floor planarity are
assumptions, not measurements. All four values are estimates. Configuration is
marked `measurements_status: estimated`, `calibration_status: provisional`;
runtime exports have `approximate: true` and never claim physical validation.

Red-dot centres were read from the 479 × 479 marked screenshot, then mapped to
1080 × 1080 with pixel-centre resize mapping `(p + 0.5) * 1080/479 - 0.5`.
The clean screenshot is 718 × 718. Frame 0 was closest in an image-difference
scan across the clip and its first 30 frames; it was also inspected visually.
The screenshots are resized/modified, so these correspondences are approximate.
The operational polygon is only the four marked floor corners. No extrapolated
floor coverage is assumed. Feet outside that polygon produce no metre position.

To replace measurements, edit `rectangle.width`, `rectangle.depth_or_diagonal`
and `rectangle.units` (`ft` or `m`); keep `interpretation: width_and_depth`.
`rectangle` is the authoritative input for deriving the four `floor_xy_m` values.
`supplied_measurements_ft` is retained provenance; changing only that provenance
field does not change H. Update it alongside the authoritative dimensions.
To replace point locations, edit each `landmarks[].image_xy_px` and the matching
`operational_region_px`, both in original 1080 × 1080 video pixels. The screenshot
points under `point_provenance` are historical provenance, not active inputs.
Then rerun the calibration command. Runtime rejects edited inputs with a stale H.

For point-click calibration, omit `--headless` from the calibration command.
The window shows the explicit point order. Click numbered correspondences,
press U to undo, R to reset, S to save, Esc to cancel. Display resizing is reversed
once when saving original pixels. This UI is implemented; headless calibration
was exercised in this environment.

For general landmarks, remove `rectangle` and give each landmark an
`image_xy_px` and `floor_xy_m` in one shared floor coordinate system. Four pairs
are the minimum. Prefer 8–12 well-distributed measured points. More than four
pairs use RANSAC from floor metres to image pixels with an explicit pixel
threshold, then invert. Fitting residuals/inliers are saved; four-point residuals
near zero are expected algebraically and provide no independent accuracy evidence.

`config/cameras/floor_example.json` is non-sensitive illustrative data, described
by `floor.schema.json`. It cannot silently serve as runtime calibration while
marked illustrative. The CLI applies numerical/geometry checks; the schema is
also available for editors and external validators.

## Coordinates, quality and motion

Boxes are original-frame `[x1,y1,x2,y2]` pixels. Ultralytics `boxes.xyxy` already
reverses its preprocessing; it must not be unletterboxed a second time. A future
adapter can use `restore_box` for explicitly specified scale/padding.
Foot proxy is `((x1+x2)/2, y2)`. H maps original image pixels to floor metres;
homogeneous division is checked. Resized/cropped or other camera sources are
rejected. A global perspective-image pixel multiplier is never used.

No lens correction is currently applied to either calibration or runtime.
Intrinsics/distortion metadata slots are retained, but supplying coefficients
alone does not activate undistortion. To add it, explicitly undistort both
reference landmarks/operational polygons and runtime coordinates through the
same camera model, record that pixel space, then extend the coordinate-space
guard. Normalized coordinates cannot be mixed with pixels.

Statuses include `uncalibrated`, `observed_proxy`, `predicted`, `unreliable`,
`out_of_region`, `motion_unverified`, and `motion_invalid`. Unsupported positions
and distances are `null` with reasons, never valid-looking zeroes.
Lower-frame clipping, boxes outside frame, person overlap and manual exclusion
regions are checked. `observed_proxy` does not establish foot visibility.
Seated people, carts, chairs, shelf occlusion and imperfect boxes can make the
proxy wrong. Add polygons to `exclusion_regions_px` for known difficult areas;
the same exclusions mask motion features. No pose model or reliable visibility
detector is claimed. The localization function is separate from detection so
a future keypoint-based adapter can replace the proxy.

ByteTrack association reuses the existing pipeline. Roles are direct model
observations and are not used for downstream metric smoothing. The metric
smoother uses real timestamps, a speed/jump gate, last reliable observation time,
short prediction limits and stale-track expiry. Unsupported geometry clears
smoothing state, preventing interpolation through alignment failures.

Motion modes:

- `monitor` and `fixed`: compare masked static floor features directly against
  the reference. Require configured match count, inlier ratio, spatial spread,
  residual and supported-region displacement limits. Both suppress metre output
  on shifted or unverified frames; `fixed` never means blindly trusting H.
- `snapshot`: only the exact reference frame supports approximate projection.
  All other frames are unavailable.

The exact reference frame is labelled `reference_frame`. Other accepted frames
are `aligned_provisional`; too few/poorly distributed floor features mean
`motion_unverified`, not stationary. Diagnostics record match/inlier counts,
ratio, residual pixels, spatial coverage and maximum floor-region displacement.
Motion thresholds are exposed in the local config and are development settings,
not metre-accuracy guarantees. General background matches, parallax and rolling
shutter remain concerns. Compensation/stabilization is deliberately deferred:
this moving clip has not demonstrated reliable distributed static floor matches.
Person smoothing cannot repair camera movement. Use a new calibration for final
stationary footage and do not reuse this temporary matrix for another installation.

## Evaluation and remaining physical work

Focused synthetic checks:

```powershell
.venv/Scripts/python.exe -m unittest backend.tests.test_floor_distance -v
```

The 17 checks cover known projections/distances, ft-to-m conversion, degenerate
geometry, denominators, region/frame/unit guards, robust fitting, preprocessing
recovery, invalid/occluded/motion states, smoothing/prediction/expiry, synthetic
camera shift rejection, and independent evaluation statistics. Existing handoff
tests also pass when invoked with the repository's expected backend import path:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'backend')
$env:YOLO_CONFIG_DIR = (Join-Path (Get-Location) 'data/outputs/ultralytics')
.venv/Scripts/python.exe -m unittest backend.test_handoff_core -v
```

Generate runtime coverage (no physical accuracy assertion):

```powershell
.venv/Scripts/python.exe scripts/evaluate_floor_distance.py --metrics data/outputs/distance/demo/metrics.jsonl --output data/outputs/distance/demo/evaluation.json
```

For physical evaluation, copy `config/cameras/validation_example.json` into
`data/calibration/validation.json`, replace its illustrative data with independent
measured references, and set `reference_kind: independently_measured`. Supply
withheld reference-frame pixels and known metre coordinates/separations, labelled
near/middle/far and visible/occluded when available. Fitting points cannot serve
as withheld point samples. Evaluate with:

```powershell
.venv/Scripts/python.exe scripts/evaluate_floor_distance.py --calibration data/calibration/queue_temp.json --annotations data/calibration/validation.json --metrics data/outputs/distance/demo/metrics.jsonl --output data/outputs/distance/demo/measured_evaluation.json
```

Reports separate point radial/x/y error and pair-distance error: sample count,
MAE, median absolute error, 95th percentile, signed bias (meaningful for x/y and
pair errors), grouped by region/visibility, plus acceptance/rejection coverage.
Synthetic correctness and observed detection coverage are separate from physical
accuracy. No measured physical accuracy or validated camera stability is available.

Actual temporary-clip run: 148 frames sampled every 30 source frames, 284 person
detections. The conservative monitor accepted only the reference-frame snapshot:
9 frames were motion-invalid and 138 were unverified. Only 2 of 284 position
observations (0.70%) were accepted; one approximate pair was available in the
reference frame. That pair includes a seated person's bounding-box proxy and
must not be treated as measured standing-person spacing. This is a coverage
diagnostic, not an accuracy result. Whole-clip supported metric analysis is not
available from this calibration/moving view. Snapshot and missing-selected-track
failure behavior were also exercised on 3 sampled frames.

Before final acceptance: verify rectangle dimensions/corner correspondence;
measure additional distributed landmarks plus withheld near/middle/far separations;
record known standing positions with visible feet; obtain `queue_fixed.mp4` from
a stationary final camera; create and independently evaluate its own calibration.

Raw footage, all real calibration data and generated diagnostics remain ignored
under `/data/videos/raw/`, `/data/calibration/`, `/data/outputs/`. Trained weights
stay in their existing ignored `models/` location. Source, examples, schema and
documentation are tracked. No frontend or staffing/orchestration layer was changed.
