"""Two-aisle relay, offline CV pass. Thin wrapper over backend.aisle_relay_cv, the same pipeline the app runs live:
each split-screen frame goes through YOLO once and the detections are split into Aisle 1 (left) and Aisle 2 (right).

Outputs (in --out):
  trace.json      per-sample aisle counts, every track, and every watcher signal with its reason
                  (the app can replay it: /manager/aisle-relay, source "Replay recorded pass")
  annotated.webm  both aisles with boxes, roles and the agent's state

Usage: python scripts/aisle_relay_demo.py backend/videos/multirow.mp4 --out dummyoutputs/multirow
       add --dispatch to send each signal to the store database (DATABASE_URL) while the CV runs,
       --realtime to pace it like a live camera.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.aisle_relay_cv import main  # noqa: E402

if __name__ == "__main__":
    main()
