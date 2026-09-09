"""Unified local backend entry point for POS and camera analytics."""

from fastapi import FastAPI

from .camera_service import app as camera_app
from .pos_service import app as pos_app

app = FastAPI(title="RetailPulse Backend", version="0.1.0")
app.mount("/camera", camera_app)
app.mount("/pos", pos_app)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
