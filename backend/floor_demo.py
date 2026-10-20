import itertools
import json

import cv2

from .floor_calibration import map_canvas, reference_frame
from .floor_geometry import inside, pair_distance, position, project, validate_runtime
from .floor_motion import MotionMonitor
from .floor_tracking import PositionSmoother
from .floor_video import draw_detections, open_video, video_frames, writer
from .vision_inference import PersonDetector


def run(args):
    if args.sample_every < 1 or args.max_frames < 0 or not 0 < args.confidence <= 1:
        raise ValueError("Invalid frame sampling/confidence settings")
    cfg = json.loads(args.calibration.read_text(encoding="utf-8"))
    cap, fps, size = open_video(args.video)
    outputs = []
    processed, accepted, total, pairs_supported = 0, 0, 0, 0
    status_counts, motion_counts = {}, {}
    try:
        validate_runtime(cfg, size)
        # The calibration is bound to the selected video. Reusing it for another camera is unsafe.
        from pathlib import Path
        if Path(cfg["source_reference"]).resolve() != args.video.resolve():
            raise ValueError("Calibration belongs to another source video; create/verify a new calibration")
        reference, _, _ = reference_frame(args.video, cfg["reference_timestamp_s"])
        detector = PersonDetector(args.model, args.confidence)
        monitor = MotionMonitor(reference, cfg, detector(reference))
        smoother = PositionSmoother(**cfg.get("smoothing", {}))
        floor_region = [project(cfg["H_image_to_floor"], p) for p in cfg["operational_region_px"]]
        args.output_dir.mkdir(parents=True, exist_ok=True)
        canvas, to_canvas = map_canvas(cfg, args.pixels_per_metre)
        main_out = writer(args.output_dir / "distance.mp4", fps / args.sample_every, size)
        outputs.append(main_out)
        map_size = [canvas.shape[1] + canvas.shape[1] % 2, canvas.shape[0] + canvas.shape[0] % 2]
        map_out = writer(args.output_dir / "top_down.mp4", fps / args.sample_every, map_size)
        outputs.append(map_out)
        with (args.output_dir / "metrics.jsonl").open("w", encoding="utf-8") as stream:
            for index, ts, frame in video_frames(cap, fps, args.sample_every, args.max_frames):
                detections = detector(frame)
                if index == cfg["reference_frame_index"]:
                    motion = {"status": "reference_frame", "reason": "same_calibrated_frame", "compensated": False}
                elif args.motion_mode == "snapshot":
                    motion = {"status": "motion_invalid", "reason": "snapshot_only_supports_reference_frame", "compensated": False}
                else:
                    motion = monitor.check(frame, detections)
                motion_counts[motion["status"]] = motion_counts.get(motion["status"], 0) + 1
                records = []
                for d in detections:
                    record = {**d, **position(d, cfg, size, motion["status"], detections),
                              "camera_id": cfg["camera_id"], "timestamp_s": ts}
                    records.append(record)
                aligned = motion["status"] in {"reference_frame", "aligned_provisional"}
                if not aligned:
                    smoother.states.clear()
                predictions = smoother.update(records, ts, allow_predictions=aligned)
                for predicted in predictions:
                    if not inside(predicted["floor_xy_m"], floor_region):
                        predicted.update(status="out_of_region", floor_xy_m=None,
                                         reason="prediction_outside_calibrated_coverage", position_reliability="unsupported")
                distances = []
                # Missing/unsupported selected tracks still produce an explicit unavailable record.
                if args.pair:
                    by_id = {r["track_id"]: r for r in records + predictions}
                    left, right = args.pair
                    if left in by_id and right in by_id:
                        distances.append({"track_ids": [left, right], **pair_distance(by_id[left], by_id[right])})
                    else:
                        distances.append({"track_ids": [left, right], "distance_m": None,
                                          "status": "unavailable", "reason": "selected_track_missing", "approximate": True})
                else:
                    # Modest scenes only. Cap output to avoid quadratic growth in crowded footage.
                    for a, b in itertools.islice(itertools.combinations(records, 2), 100):
                        distances.append({"track_ids": [a["track_id"], b["track_id"]], **pair_distance(a, b)})
                for record in records:
                    status_counts[record["status"]] = status_counts.get(record["status"], 0) + 1
                    total += 1
                    accepted += record["status"] == "observed_proxy"
                pairs_supported += sum(d["distance_m"] is not None for d in distances)
                stream.write(json.dumps({"frame_index": index, "timestamp_s": ts, "camera_id": cfg["camera_id"],
                                         "calibration_id": cfg["calibration_id"], "calibration_status": cfg["calibration_status"],
                                         "approximate": True, "motion": motion, "positions": records,
                                         "predictions": predictions, "distances": distances}, allow_nan=False) + "\n")
                image = draw_detections(frame.copy(), detections)
                cv2.putText(image, "PROVISIONAL - distances approximate", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 220, 255), 2)
                cv2.putText(image, f'{ts:.2f}s {cfg["calibration_id"]} {motion["status"]}', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 220, 255), 2)
                for row, record in enumerate(records):
                    cv2.putText(image, f'ID:{record["track_id"]} {record["status"]}: {record["reason"] or "bbox proxy"}',
                                (10, 90 + row * 22), cv2.FONT_HERSHEY_SIMPLEX, .5, (230, 230, 230), 1)
                for row, d in enumerate(distances[:8]):
                    value = f'~{d["distance_m"]:.2f} m' if d["distance_m"] is not None else f'unavailable ({d["reason"]})'
                    cv2.putText(image, f'{d["track_ids"]}: {value}', (10, size[1] - 20 - row * 24), cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 220, 255), 2)
                top = canvas.copy()
                cv2.putText(top, f'{ts:.2f}s {motion["status"]}', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, .4, (200, 200, 200), 1)
                for r in records + predictions:
                    if r["floor_xy_m"] is not None:
                        p = to_canvas(r.get("smoothed_xy_m", r["floor_xy_m"]))
                        color = (60, 200, 80) if r["role"] == "employee" else (255, 180, 50)
                        cv2.circle(top, p, 5, color, 1 if r["status"] == "predicted" else -1)
                        cv2.putText(top, str(r["track_id"]), p, cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1)
                top = cv2.copyMakeBorder(top, 0, map_size[1] - top.shape[0], 0, map_size[0] - top.shape[1], cv2.BORDER_CONSTANT)
                main_out.write(image)
                map_out.write(top)
                if processed == 0:
                    cv2.imwrite(str(args.output_dir / "distance.jpg"), image)
                    cv2.imwrite(str(args.output_dir / "top_down.jpg"), top)
                processed += 1
                if processed % 100 == 0:
                    stream.flush()
                    print(f"Distance demo: {processed} frames; video time {ts:.2f}s", flush=True)
                if not args.headless:
                    cv2.imshow("Approximate floor distances", image)
                    cv2.imshow("Floor map", top)
                    if cv2.waitKey(1) & 255 == 27:
                        break
        summary = {"processed_frames": processed, "detections": total, "accepted_positions": accepted,
                   "accepted_position_coverage": accepted / total if total else None,
                   "rejection_rate": 1 - accepted / total if total else None, "position_status_counts": status_counts,
                   "motion_status_counts": motion_counts, "supported_approximate_pairs": pairs_supported,
                   "calibration_status": cfg["calibration_status"], "physical_validation": "pending",
                   "model": str(args.model), "sample_every": args.sample_every}
        (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary))
    finally:
        cap.release()
        for output in outputs:
            output.release()
        if not args.headless:
            cv2.destroyAllWindows()
