"""Reference extraction, point-click UI and calibration diagnostics."""
import json
from pathlib import Path

import cv2
import numpy as np

from .floor_geometry import fit_calibration, project
from .floor_video import open_video


def reference_frame(video, timestamp):
    cap, fps, size = open_video(video)
    try:
        if not np.isfinite(timestamp) or timestamp < 0:
            raise ValueError("Timestamp must be finite and nonnegative")
        # Seek on the media time axis; nominal FPS can differ from variable-rate footage.
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ok, frame = cap.read()
        if not ok:
            raise ValueError(f"Cannot decode reference at {timestamp}s; check video duration")
        index = max(0, round(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1)
        actual_ts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if not np.isfinite(actual_ts) or actual_ts < 0:
            raise ValueError("Invalid decoded reference timestamp")
        return frame, index, actual_ts
    finally:
        cap.release()


def click_points(frame, labels):
    chosen = []
    name = "Floor landmarks: click order shown; U undo, R reset, S save, Esc cancel"
    # Display at <= 1000 px while retaining original-frame coordinates.
    scale = min(1., 1000 / max(frame.shape[:2]))
    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(chosen) < len(labels):
            chosen.append([x / scale, y / scale])
    cv2.namedWindow(name)
    cv2.setMouseCallback(name, on_mouse)
    try:
        while True:
            image = cv2.resize(frame, None, fx=scale, fy=scale)
            cv2.putText(image, "Order: " + " -> ".join(labels), (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 220, 255), 2)
            for i, xy in enumerate(chosen):
                p = tuple(round(v * scale) for v in xy)
                cv2.circle(image, p, 5, (0, 0, 255), -1)
                cv2.putText(image, f"{i+1}:{labels[i]}", p, cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 0, 255), 2)
            cv2.imshow(name, image)
            key = cv2.waitKey(30) & 255
            if key == 27:
                raise ValueError("Point selection cancelled")
            if key in (ord('u'), 8) and chosen:
                chosen.pop()
            if key == ord('r'):
                chosen.clear()
            if key == ord('s') and len(chosen) == len(labels):
                return chosen
    finally:
        cv2.destroyWindow(name)


def map_canvas(cfg, pixels_per_metre=200):
    if not 10 <= pixels_per_metre <= 1000:
        raise ValueError("Display pixels-per-metre must be between 10 and 1000")
    floor = np.asarray([project(cfg["H_image_to_floor"], p) for p in cfg["operational_region_px"]])
    lo, hi = floor.min(axis=0), floor.max(axis=0)
    size = np.ceil((hi - lo) * pixels_per_metre + [100, 150]).astype(int)
    if max(size) > 5000:
        raise ValueError("Top-down canvas too large; reduce pixels-per-metre or fix calibration")
    canvas = np.full((size[1], size[0], 3), 30, np.uint8)
    def to_canvas(xy):
        return tuple(np.round((np.asarray(xy) - lo) * pixels_per_metre + [50, 90]).astype(int))
    polygon = np.array([to_canvas(p) for p in floor], np.int32)
    cv2.polylines(canvas, [polygon], True, (130, 130, 130), 1)
    cv2.putText(canvas, "Approximate floor map (m)", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 220, 255), 1)
    return canvas, to_canvas


def diagnostics(cfg, frame, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    overlay = frame.copy()
    H_inverse = np.linalg.inv(cfg["H_image_to_floor"])
    floor = np.asarray([project(cfg["H_image_to_floor"], p) for p in cfg["operational_region_px"]])
    lo, hi = floor.min(axis=0), floor.max(axis=0)
    step = float(cfg.get("grid_step_m", .25))
    if step <= 0 or max((hi - lo) / step) > 100:
        raise ValueError("Invalid/excessive diagnostic grid spacing")
    for axis in (0, 1):
        for value in np.arange(np.ceil(lo[axis] / step) * step, hi[axis] + 1e-8, step):
            a, b = lo.copy(), hi.copy()
            a[axis] = b[axis] = value
            try:
                line = np.array([project(H_inverse, a), project(H_inverse, b)]).round().astype(int)
                cv2.line(overlay, tuple(line[0]), tuple(line[1]), (0, 180, 80), 1)
            except ValueError:
                continue
    region = np.asarray(cfg["operational_region_px"], np.int32)
    mask = np.zeros(frame.shape[:2], np.uint8)
    cv2.fillPoly(mask, [region], 255)
    overlay[mask == 0] = frame[mask == 0]
    cv2.polylines(overlay, [region], True, (0, 220, 255), 2)
    top, to_canvas = map_canvas(cfg)
    for landmark in cfg["landmarks"]:
        px = tuple(round(v) for v in landmark["image_xy_px"])
        cv2.circle(overlay, px, 6, (0, 0, 255), -1)
        cv2.putText(overlay, landmark["id"], px, cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 255), 2)
        xy = to_canvas(landmark["floor_xy_m"])
        cv2.circle(top, xy, 4, (0, 0, 255), -1)
        cv2.putText(top, landmark["id"], xy, cv2.FONT_HERSHEY_SIMPLEX, .5, (220, 220, 220), 1)
    cv2.putText(overlay, "PROVISIONAL - approximate metres; physical validation pending", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, .65, (0, 220, 255), 2)
    for filename, image in (("reference.jpg", frame), ("floor_grid.jpg", overlay), ("floor_map.jpg", top)):
        if not cv2.imwrite(str(output_dir / filename), image):
            raise ValueError(f"Cannot save {filename}")


def calibrate(args):
    template = json.loads(args.landmarks.read_text(encoding="utf-8"))
    frame, index, timestamp = reference_frame(args.video, args.timestamp)
    if template["frame_size"] != [frame.shape[1], frame.shape[0]]:
        raise ValueError("Landmark frame size differs from video; explicitly transform points first")
    if not args.headless:
        labels = [p["id"] for p in template["landmarks"]]
        selected = click_points(frame, labels)
        for landmark, xy in zip(template["landmarks"], selected):
            landmark["image_xy_px"] = xy
        # Rectangle corners already come in perimeter order in the example.
        if template.get("rectangle"):
            by_id = {p["id"]: p["image_xy_px"] for p in template["landmarks"]}
            template["operational_region_px"] = [by_id[i] for i in template["rectangle"]["corner_order"]]
    template["source_reference"] = str(args.video).replace("\\", "/")
    template["reference_frame_index"] = index
    template["reference_timestamp_s"] = timestamp
    cfg = fit_calibration(template)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cfg["reference_image"] = str(args.output.with_suffix(".reference.jpg")).replace("\\", "/")
    diagnostics(cfg, frame, args.output.parent / args.output.stem)
    cv2.imwrite(cfg["reference_image"], frame)
    args.output.write_text(json.dumps(cfg, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"calibration": str(args.output), "status": cfg["calibration_status"],
                      "derived_rectangle_m": cfg.get("derived_rectangle_m"), "fit": cfg["fit"]}))
