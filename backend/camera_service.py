"""Local FastAPI service for the camera handoff MVP.

The service deliberately keeps video/model work out of module import time so
health checks and API discovery work on machines without OpenCV installed.
It is intended for localhost use behind the Next.js manager session.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException

try:  # package invocation: python -m backend.camera_handoff
    from .camera_handoff import run_pipeline
except ImportError:  # script/test invocation from backend/
    from camera_handoff import run_pipeline


INTERNAL_SECRET = os.getenv("CAMERA_INTERNAL_SECRET", os.getenv("POS_INTERNAL_SECRET", "local-dev-pos-secret"))
REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(os.getenv("CAMERA_MODEL_PATH", str(REPO_ROOT / "backend" / "yolov8n.pt")))
app = FastAPI(title="RetailPulse Camera Analytics", version="0.1.0")
_jobs: dict[str, dict[str, Any]] = {}


def require_internal(x_camera_internal_secret: str | None = Header(default=None)) -> None:
    if x_camera_internal_secret != INTERNAL_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized camera service request")


def resolve_video(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(status_code=400, detail=f"{label} is required")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    else:
        path = path.resolve()
    # Keep demo processing inside the repository (prevents arbitrary file reads).
    try:
        path.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{label} must be inside the project directory") from exc
    if path.suffix.lower() not in {".mp4", ".mov", ".avi", ".mkv"}:
        raise HTTPException(status_code=400, detail=f"{label} must be a supported video file")
    if not path.is_file():
        raise HTTPException(status_code=400, detail=f"{label} does not exist")
    return path


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "camera", "jobs": len(_jobs)}


async def execute(job_id: str, body: dict[str, Any], cam1: Path, cam2: Path) -> None:
    _jobs[job_id]["status"] = "running"
    try:
        def log(message: str) -> None:
            _jobs[job_id]["logs"].append(str(message))

        result = await asyncio.to_thread(
            run_pipeline,
            cam1,
            cam2,
            MODEL_PATH,
            max(1, int(body.get("sample_every", 5))),
            max(0.0, float(body.get("min_gap", 1))),
            max(1.0, float(body.get("max_gap", 45))),
            float(body.get("cam1_boundary", 0.85)),
            float(body.get("cam2_boundary", 0.15)),
            log,
        )
        _jobs[job_id].update(status="completed", result=result)
    except Exception as exc:  # surfaced through the job API, never leaked as a traceback
        _jobs[job_id].update(status="failed", error=str(exc))


@app.post("/handoff", dependencies=[Depends(require_internal)])
async def start_handoff(body: dict[str, Any]) -> dict[str, Any]:
    cam1 = resolve_video(body.get("cam1"), "cam1")
    cam2 = resolve_video(body.get("cam2"), "cam2")
    if not MODEL_PATH.is_file():
        raise HTTPException(status_code=503, detail=f"Camera model not found: {MODEL_PATH}")
    for key, low, high in (("cam1_boundary", 0.0, 1.0), ("cam2_boundary", 0.0, 1.0)):
        try:
            value = float(body.get(key, 0.85 if key == "cam1_boundary" else 0.15))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"{key} must be numeric") from exc
        if not low <= value <= high:
            raise HTTPException(status_code=400, detail=f"{key} must be between 0 and 1")
    try:
        min_gap = float(body.get("min_gap", 1))
        max_gap = float(body.get("max_gap", 45))
        sample_every = int(body.get("sample_every", 5))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="sample_every, min_gap, and max_gap must be numeric") from exc
    if sample_every < 1 or min_gap < 0 or max_gap <= min_gap:
        raise HTTPException(status_code=400, detail="Require sample_every >= 1, min_gap >= 0, and max_gap > min_gap")
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"id": job_id, "status": "queued", "logs": [], "result": None}
    asyncio.create_task(execute(job_id, body, cam1, cam2))
    return {"id": job_id, "status": "queued"}


@app.get("/jobs/{job_id}", dependencies=[Depends(require_internal)])
def job(job_id: str) -> dict[str, Any]:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Camera job not found")
    return _jobs[job_id]
