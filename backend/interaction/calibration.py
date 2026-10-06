"""Camera-scoped few-shot roles. No identity association or held-out references."""

from collections import deque

from .core import cosine, normalized, prototype
from .cv_contracts import Calibration


def build_calibration(store_id, camera_id, version, models, references, **thresholds):
    prototypes = {role: prototype([prototype(ref.embeddings) for ref in references if ref.role == role])
                  for role in ("employee", "customer")}
    return Calibration(store_id=store_id, camera_id=camera_id, version=version, models=models,
                       references=references, prototypes=prototypes, **thresholds)


class RoleEstimator:
    def __init__(self, models, store_id, camera_id, calibration=None):
        self.models, self.calibration = models, calibration
        self.history = {}
        if calibration is not None:
            if (calibration.store_id, calibration.camera_id) != (store_id, camera_id):
                raise ValueError("Calibration store/camera mismatch")
            for key in ("embedding", "preprocessing", "embedding_dimensions"):
                if getattr(calibration.models, key) != getattr(models, key):
                    raise ValueError(f"Incompatible calibration {key}")

    def update(self, track_id, vector):
        if len(vector) != self.models.embedding_dimensions:
            raise ValueError("Embedding dimensions do not match model")
        self.history.setdefault(track_id, deque(maxlen=5)).append(normalized(vector))

    def estimate(self, track_id, config, zone_prior=0, dwell=0):
        samples = self.history.get(track_id)
        if not self.calibration or not samples:
            return "unknown", {}, "uncalibrated" if not self.calibration else "no_valid_crop"
        vector = prototype(list(samples))
        scores = {role: cosine(vector, self.calibration.prototypes[role]) for role in ("employee", "customer")}
        visual_margin = scores["employee"] - scores["customer"]
        prior = config.prior_weight * (max(-1, min(1, zone_prior)) + max(0, min(1, dwell / config.dwell_seconds))) / 2
        fused = visual_margin + prior
        role = "employee" if visual_margin > 0 else "customer"
        evidence = {**scores, "visual_margin": visual_margin, "prior": prior, "margin": fused,
                    "embedding_samples": float(len(samples))}
        # Priors can reduce certainty but cannot rescue insufficient appearance evidence.
        if scores[role] < self.calibration.similarity or abs(visual_margin) < self.calibration.margin:
            return "unknown", evidence, "insufficient_visual_evidence"
        if abs(fused) < self.calibration.margin or (fused > 0) != (visual_margin > 0):
            return "unknown", evidence, "conflicting_prior"
        return role, evidence, None

    def discard(self, track_id):
        self.history.pop(track_id, None)
