# Isolated VLM runtime

This folder is separate from the main application environment. It contains a
CPU PyTorch environment and the SmolVLM2 adapter used by the interaction
pipeline.

The first run downloads the model into `hf_cache/`. On this laptop, one-frame
CPU inference is expected to be slow; use a GPU machine for processing all
eight feeds. A bounded smoke test is:

```bash
PYTHONPATH=. HF_HOME=vlm_runtime/hf_cache \
  vlm_runtime/.venv/bin/python vlm_runtime/run_smoke.py backend/videos/cam1.mp4
```
