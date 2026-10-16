"""Weighted customer/employee decision agent.

Every factor is an employee-evidence score: YOLO is signed (+confidence for an
`employee` detection, -confidence for `customer`, None when the role model saw
nothing), the others are in [0, 1]. The agent's score is the weighted sum,
clipped to [0, 1], compared against a threshold.
"""

from __future__ import annotations

DEFAULT_WEIGHTS = {
    "yolo": 0.55,        # role model (best.pt) decision; >=0.82 confidence alone is enough
    "bib_colour": 0.30,  # HSV bib coverage in the torso; steadier than best.pt on bib wearers
    "staff_zone": 0.10,  # dwell in a configured staff-only zone
    "stationary": 0.05,  # standing still; zone + stationary (0.15) can never decide alone
}


class CustEmpClassifier:
    def __init__(self, weights: dict[str, float] | None = None, threshold: float = 0.45) -> None:
        self.weights = {**DEFAULT_WEIGHTS, **(weights or {})}
        self.threshold = threshold

    def decide(self, factors: dict[str, float | None]) -> tuple[str, float, dict[str, float]]:
        """Return (role, employee_score, per-factor weighted contributions)."""
        weights = dict(self.weights)
        if factors.get("yolo") is None:
            # No role-model evidence: the bib colour is the only appearance signal left.
            weights["bib_colour"] += weights.pop("yolo")
        contributions = {name: round(weight * (factors.get(name) or 0.0), 3) for name, weight in weights.items()}
        score = min(1.0, max(0.0, sum(contributions.values())))
        return ("employee" if score >= self.threshold else "customer"), score, contributions

    def classify_person(self, frame_factors: list[dict[str, float | None]]) -> dict:
        """Final per-track decision from the mean of each factor over every frame the person was seen."""
        means: dict[str, float | None] = {}
        for name in self.weights:
            values = [f[name] for f in frame_factors if f.get(name) is not None]
            means[name] = round(sum(values) / len(values), 3) if values else None
        role, score, contributions = self.decide(means)
        return {"role": role, "employee_score": round(score, 3), "factors": means, "contributions": contributions}
