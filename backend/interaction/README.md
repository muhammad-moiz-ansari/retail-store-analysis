# Interaction module

This is a standalone prototype. It does not alter or mount itself into the existing RetailPulse backend.

It detects people with the project YOLO model, assigns persistent IDs using ByteTrack, labels each tracked person as an employee or customer, and records sustained employee/customer proximity as an interaction.

## Employee-identification evidence

The module combines signals over a ByteTrack ID rather than trusting one frame:

- **Bib / uniform appearance**: the custom role model is the primary signal. The HSV bib fallback is intended only for early experiments.
- **Time in a staff-only zone**: a configured checkout, counter, stock-room, or service-desk region gradually raises staff confidence.
- **Stationary work behaviour**: remaining at a configured work zone reinforces the score; it never classifies someone by itself.
- **Temporal smoothing**: confidence is smoothed across frames to reduce one-frame misclassifications and lighting changes.

Customer dwell time in ordinary aisles is deliberately not used as employee evidence. Configure `staff_zones` using normalised coordinates `(x1, y1, x2, y2)` after camera calibration. This prevents the common error of calling a browsing customer an employee simply because they pause for a long time.

## Bib-labelled dataset

Train a small YOLO role model from the existing bib-labelled dataset with labels such as `employee`, `customer`, or `bib`. Supply the generated weight file at runtime:

```powershell
python -m backend.interaction.cli path\to\footage.mp4 --track-every 3 --every 15 --output interaction.mp4
```

By default one model does detection, tracking and the YOLO role factor: `backend/models/best_320_openvino_model` (`best.pt` exported to OpenVINO at 320 px, ~10 fps tracking on a laptop CPU). `--track-every 3` tracks at 10 fps on 30 fps video; `--every 15` scores roles and writes output at 2 fps. Re-export with `YOLO('backend/models/best.pt').export(format='openvino', imgsz=320)` and rename the folder to `best_320_openvino_model`. With a plain COCO person model instead, set `person_classes=(0,)` and pass the role model via `--roles`; with neither, classification falls back to the configured yellow-bib HSV range. Update `bib_hsv_lower` and `bib_hsv_upper` in an `InteractionConfig` instance to match the real bib colour and lighting.

## Interaction judge (second model)

Proximity (body-height distance for `min_interaction_seconds`, without the pair sliding past each other by more than `max_relative_drift_heights`) only nominates a candidate. The judge then receives `judge_frames` crops of the pair from the last `min_interaction_seconds` and answers `interaction` or `no_interaction`. `--judge pose` (default) runs `backend/models/yolov8n-pose.pt` and confirms when someone's head (nose vs ears; one ear is enough for a head in profile) points at the other person's head within `facing_angle_degrees` in at least `min_facing_fraction` of the frames; two backs to the camera give no evidence and are rejected. `--judge off` keeps proximity alone. It runs once per candidate, inline (~250 ms on CPU), and a rejected pair is re-judged every `judge_recheck_seconds` (1 s) while still close, so a pair that turns to face each other a moment late is caught. If the judge fails or finds no pose, the proximity result stands (`verdict: unverified`).

GPU: `--device cuda:0` runs the detector on the GPU (the pipeline switches to `best.pt`, since OpenVINO is CPU-only) and the judge too; `--judge-device cuda:0` moves only the judge.

## Customer/employee agent

`cust_emp_classifier.py` (`CustEmpClassifier`) weighs each factor and decides the role. Weights: appearance 0.55 (signed: `+` employee, `-` customer), bib colour 0.30, staff-zone dwell 0.10, stationary 0.05; employee when the score is >= 0.45. The appearance slot goes to the camera's few-shot references when it is calibrated, else to the YOLO role model, else to bib colour (a missing factor hands its weight down the chain `reference → yolo → bib_colour`). Per frame the score is smoothed; per person the agent averages each factor over every observed frame and makes a final decision.

## Another store (generalisation)

`best.pt` and the yellow-bib range only know our training store. A new store or camera needs settings and a few labels, not retraining:

