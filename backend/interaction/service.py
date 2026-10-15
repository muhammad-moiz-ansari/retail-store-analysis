"""Optional isolated FastAPI application for one-frame interaction inference."""

from __future__ import annotations

import base64

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException

from .pipeline import InteractionPipeline

app = FastAPI(title="RetailPulse Interaction Analytics", version="0.1.0")
_pipeline: InteractionPipeline | None = None


def get_pipeline() -> InteractionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = InteractionPipeline()
    return _pipeline


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "interaction"}


@app.post("/frame")
def analyse_frame(body: dict) -> dict:
    encoded = body.get("image_base64")
    if not isinstance(encoded, str):
        raise HTTPException(status_code=400, detail="image_base64 is required")
    try:
        image = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), np.uint8), cv2.IMREAD_COLOR)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image") from exc
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image")
    return get_pipeline().process_frame(image, body.get("timestamp"))
