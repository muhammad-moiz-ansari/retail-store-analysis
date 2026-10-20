# GPU switch and VLM removal: session notes

## 1. One-line GPU mode

All model inference now reads its device from one switch in `backend/device.py`:

```python
USE_GPU = False  # set True on a CUDA machine (e.g. RTX 5060 laptop)
```

Set it to `True` and every model runs on `cuda:0`. Before this change, `"cpu"` was hard-coded in about 8 places.

**What uses it:** `analyze_frame.py`, `compare_people.py`, `vision_inference.py` (camera handoff tracking), and in `interaction/`: `models.py` (detector and pose), `config.py` (`InteractionConfig.device`) and `cli.py` (the `--device` default). The CLI's `--device` flag still overrides it for a single run.

**Left on CPU on purpose:** the MobileNet embedder in `interaction/models.py`. It runs on one crop at a time, so copying each crop to the GPU and back would probably cost more time than it saves.

### Setting up the RTX 5060 laptop

- The card needs a PyTorch build with CUDA 12.8 or newer:
  `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128`
- On WSL2, install the NVIDIA driver on the Windows side only, not inside Linux.
- If `USE_GPU = True` and CUDA isn't working, model calls raise an error. They don't fall back to CPU.

## 2. Expected GPU performance (estimates, not measured)

| Part | CPU now (2 threads) | RTX 5060 laptop (guess) |
|---|---|---|
| YOLOv8n detect/track at 960px | ~150–250 ms per frame | ~8–15 ms |
| Pose model | about the same as detect | ~10–20 ms |

- The models themselves: roughly **10–20× faster**.
- The whole pipeline: more like **3–8× faster**. Once the models are fast, the slow parts become the work that stays on the CPU: video decoding, ByteTrack, the embedder, drawing boxes and writing the output video. A rough guess for the interaction CLI on 1080p video is 20–40 fps.
- `analyze_frame` may get **slower**. The frontend starts a new Python process for each request, and setting up CUDA plus loading the model takes about 1–3 s each time.
- The first frame of each run is slow while the GPU warms up. On long runs, laptop thermals may throttle the GPU.

**Easy gains for later (not done):**
- Add `half=True` to the YOLO calls for 16-bit inference, usually another 1.5–2×.
- Keep `analyze_frame`'s model loaded in a long-running process instead of starting a new one per request.
- Move the embedder to the GPU and process each frame's crops as one batch, if profiling shows it's the bottleneck.

**How to measure:** run the interaction CLI on the same clip with `--device cpu` and with `--device cuda:0`, and compare the timings it prints.

## 3. VLM removed: the pipeline is YOLO only

The SmolVLM2 classifier was never used by the running app. The pipeline always used `NullVLM`, which answers "unknown", and only a standalone smoke test created the real model. Role classification comes from registered identities plus the YOLO role model (`--roles`).

**Removed:**
- `backend/interaction/vlm.py` and `requirements-vlm.txt` (`transformers` is no longer a dependency).
- The `vlm_runtime/` folder, including its 1.3 GB local `.venv`.
- The `vlm_role_*` and `vlm_interaction_*` settings from `CameraConfig` (`schemas.py`).
- The `vlm_role_confidence` and `vlm_role_evidence` fields from `TrackObservation` (`cv_contracts.py`).
- The VLM steps in `pipeline.py` and `core.py`, including the `interaction_classifier` hook in `EventEngine`.
- The VLM test in `test_task_a.py`.
- The VLM stages in the `interaction.md` pipeline diagram (it now has 6 stages).

**Risk:** `CameraConfig` rejects fields it doesn't recognise (`extra="forbid"`). Any saved config, database row or API caller that still sends a `vlm_*` field will fail validation. None were found in the repo, but stored data outside it wasn't checked.

**Possible future use:** if the YOLO role model leaves a lot of people as "unknown" on real footage, a VLM could come back as a fallback. It would be practical to run on the GPU.

## 4. Verification

- All backend modules import correctly both ways the backend is run (`backend.*` package and flat scripts).
- `InteractionConfig().device` defaults to `cpu`.
- The 12 interaction tests pass when run from the repo root:
  `python -m unittest discover -s backend/interaction -t .`
- Running the tests from inside `backend/` shows 2 errors in `test_task_a` and `test_tracker`. Both are relative-import errors from running in that folder, and both also appear with these changes stashed.
- Nothing has been tested on a real GPU yet.
