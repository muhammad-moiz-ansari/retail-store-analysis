# Evaluation Plan (Step 4)

## Current decision — 11 November 2026

The [combined team plan](RetailPulse_FYP2_Implementation_Plan.md) governs current work and ownership. Implement camera/CV first, then register the supplied map, then render live role occupancy and confirmed-interaction layers. Exactly four dynamic occupancy categories are allowed: **Customer, Employee, Customer–employee both, No one**. They are not fixed permitted-role polygons. Invalid/missing/unknown observation is separate quality metadata, never a fifth category or a false No one. Historical z1–z6, staff zones, queue/counter geometries and hot/gray terminology below are legacy technical references, not additional category requirements. No existing runtime/schema/fixture has been migrated by this documentation update.

Current inventory supersedes the original one-clip snapshot: 11 tuning clips and 14 set-B clips exist. Local reports support F1 0.867 tuned and 0.462 set B; set B was viewed once during tuning. Role refit results on Saqib's other branch are reported, not locally verified. Audit 9 locally listed versus 10 reported set-B pass-bys; retain blind rechecks, second annotation, clean timing and map-specific ground truth as pending. The older procedures below remain reference instructions, not a current label-completeness claim.

## Labelling

1. Follow `backend/interaction/ANNOTATION_GUIDE.md`.
2. One spec per clip, shaped like `backend/interaction/evaluation_spec.example.json`:
   interaction intervals (`start`, `end`), and include close pass-bys that are **not** assistance.
3. For Step 1 metrics, also note per clip: footfall in/out (if an entrance is visible),
   and any customer who clearly waited unattended (start/end seconds).

## Running

```bash
python -m backend.interaction.benchmark <spec.json> --output backend/interaction/benchmarks/<clip>.json
python -m backend.interaction.benchmark <spec.json> --judge off --output backend/interaction/benchmarks/<clip>.nojudge.json
```

`benchmark.py` already reports with-judge and without-judge matching by interval IoU.

## What goes in the final report

| Metric | Source |
|---|---|
| Interaction precision / recall / F1, with vs without pose judge, per clip and pooled | `benchmark.py` |
| Pass-by rejection rate (labelled pass-bys correctly dropped) | `benchmark.py` candidates vs spec |
| Role accuracy per track (employee/customer) | `people.json` vs labels |
| Footfall error (counted vs labelled) | `summary.json` vs labels |
| Unattended-event precision / recall | `summary.json` vs labels |
| Identity switches (a labelled person split into several tracks) | `people.json` `role_segments` + manual count |
| CPU throughput (× realtime, fps) per clip, with `--track-every 1` and `3` | CLI prints `processed Xs of video in Ys` |

Write the results into `backend/interaction/benchmarks/` next to the existing `report.json`, and
add an error-analysis paragraph per failure type (occlusion, ID switch, wrong role, pass-by).

## Done when

- All 11 clips have specs.
- Pooled precision/recall are reported with and without the judge.
- CPU throughput is recorded for every clip on the demo laptop.
