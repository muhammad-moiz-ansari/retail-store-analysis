# Mid-iteration report evidence, 20 October 2026

`verification_20261020.json` contains the 15 retained in-scope local HTTP assertions and the earlier corrected-scope unit-test result. One assertion checks the absent PDF report route; this is not a passed feature test. The original broader execution records are retained outside the report in the ignored local execution directory.

## Unit tests (rerun 20 October 2026, after the interaction-judge port)

All interaction suites: **44 passed in 1.72 seconds** (engagement 8, customer/employee classifier 4, role classifier 5, identity 4, tracker 5, pose judge 7, benchmark 3, streaming frame processor 8). Camera-handoff core: **5 passed**. Run from the repository root with the virtual environment:

```
python -m pytest backend/interaction -q
PYTHONPATH=backend python -m pytest backend/test_handoff_core.py -q
```

`unit_tests_20261020.txt` records the earlier 24-test run of the five original suites.

## Benchmark and batch run

- `benchmark_20261020.json`: output of `python -m backend.interaction.benchmark backend/interaction/benchmarks/benchmark.json` on a CPU-only laptop (every 10th frame scored and tracked). Detector KPIs on the 455-image held-out split; interaction precision/recall on the one labelled clip (IMG_8829), for proximity alone and with the pose judge; per-clip speed and the candidates found on all 11 clips.
- `interaction_judge_batch_20261020.csv`: per-clip results of the interaction CLI with the pose judge on 11 local clips (`--every 10 --track-every 3`): candidates, confirmed and rejected interactions with start time, duration and body band.

The ten clips other than IMG_8829 are not labelled; their counts are pipeline outputs, not accuracy.

## Other

Representative UI screenshots show demonstration data rather than measured vision accuracy. Role navigation remains partial. The earlier development server exhausted a 768 MB Node heap and was restarted at 2048 MB. Authentication checks used isolated local databases; credentials, cookies, databases and raw video are excluded from this folder.

Historical floor-distance results refer to commit `4a9023a`, before source removal in `8c3a6fe`. The inspected code snapshot was `feature/interaction` at `6560403`.
