#!/usr/bin/env bash
# Rerun both interaction benchmarks with the fitted role weights (B6 freeze input), then the 95% intervals.
# Needs the clips named in the two specs (dummydataset/ and dummyoutputs/square_640/, not in Git) and the CV
# requirements (backend/requirements.txt). Run on an otherwise idle machine: the speed figure is part of the report.
#   scripts/rerun-benchmarks.sh            # both sets
#   PYTHON=python3 scripts/rerun-benchmarks.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-./.venv/bin/python}"
B=backend/interaction/benchmarks
STAMP="$(date -u +%Y%m%d)"

missing=$("$PYTHON" - <<'PY'
import json
from pathlib import Path
for spec in ("benchmark.json", "benchmark_set_b.json"):
    data = json.loads(Path("backend/interaction/benchmarks", spec).read_text())
    for video in data["videos"] if isinstance(data, dict) else data:
        if not Path(video["path"]).exists():
            print(video["path"])
PY
)
if [ -n "$missing" ]; then
  echo "Clips missing; copy them in before running:" >&2
  echo "$missing" >&2
  exit 1
fi

for set in "benchmark:11_fitted" "benchmark_set_b:set_b_fitted"; do
  spec="${set%%:*}"; name="${set##*:}"
  report="$B/report_${name}_${STAMP}.json"
  "$PYTHON" -m backend.interaction.benchmark "$B/$spec.json" --output "$report" --label "${name}_${STAMP}"
  "$PYTHON" -m backend.interaction.confidence "$report" | tee "$B/confidence_${name}_${STAMP}.txt"
  echo "wrote $report"
done
echo "Commit: $(git rev-parse HEAD). Record it with the report names in docs/fyp2-plan/MODELS.md and CV_EVAL_CHAPTER.md."
