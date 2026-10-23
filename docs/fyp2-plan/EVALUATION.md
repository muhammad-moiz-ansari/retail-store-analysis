# Evaluation Plan (Step 4)

The report's weakest claim: interaction accuracy comes from **one** labelled clip. Ten local clips
are waiting for labels. Labelling them needs no code.

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
