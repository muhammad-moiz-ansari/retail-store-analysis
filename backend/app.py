"""Unified local backend entry point for camera analytics."""

from fastapi import FastAPI

from .camera_service import app as camera_app

app = FastAPI(title="RetailPulse Backend", version="0.1.0")
app.mount("/camera", camera_app)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