1. **Settings file.** `--config store-cam1.json` loads any `InteractionConfig` field, e.g. `{"bib_hsv_lower": [0, 120, 70], "bib_hsv_upper": [10, 255, 255], "staff_zones": [[0, 0, 0.25, 1]], "role_weights": {"bib_colour": 0}, "employee_score_threshold": 0.5}`. Unknown keys are an error. The benchmark takes the same file per video (`"config": "path.json"`).
2. **Few-shot calibration.** Run the CLI once on that camera, read the track IDs off the annotated video, then `python -m backend.interaction.calibrate out.people.json --employee 3 7 --customer 1 2 --config store-cam1.json`. Each labelled track's mean torso descriptor (`appearance` in `people.json`) becomes a reference; a person is scored by their nearest employee vs nearest customer reference, so several uniforms or varied customers still work. Label at least two tracks per role, and repeat with more runs (other shifts, lighting) to add references. Once both roles have references, the `reference` factor replaces the YOLO role model for that camera; to blend both, set `role_weights`, e.g. `{"reference": 0.3, "yolo": 0.25}`.
3. **Abstain.** `role_unknown_band` (e.g. `0.1`) labels scores within threshold ± band `unknown` instead of guessing; unknown people never form interactions and are counted as `unknown_count`.
4. **Measure.** Add `"roles": {"<track_id>": "employee" | "customer"}` to a benchmark video (IDs from a reviewed run with the same settings). The report gives per-role precision/recall, accuracy and the unknown rate; run the same clips with and without the calibrated config to show the gain.

## Output

The CLI writes an annotated video, `<output>.detections.json` (every processed frame: ByteTrack ID, bbox, detection confidence, per-frame role and factor evidence), `<output>.people.json` (one entry per ByteTrack ID: factors, weighted contributions, score, final role), `<output>.interactions.json` (one record per confirmed interaction: employee and customer ByteTrack IDs, start, last seen, duration, distance in body heights, the body part it was measured by, active state and the judge's `verdict`) and `<output>.rejected_interactions.json` (candidates the judge vetoed). Each detections frame also carries `interaction_active`, the flag shown on screen as INTERACTION: ON/OFF. Pixel distances must be calibrated per camera before treating them as physical distance.

## Optional service

For experimentation only, run the isolated service with:

```powershell
uvicorn backend.interaction.service:app --port 8012
```

It accepts `POST /frame` with `image_base64` and an optional `timestamp`.

## Live camera (laptop or phone)

WSL2 cannot see webcams, so live mode runs on Windows Python. Install a phone-webcam app (DroidCam, Iriun or Camo) on the phone and its Windows client; it shows up as an extra webcam (usually index `1`) or, for DroidCam, also as a stream URL `http://<phone-ip>:4747/video`. Then:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run-interaction-live.ps1 -Camera laptop -PhoneCam 1
```

The first run creates `.venv-win` and installs `requirements-cv.txt`. In the preview window press `s` to switch between the laptop and phone camera (if the other camera cannot be opened, the feed stays where it is) and `q` to stop; outputs go to `backend\output\live-<time>.*`, plus `live-<time>.raw.mp4` with every unprocessed camera frame. Frames are read on a background thread that keeps only the newest, so a slow pipeline skips frames instead of lagging (and the phone does not report dropped frames). Live timestamps come from the wall clock, not the camera's nominal FPS. Directly: `python -m backend.interaction.cli --live phone --phone-cam http://<phone-ip>:4747/video`.

From WSL, DroidCam works over Wi-Fi without the Windows client (close it first; the phone serves one viewer): `scripts/run-interaction.sh live <phone-ip>`. Camera switching is unavailable there, since WSL has no laptop webcam.

From the web app: `npm run dev`, open **Interactions**, pick **Live DroidCam**, enter the phone IP shown in DroidCam (port `4747`) and press **Start Live Analysis**. The page plays the camera live (MJPEG, ~15 fps) with the latest detections drawn on it; boxes update as fast as the model runs; **Stop** ends the run and lists the people and interactions. Outputs go to `backend/output/interaction-runs/live-<time>-<id>/`. This runs `cli.py --live phone --stop-file ...`, which skips the preview window and stops when that file appears.
