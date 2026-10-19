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

## Customer/employee agent

`cust_emp_classifier.py` (`CustEmpClassifier`) weighs each factor and decides the role. Weights: YOLO role model 0.55 (signed: `+conf` for employee, `-conf` for customer), bib colour 0.30, staff-zone dwell 0.10, stationary 0.05; employee when the score is >= 0.45. Without a role model, the YOLO weight moves to bib colour. Per frame the score is smoothed; per person the agent averages each factor over every observed frame and makes a final decision.

## Output

The CLI writes an annotated video, `<output>.detections.json` (every processed frame: ByteTrack ID, bbox, detection confidence, per-frame role and factor evidence), `<output>.people.json` (one entry per ByteTrack ID: factors, weighted contributions, score, final role), plus a JSON file of interactions. Each JSON interaction includes employee and customer ByteTrack IDs, duration, image-plane distance, and active state. Pixel distances must be calibrated per camera before treating them as physical distance.

## Optional service

For experimentation only, run the isolated service with:

```powershell
uvicorn backend.interaction.service:app --port 8012
```

It accepts `POST /frame` with `image_base64` and an optional `timestamp`.
