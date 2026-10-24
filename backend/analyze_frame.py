#!/usr/bin/env python3
"""Analyze a single frame for people detection via YOLO.

Reads base64-encoded JPEG from stdin, runs YOLOv8n person detection,
and outputs JSON with bounding boxes, employee/customer classification,
and interaction analysis.

Usage:
    echo '<base64>' | python analyze_frame.py [aisle_id]
"""

import base64
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from device import DEVICE

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "backend" / "yolov8n.pt"

_model = None


def get_model():
    global _model
    if _model is None:
        _model = YOLO(str(MODEL_PATH))
    return _model


def classify_people(boxes, frame_h, frame_w):
    """Classify detected people as employee or customer using position heuristics.

    Heuristic: people standing still near edges/counters are likely employees.
    Since we only get a single frame, we use vertical position:
      - Bottom 40% of frame (close to camera) = customer
      - Top 60% of frame (further back, near shelves/counters) = employee
    This is a reasonable default for retail aisle cameras.
    """
    employees = []
    customers = []

    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        conf = float(box.conf[0])
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        w = x2 - x1
        h = y2 - y1
        area = w * h

        person = {
            "bbox": [x1, y1, x2, y2],
            "center": [int(cx), int(cy)],
            "size": [w, h],
            "area": area,
            "confidence": round(conf, 3),
        }

        # Vertical position heuristic: bottom 40% = customer, top 60% = employee
        rel_y = cy / frame_h if frame_h > 0 else 0.5
        if rel_y > 0.6:
            customers.append(person)
        else:
            employees.append(person)

    return employees, customers


def analyze_interaction(employees, customers):
    """Analyze employee-customer interaction quality."""
    n_emp = len(employees)
    n_cust = len(customers)

    if n_emp == 0 and n_cust == 0:
        return {
            "status": "empty",
            "message": "No people detected",
            "score": 0,
        }

    if n_emp == 0 and n_cust > 0:
        return {
            "status": "unattended",
            "message": f"{n_cust} customer(s) with no staff present",
            "score": 0,
        }

    if n_cust == 0 and n_emp > 0:
        return {
            "status": "idle",
            "message": f"{n_emp} employee(s) with no customers",
            "score": 30,
        }

    # Both present - check proximity and ratio
    ratio = n_cust / n_emp if n_emp > 0 else float("inf")

    # Check if any employee is close to a customer (proximity = interaction)
    interacting = 0
    for emp in employees:
        for cust in customers:
            dx = emp["center"][0] - cust["center"][0]
            dy = emp["center"][1] - cust["center"][1]
            dist = (dx**2 + dy**2) ** 0.5
            if dist < 150:  # within 150px = interacting
                interacting += 1
                break

    # Score: based on ratio and interaction
    if ratio <= 3:
        ratio_score = 100
    elif ratio <= 5:
        ratio_score = 70
    elif ratio <= 8:
        ratio_score = 40
    else:
        ratio_score = 10

    interaction_pct = (interacting / n_emp * 100) if n_emp > 0 else 0
    score = int(ratio_score * 0.5 + interaction_pct * 0.5)

    if ratio > 5:
        status = "overwhelmed"
        message = f"Too many customers per employee ({ratio:.1f}:1)"
    elif interacting == 0:
        status = "not_interacting"
        message = f"{n_emp} employee(s) present but none near customers"
    elif interaction_pct >= 80:
        status = "good"
        message = f"Employees actively engaging customers ({interacting}/{n_emp})"
    else:
        status = "partial"
        message = f"{interacting}/{n_emp} employees near customers"

    return {
        "status": status,
        "message": message,
        "score": score,
        "employee_count": n_emp,
        "customer_count": n_cust,
        "ratio": round(ratio, 2),
        "interacting_count": interacting,
    }


def main():
    aisle_id = sys.argv[1] if len(sys.argv) > 1 else "aisle"

    # Read base64 from stdin
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"error": "No frame data"}))
        sys.exit(1)

    # Decode
    try:
        img_bytes = base64.b64decode(raw)
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception as e:
        print(json.dumps({"error": f"Decode failed: {e}"}))
        sys.exit(1)

    if frame is None:
        print(json.dumps({"error": "Invalid image"}))
        sys.exit(1)

    h, w = frame.shape[:2]

    # Run YOLO
    model = get_model()
    results = model(frame, verbose=False, classes=[0], device=DEVICE)

    boxes = []
    for r in results:
        for box in r.boxes:
            boxes.append(box)

    employees, customers = classify_people(boxes, h, w)
    interaction = analyze_interaction(employees, customers)

    output = {
        "aisle": aisle_id,
        "frame_size": [w, h],
        "total_people": len(employees) + len(customers),
        "employees": employees,
        "employee_count": len(employees),
        "customers": customers,
        "customer_count": len(customers),
        "interaction": interaction,
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
