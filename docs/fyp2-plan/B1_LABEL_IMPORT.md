# B1 Label Import: CVAT to benchmark.json

Status as of 2026-11-05. Labels are a **machine-drafted first pass**, not verified human ground truth.

## What was done
- `backend/interaction/cvat_import.py` (+ `test_cvat_import.py`) copies a CVAT "CVAT for video 1.1" export into `backend/interaction/benchmarks/benchmark.json`.
  - Matches a task to a clip when the video file stem or name appears in the CVAT task name.
  - Writes `interactions`, `pass_bys`, `people`; deletes `candidates_to_review` and the "Not labelled yet" note. Overwrites a clip's existing `interactions`.
  - CVAT labels: `interaction`, `pass_by`, `person` (rectangle tracks). Only employee-customer interactions count; employee wears the neon-green vest.
- Project "interaction-benchmark" (id 2), tasks 5-15, exported to `/tmp/cvat_export/task_{id}.xml` and imported.
- `benchmark.json` is committed. `backend/interaction` tests pass (63).

## Imported labels (interactions / pass-bys / people)
| Clip | Result |
| --- | --- |
| 8878 | 1 / 0 / 2 (21.0-33.5 s; old candidates were two spans, now merged) |
| 8880 | 1 / 0 / 2 |
| 8881 | 2 / 1 / 2 |
| 8885 | 0 / 0 / 2 (no employee; `interactions` = [], counts as labelled) |
| 8886 | 1 / 1 / 2 |
| 8890 | 2 / 0 / 2 |
| 8893 | 1 / 1 / 2 |
| 8894 | 1 / 0 / 2 |
| 8895 | 2 / 1 / 3 |
| 8897 | 1 / 0 / 3 |
| 8829 | 1 / 0 / 2 (33.0-44.0 s; escort-walk span 0-15 s dropped, see below) |

## Open issues
1. **8829 (resolved by drop, unverified).** The imported 0.0-15.0 s span contradicted the clip note (1.2-15.5 s is NOT an interaction), so it was removed; 33.0-44.0 s stays (old reviewed label 35.4-43.9 s). Not checked against the footage.
2. `roles` is unset: it is keyed by pipeline track IDs, so a benchmark run is needed first.
3. No importer test on a real exported XML (it reads fps from the video file).
4. Labels need human verification before they are cited as ground truth. A second annotator is recommended (ANNOTATION_GUIDE.md).

## Next
Run `python -m backend.interaction.benchmark` (and `--judge off`), then `python -m backend.interaction.refit`, then fill `CV_EVAL_CHAPTER.md`.

Security note: the CVAT password was pasted into a chat session; rotate it if the account is real.
