"""Checks for the temporal role-evidence policy."""

import numpy as np

from .config import InteractionConfig
from .role_classifier import RoleClassifier


def test_yellow_bib_is_primary_employee_evidence() -> None:
    frame = np.full((120, 80, 3), (0, 255, 255), dtype=np.uint8)  # BGR yellow
    classifier = RoleClassifier(InteractionConfig(role_mode="bib_color"))
    role, score, evidence = classifier.classify(frame, (0, 0, 80, 120), 1, 0.0)
    assert role == "employee"
    assert score >= 0.60
    assert evidence["visual_employee_score"] > 0


def test_staff_zone_alone_does_not_label_a_customer_as_employee() -> None:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    config = InteractionConfig(role_mode="bib_color", staff_zones=((0, 0, 1, 1),), staff_zone_dwell_seconds=1)
    classifier = RoleClassifier(config)
    classifier.classify(frame, (0, 0, 20, 100), 1, 0.0)
    role, _, evidence = classifier.classify(frame, (0, 0, 20, 100), 1, 2.0)
    assert role == "customer"
    assert evidence["staff_zone_dwell_seconds"] == 2.0
