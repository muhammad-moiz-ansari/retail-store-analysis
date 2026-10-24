#!/usr/bin/env bash
# Run the interaction pipeline on one video, or on every video in dummydataset/.
#   scripts/run-interaction.sh path/to/video.mp4   -> backend/output/<name>.*
#   scripts/run-interaction.sh                     -> dummyoutputs/interaction/<name>.*
#   scripts/run-interaction.sh live <phone-ip>     -> live DroidCam feed, backend/output/live-<time>.*
# Extra CLI flags go in CLI_ARGS, e.g. CLI_ARGS="--judge off" scripts/run-interaction.sh
set -uo pipefail
cd "$(dirname "$0")/.."

# CPU by default: the installed torch has no kernels for the MX230 (sm_61).
DEVICE=${DEVICE:-cpu}
PY=${PY:-.venv/bin/python}

run() {  # run <video> <output-dir>
  local name; name=$(basename "${1%.*}"); name=${name#Copy of }
  mkdir -p "$2"
  echo "==> $1"
  "$PY" -m backend.interaction.cli "$1" --track-every 3 --every 15 --device "$DEVICE" \
    --output "$2/$name.mp4" ${CLI_ARGS:-}
}

if [[ ${1:-} == live ]]; then
  # DroidCam over Wi-Fi: WSL2 has no webcams, but can reach the phone's stream. Close the DroidCam PC client
  # first, since the phone serves one viewer at a time. s/q in the preview window; output in backend/output/live-<time>.* (+ .raw.mp4)
  [[ -n ${2:-} ]] || { echo "usage: $0 live <phone-ip shown in DroidCam>" >&2; exit 1; }
  mkdir -p backend/output
  exec "$PY" -m backend.interaction.cli --live phone --phone-cam "http://$2:${PORT:-4747}/video" \
    --device "$DEVICE" --track-every 1 --every 3 --output "backend/output/live-$(date +%Y%m%d-%H%M%S).mp4" ${CLI_ARGS:-}
fi

if [[ $# -gt 0 ]]; then
  [[ -f $1 ]] || { echo "No such video: $1" >&2; exit 1; }
  run "$1" backend/output
  exit
fi

failed=0
shopt -s nullglob nocaseglob
for f in dummydataset/*.{mov,mp4}; do
  run "$f" dummyoutputs/interaction || { echo "FAILED: $f" >&2; failed=$((failed + 1)); }
done
echo "done, $failed failed"
[[ $failed -eq 0 ]]
