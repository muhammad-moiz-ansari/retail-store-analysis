"""Weighted customer/employee decision agent.

Every factor is an employee-evidence score: YOLO and reference are signed (+ for
employee evidence, - for customer, None when there is none), the others are in
[0, 1]. The agent's score is the weighted sum, clipped to [0, 1], compared
against a threshold.
"""

from __future__ import annotations

DEFAULT_WEIGHTS = {
    # A calibrated camera's own labelled tracks replace the generic role model (best.pt), which only knows our
    # training store; uncalibrated, the 0.55 passes to yolo. Give yolo weight in role_weights to blend both.
    "reference": 0.55,   # similarity to this camera's labelled employee/customer tracks; >=0.82 alone is enough
    "yolo": 0.0,         # role model decision (signed confidence)
    "bib_colour": 0.30,  # HSV bib coverage in the torso; steadier than best.pt on bib wearers
    "staff_zone": 0.10,  # dwell in a configured staff-only zone
    "stationary": 0.05,  # standing still; zone + stationary (0.15) can never decide alone
}
# Appearance factors, most store-specific first: a missing one hands its weight to the next one present.
APPEARANCE = ("reference", "yolo", "bib_colour")


class CustEmpClassifier:
    def __init__(self, weights: dict[str, float] | None = None, threshold: float = 0.45, unknown_band: float = 0.0) -> None:
        self.weights = {**DEFAULT_WEIGHTS, **(weights or {})}
        self.threshold = threshold
        self.unknown_band = unknown_band

    def role_for(self, score: float) -> str:
        if abs(score - self.threshold) < self.unknown_band:
            return "unknown"
        return "employee" if score >= self.threshold else "customer"

    def decide(self, factors: dict[str, float | None]) -> tuple[str, float, dict[str, float]]:
        """Return (role, employee_score, per-factor weighted contributions)."""
        weights, carry = dict(self.weights), 0.0
        for name in APPEARANCE:
            if factors.get(name) is None and name != APPEARANCE[-1]:
                carry += weights.pop(name, 0.0)
            else:
                weights[name] = weights.get(name, 0.0) + carry
                carry = 0.0
        contributions = {name: round(weight * (factors.get(name) or 0.0), 3) for name, weight in weights.items()}
        score = min(1.0, max(0.0, sum(contributions.values())))
        return self.role_for(score), score, contributions

    def classify_person(self, frame_factors: list[dict[str, float | None]]) -> dict:
        """Final per-track decision from the mean of each factor over every frame the person was seen."""
        means: dict[str, float | None] = {}
        for name in self.weights:
            values = [f[name] for f in frame_factors if f.get(name) is not None]
            means[name] = round(sum(values) / len(values), 3) if values else None
        role, score, contributions = self.decide(means)
        return {"role": role, "employee_score": round(score, 3), "factors": means, "contributions": contributions}
