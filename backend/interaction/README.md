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
python -m backend.interaction.cli path\to\footage.mp4 --roles path\to\best.pt --output interaction.mp4
```

Without `--roles`, classification falls back to the configured yellow-bib HSV range. Update `bib_hsv_lower` and `bib_hsv_upper` in an `InteractionConfig` instance to match the real bib colour and lighting.

## Output

The CLI writes an annotated video plus a JSON file. Each JSON interaction includes employee and customer ByteTrack IDs, duration, image-plane distance, and active state. Pixel distances must be calibrated per camera before treating them as physical distance.

## Optional service

For experimentation only, run the isolated service with:

```powershell
uvicorn backend.interaction.service:app --port 8012
```

It accepts `POST /frame` with `image_base64` and an optional `timestamp`.
