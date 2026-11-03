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
    for t in (0.0, 1.0, 2.0, 3.0):
        assert classifier.classify(yellow, box, 1, t)[0] == "employee"  # employee held 3 s -> locked
    assert classifier.classify(grey, box, 1, 4.0)[0] == "employee"  # flicker starts
    assert classifier.classify(yellow, box, 1, 5.0)[0] == "employee"  # flicker over, pending reset
    for t in (6.0, 7.0, 8.0):
        assert classifier.classify(grey, box, 1, t)[0] == "employee"  # held < 3 s
    assert classifier.classify(grey, box, 1, 9.0)[0] == "customer"  # held 3 s -> switch


def test_new_id_follows_frame_role_until_a_role_has_held_long_enough_to_lock() -> None:
    classifier = RoleClassifier(InteractionConfig(role_mode="bib_color", role_smoothing=0.0, role_hold_seconds=3.0))
    yellow = np.full((120, 80, 3), (0, 255, 255), dtype=np.uint8)
    grey = np.full((120, 80, 3), (128, 128, 128), dtype=np.uint8)
    box = (0, 0, 80, 120)
    assert classifier.classify(yellow, box, 1, 0.0)[0] == "employee"  # first frame overlapped a bib wearer
    for t in (0.5, 1.0, 2.0, 3.5):
        assert classifier.classify(grey, box, 1, t)[0] == "customer"  # not locked: corrects at once
    assert classifier.classify(yellow, box, 1, 4.0)[0] == "customer"  # customer locked at 3.5 s


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


def test_role_model_labels_a_track_once_then_only_rechecks() -> None:
    class Box:
        def __init__(self, cls):
            self.xyxy, self.cls, self.conf = np.array([(100, 50, 200, 400)], float), np.array([cls]), np.array([0.9])

    label = [0]
    calls = []

    def model(frame, **_):
        calls.append(1)
        return [type("Result", (), {"names": {0: "employee", 1: "customer"}, "boxes": [Box(label[0])]})()]

    classifier = RoleClassifier(InteractionConfig(role_mode="model", role_model_seconds=1.0, role_recheck_seconds=2.0), model)
    frame = lambda: np.zeros((480, 640, 3), np.uint8)
    yolo_role = lambda bbox, track, t: classifier.classify(frame(), bbox, track, t)[2]["yolo_role"]
    assert [yolo_role((100, 50, 200, 400), 1, t) for t in (0.0, 0.5, 1.0)] == ["employee"] * 3
    assert len(calls) == 1  # labelled on its first frame, then idle
    label[0] = 1  # ID switch: a customer now holds track 1
    assert yolo_role((100, 50, 200, 400), 1, 1.5) == "employee"  # kept between checks
    assert yolo_role((100, 50, 200, 400), 1, 2.0) == "customer"  # corrected at the recheck
    calls.clear()
    # nobody under this box: tried on each frame of its first second, then once per recheck
    assert [yolo_role((500, 50, 600, 400), 2, t) for t in (0.0, 0.5, 1.5, 3.0)] == [None] * 4
    assert len(calls) == 3


def test_role_score_settles_at_the_same_speed_at_any_frame_rate() -> None:
    yellow = np.full((120, 80, 3), (0, 255, 255), dtype=np.uint8)
    grey = np.full((120, 80, 3), (128, 128, 128), dtype=np.uint8)
    scores = []
    for fps in (3, 10):
        classifier = RoleClassifier(InteractionConfig(role_mode="bib_color"))
        classifier.classify(grey, (0, 0, 80, 120), 1, 0.0)
        scores.append([classifier.classify(yellow, (0, 0, 80, 120), 1, i / fps)[1] for i in range(1, fps + 1)][-1])
    assert abs(scores[0] - scores[1]) < 0.01  # same score 1 s after the bib appears (stationary evidence differs a hair)


def test_calibrated_camera_learns_a_uniform_the_bib_rules_have_never_seen() -> None:
    from .tracker import appearance_descriptor

    red = np.full((120, 80, 3), (0, 0, 220), dtype=np.uint8)  # BGR red uniform: no yellow bib
    blue = np.full((120, 80, 3), (200, 80, 0), dtype=np.uint8)
    noise = lambda frame: np.clip(frame.astype(int) + np.random.default_rng(1).integers(-20, 20, frame.shape), 0, 255).astype(np.uint8)
    box = (0, 0, 80, 120)
    references = {"employee": [appearance_descriptor(noise(red), list(box))], "customer": [appearance_descriptor(noise(blue), list(box))]}
    calibrated = RoleClassifier(InteractionConfig(role_mode="bib_color", role_references=references, role_smoothing=0.0))
    assert calibrated.classify(noise(red), box, 1, 0.0)[0] == "employee"
    assert calibrated.classify(noise(blue), box, 2, 0.0)[0] == "customer"
    assert calibrated.appearance(1) is not None
    uncalibrated = RoleClassifier(InteractionConfig(role_mode="bib_color", role_smoothing=0.0))
    role, _, evidence = uncalibrated.classify(noise(red), box, 1, 0.0)
    assert role == "customer" and evidence["factors"]["reference"] is None
