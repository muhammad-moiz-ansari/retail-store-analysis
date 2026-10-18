"""Timestamp based metric smoothing downstream of existing ByteTrack association."""
import math
import numpy as np


class PositionSmoother:
    def __init__(self, tau_s=.25, max_speed_m_s=3., jump_allowance_m=.2, prediction_s=.3, expire_s=1.):
        if tau_s <= 0 or max_speed_m_s <= 0 or jump_allowance_m < 0 or not 0 <= prediction_s <= expire_s:
            raise ValueError("Invalid smoothing/prediction settings")
        self.tau = tau_s
        self.max_speed = max_speed_m_s
        self.allowance = jump_allowance_m
        self.prediction_s = prediction_s
        self.expire_s = expire_s
        self.states = {}

    def update(self, records, timestamp, allow_predictions=True):
        self.states = {k: v for k, v in self.states.items() if timestamp - v["last_reliable_observation_s"] <= self.expire_s}
        seen = set()
        for record in records:
            key = record["track_id"]
            if key is None:
                continue
            seen.add(key)
            if record["status"] != "observed_proxy":
                # No smoothing across unsupported geometry/visibility intervals.
                self.states.pop(key, None)
                continue
            xy = np.asarray(record["floor_xy_m"])
            previous = self.states.get(key)
            velocity = np.zeros(2)
            smooth = xy.copy()
            if previous:
                dt = timestamp - previous["last_reliable_observation_s"]
                raw = np.asarray(previous["raw_xy_m"])
                if dt <= 0 or np.linalg.norm(xy - raw) > self.max_speed * dt + self.allowance:
                    record.update(status="unreliable", reason="implausible_metric_jump", floor_xy_m=None)
                    self.states.pop(key, None)
                    continue
                alpha = 1 - math.exp(-dt / self.tau)
                smooth = np.asarray(previous["smoothed_xy_m"]) + alpha * (xy - np.asarray(previous["smoothed_xy_m"]))
                velocity = (xy - raw) / dt
            record.update(smoothed_xy_m=smooth.tolist(), last_reliable_observation_s=timestamp)
            self.states[key] = {"raw_xy_m": xy.tolist(), "smoothed_xy_m": smooth.tolist(),
                                "velocity_m_s": velocity.tolist(), "last_reliable_observation_s": timestamp,
                                "record": record.copy()}
        predictions = []
        if allow_predictions:
            for key, state in self.states.items():
                dt = timestamp - state["last_reliable_observation_s"]
                if key not in seen and 0 < dt <= self.prediction_s:
                    record = state["record"].copy()
                    xy = np.asarray(state["smoothed_xy_m"]) + dt * np.asarray(state["velocity_m_s"])
                    record.update(status="predicted", timestamp_s=timestamp, prediction_time_s=timestamp,
                                  floor_xy_m=xy.tolist(), smoothed_xy_m=xy.tolist(),
                                  reason="short_extrapolation", position_reliability="predicted")
                    predictions.append(record)
        return predictions
