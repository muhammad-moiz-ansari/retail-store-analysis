"""/analyze-frame runs in the backend process and keeps its model loaded between requests."""

import base64
import time

import cv2
import numpy as np
from fastapi.testclient import TestClient

from backend import analyze_frame
from backend.app import INTERNAL_SECRET, app

MANAGER = {"x-retailpulse-internal-secret": INTERNAL_SECRET, "x-retailpulse-role": "Manager"}


def test_model_loads_once_and_bad_input_is_400():
    client = TestClient(app)
    _, jpg = cv2.imencode(".jpg", np.full((240, 320, 3), 127, np.uint8))
    body = {"image_base64": base64.b64encode(jpg.tobytes()).decode(), "aisle": "a1"}
    first = client.post("/analyze-frame", json=body, headers=MANAGER)
    assert first.status_code == 200, first.text
    model = analyze_frame._model
    started = time.perf_counter()
    second = client.post("/analyze-frame", json=body, headers=MANAGER)
    assert second.json()["frame_size"] == [320, 240]
    assert analyze_frame._model is model  # same loaded model, no new process
    assert time.perf_counter() - started < 5
    assert client.post("/analyze-frame", json={"image_base64": "bm90IGFuIGltYWdl"}, headers=MANAGER).status_code == 400
