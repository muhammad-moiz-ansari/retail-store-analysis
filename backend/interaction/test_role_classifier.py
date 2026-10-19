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
    assert evidence["factors"]["bib_colour"] > 0


def test_staff_zone_alone_does_not_label_a_customer_as_employee() -> None:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    config = InteractionConfig(role_mode="bib_color", staff_zones=((0, 0, 1, 1),), staff_zone_dwell_seconds=1)
    classifier = RoleClassifier(config)
    classifier.classify(frame, (0, 0, 20, 100), 1, 0.0)
    role, _, evidence = classifier.classify(frame, (0, 0, 20, 100), 1, 2.0)
    assert role == "customer"
    assert evidence["staff_zone_dwell_seconds"] == 2.0


def test_role_flicker_shorter_than_hold_is_ignored_but_sustained_change_switches() -> None:
    config = InteractionConfig(role_mode="bib_color", role_smoothing=0.0, role_hold_seconds=3.0)
    classifier = RoleClassifier(config)
    yellow = np.full((120, 80, 3), (0, 255, 255), dtype=np.uint8)
    grey = np.full((120, 80, 3), (128, 128, 128), dtype=np.uint8)
    box = (0, 0, 80, 120)
    assert classifier.classify(yellow, box, 1, 0.0)[0] == "employee"
    assert classifier.classify(grey, box, 1, 1.0)[0] == "employee"  # flicker starts
    assert classifier.classify(yellow, box, 1, 2.0)[0] == "employee"  # flicker over, pending reset
    for t in (3.0, 4.0, 5.0):
        assert classifier.classify(grey, box, 1, t)[0] == "employee"  # held < 3 s
    assert classifier.classify(grey, box, 1, 6.0)[0] == "customer"  # held 3 s -> switch


def test_full_frame_role_detection_is_matched_to_the_right_overlapping_person() -> None:
    class Box:
        def __init__(self, xyxy, cls, conf):
            self.xyxy, self.cls, self.conf = np.array([xyxy], float), np.array([cls]), np.array([conf])

    class Result:
        names = {0: "employee", 1: "customer"}
        boxes = [Box((100, 50, 200, 400), 0, 0.9), Box((160, 60, 300, 470), 1, 0.8)]

    calls = []
    model = lambda frame, **_: calls.append(1) or [Result()]
    classifier = RoleClassifier(InteractionConfig(role_mode="model"), model)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    assert classifier._classify_with_model(frame, (165, 55, 300, 470)) == ("customer", 0.8)
    assert classifier._classify_with_model(frame, (100, 50, 205, 400)) == ("employee", 0.9)
    assert classifier._classify_with_model(frame, (500, 50, 600, 400)) is None  # nobody there
    assert len(calls) == 1  # one role-model pass per frame, not per person
