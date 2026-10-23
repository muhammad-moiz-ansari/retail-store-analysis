# Live interaction feed. Runs on Windows because WSL2 cannot see USB/virtual webcams.
# From PowerShell, in the repo (\\wsl$\... path works):
#   powershell -ExecutionPolicy Bypass -File scripts\run-interaction-live.ps1                  # laptop webcam
#   powershell -ExecutionPolicy Bypass -File scripts\run-interaction-live.ps1 -Camera phone
#   ... -PhoneCam http://192.168.1.20:4747/video                                           # phone app's stream URL
# In the preview window: s switches laptop <-> phone, q stops and writes backend\output\live-<time>.* (+ .raw.mp4)
param(
  [ValidateSet("laptop", "phone")][string]$Camera = "laptop",
  [string]$LaptopCam = "0",
  [string]$PhoneCam = "1",  # index of the virtual webcam the phone app (DroidCam/Iriun/Camo) installs
  [string]$Device = "cpu"
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot)
$py = ".venv-win\Scripts\python.exe"
if (-not (Test-Path $py)) {
  py -m venv .venv-win
  & $py -m pip install -r backend\interaction\requirements-cv.txt
}
New-Item -ItemType Directory -Force backend\output | Out-Null
& $py -m backend.interaction.cli --live $Camera --laptop-cam $LaptopCam --phone-cam $PhoneCam `
  --device $Device --track-every 1 --every 3 --output "backend\output\live-$(Get-Date -Format yyyyMMdd-HHmmss).mp4"
