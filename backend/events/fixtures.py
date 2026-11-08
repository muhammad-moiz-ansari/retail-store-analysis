"""Synthetic day of events in schema v1, so tools, agents and the UI can be built before real CV output exists.

One store, 3 cameras, 6 zones (store_core's seeded ids), 09:00-21:00 UTC, seeded so every run is identical.
Planted patterns for the agents to find:
- a 17:00-19:00 rush (3x arrivals, longer queues);
- z3 (Aisle 2 - Beverages) is understaffed: its employee only drops by, so its customers wait unattended;
- c2 (aisle camera) is blocked 14:00-14:40: frozen_or_dark = 1 and no detections, so the aisles look empty.

python -m backend.events.fixtures [--db backend/events/fixture.sqlite3]
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .ingest import connect, delete_run, derive_unattended, insert, validate

RUN_ID = "fixture-2026-11-03"
STORE = "store-1"
OPEN = datetime(2026, 11, 3, 9, tzinfo=timezone.utc)
MINUTES = 12 * 60
HOME_ZONE = {"c1": "z1", "c2": "z2", "c3": "z6"}  # store_core's seeded camera zones
CAMERA_OF = {"z1": "c1", "z5": "c1", "z2": "c2", "z3": "c2", "z4": "c2", "z6": "c3"}
STAFF = {"z1": 1, "z2": 1, "z4": 1, "z6": 2}  # z3 has none on its own; z5 (promo) needs none
RUSH = (17 * 60 - 9 * 60, 19 * 60 - 9 * 60)  # minutes after opening
BLOCKED = ("c2", 5 * 60, 5 * 60 + 40)  # camera, from, to (minutes after opening)
DEFAULT_DB = Path(__file__).with_name("fixture.sqlite3")


def generate(conn, seed: int = 7, unattended_after_s: float = 180.0) -> dict:
    rnd = random.Random(seed)
    at = lambda minute: (OPEN + timedelta(minutes=minute)).isoformat()
    rows: dict[str, list[dict]] = {t: [] for t in ("tracks", "role_decisions", "interactions", "zone_dwell", "footfall",
                                                   "queue_samples", "pipeline_health", "heatmaps")}
    next_id = {c: 0 for c in ("c1", "c2", "c3")}
    started = {c: [0] * MINUTES for c in next_id}  # tracks first seen per minute, for id_churn
    present: list[tuple[str, float, float]] = []  # (zone, from, to) of every customer visit, for the queue
    blocked = lambda camera, a, b: camera == BLOCKED[0] and a < BLOCKED[2] and b > BLOCKED[1]

    def track(zone, start, end, role):
        camera = CAMERA_OF[zone]
        next_id[camera] += 1
        tid = next_id[camera]
        base = {"run_id": RUN_ID, "store_id": STORE, "camera_id": camera, "zone_id": zone, "ts_start": at(start), "ts_end": at(end)}
        rows["tracks"].append({**base, "event_id": f"{RUN_ID}:track:{camera}:{tid}", "track_id": tid, "role": role,
                               "employee_score": round(rnd.uniform(0.6, 0.95) if role == "employee" else rnd.uniform(0.0, 0.3), 3),
                               "frames_observed": int((end - start) * 60 * 10)})
        rows["role_decisions"].append({**base, "event_id": f"{RUN_ID}:role:{camera}:{tid}:0", "track_id": tid, "role": role,
                                       "frames": int((end - start) * 60 * 10)})
        rows["zone_dwell"].append({**base, "event_id": f"{RUN_ID}:dwell:{camera}:{tid}", "track_id": tid, "role": role,
                                   "dwell_s": round((end - start) * 60, 1)})
        started[camera][int(start)] += 1
        return base, tid

    # Employees: one track per hour on duty (hourly re-ID breaks, like the real tracker); z3 gets a 10-minute visit every 2 h.
    on_duty = {zone: [] for zone in CAMERA_OF}
    for hour in range(12):
        for zone, count in STAFF.items():
            for _ in range(count):
                on_duty[zone].append((hour * 60, hour * 60 + 60, track(zone, hour * 60, hour * 60 + 60, "employee")[1]))
        if hour % 2 == 0:
            visit = hour * 60 + rnd.randint(0, 50)
            on_duty["z3"].append((visit, visit + 10, track("z3", visit, visit + 10, "employee")[1]))

    for minute in range(MINUTES - 20):
        rate = 1.2 * (3 if RUSH[0] <= minute < RUSH[1] else 1)
        for _ in range(sum(rnd.random() < rate / 4 for _ in range(4))):  # ~Poisson arrivals per minute
            t = minute + rnd.random()
            _, entry = track("z1", t, t + 0.5, "customer")
            rows["footfall"].append({"event_id": f"{RUN_ID}:footfall:c1:{entry}:in", "run_id": RUN_ID, "store_id": STORE,
                                     "camera_id": "c1", "zone_id": "z1", "ts_start": at(t), "ts_end": at(t), "track_id": entry, "direction": "in"})
            t += 0.5
            for zone in rnd.sample(["z2", "z3", "z4", "z5"], rnd.randint(1, 3)) + ["z6"]:
                dwell = {"z5": rnd.uniform(0.5, 3), "z6": rnd.uniform(1, 3)}.get(zone, rnd.uniform(1, 5))
                end = min(t + dwell, MINUTES - 1)
                present.append((zone, t, end))
                if not blocked(CAMERA_OF[zone], t, end):
                    base, cid = track(zone, t, end, "customer")
                    wait = rnd.expovariate(1 / 1.2)  # minutes until a free employee walks over
                    staff = [e for a, b, e in on_duty[zone] if a <= t + wait < b]
                    if staff and zone != "z6" and t + wait < end and rnd.random() < 0.8:
                        length = min(rnd.uniform(0.3, 2.5), end - t - wait)
                        rows["interactions"].append({**base, "event_id": f"{RUN_ID}:interaction:{base['camera_id']}:{staff[0]}:{cid}",
                                                     "ts_start": at(t + wait), "ts_end": at(t + wait + length),
                                                     "employee_track_id": staff[0], "customer_track_id": cid,
                                                     "duration_s": round(length * 60, 1), "verdict": "interaction"})
                t = end
            _, leaving = track("z1", t, t + 0.5, "customer")
            rows["footfall"].append({"event_id": f"{RUN_ID}:footfall:c1:{leaving}:out", "run_id": RUN_ID, "store_id": STORE,
                                     "camera_id": "c1", "zone_id": "z1", "ts_start": at(t + 0.5), "ts_end": at(t + 0.5),
                                     "track_id": leaving, "direction": "out"})

    for second in range(0, MINUTES * 60, 30):  # checkout queue every 30 s; 2 tills, ~90 s per customer
        minute = second / 60
        length = sum(zone == "z6" and a <= minute < b for zone, a, b in present)
        rows["queue_samples"].append({"event_id": f"{RUN_ID}:queue:c3:{second}", "run_id": RUN_ID, "store_id": STORE, "camera_id": "c3",
                                      "zone_id": "z6", "ts_start": at(minute), "ts_end": at(minute), "queue_length": length,
                                      "est_wait_s": round(length * 90 / STAFF["z6"], 1)})

    for camera, zone in HOME_ZONE.items():
        for minute in range(MINUTES):
            dark = blocked(camera, minute, minute + 1)
            rows["pipeline_health"].append({"event_id": f"{RUN_ID}:health:{camera}:{minute}", "run_id": RUN_ID, "store_id": STORE,
                                            "camera_id": camera, "zone_id": zone, "ts_start": at(minute), "ts_end": at(minute + 1),
                                            "fps": round(rnd.uniform(8.5, 10.0), 2),
                                            "mean_confidence": None if dark else round(rnd.uniform(0.72, 0.86), 3),
                                            "unknown_role_share": None if dark else round(rnd.uniform(0.0, 0.08), 3),
                                            "id_churn": started[camera][minute], "frozen_or_dark": int(dark)})

    # 32x18 foot-point grids per camera per hour: traffic scaled by that hour's tracks, peaking at a per-camera hotspot.
    hotspots = {"c1": (16, 14), "c2": (8, 10), "c3": (24, 12)}
    for camera, (hx, hy) in hotspots.items():
        for hour in range(12):
            busy = sum(started[camera][hour * 60:hour * 60 + 60])
            cells = [[int(busy * 30 / (1 + ((c - hx) ** 2 + (r - hy) ** 2) / 8) * rnd.uniform(0.7, 1.3)) for c in range(32)] for r in range(18)]
            rows["heatmaps"].append({"event_id": f"{RUN_ID}:heatmap:{camera}:{hour}", "run_id": RUN_ID, "store_id": STORE, "camera_id": camera,
                                     "zone_id": HOME_ZONE[camera], "ts_start": at(hour * 60),
                                     "ts_end": at(hour * 60 + 60), "cols": 32, "rows": 18, "cells": json.dumps(cells)})

    with conn:
        delete_run(conn, RUN_ID)
        for table, table_rows in rows.items():
            insert(conn, table, table_rows)
        unattended = derive_unattended(conn, RUN_ID, unattended_after_s)
    return {**{t: len(r) for t, r in rows.items()}, "unattended_episodes": unattended}


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the synthetic schema v1 fixture day.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    with connect(args.db) as conn:
        counts = generate(conn, args.seed)
        problems = validate(conn)
    print(f"{args.db}: {counts}")
    if problems:
        raise SystemExit("\n".join(problems))


if __name__ == "__main__":
    main()
