"""Checks for mid-frame ID memory (relinking hidden people)."""

import numpy as np

from .config import InteractionConfig
from .tracker import ByteTrackPersonTracker

MID, EDGE = (250, 100, 350, 400), (0, 100, 100, 400)


def _frame(box: tuple[int, int, int, int], bgr: tuple[int, int, int]) -> np.ndarray:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[box[1]:box[3], box[0]:box[2]] = bgr
    return frame


def _person(raw_id: int, box: tuple[int, int, int, int]) -> list[dict]:
    return [{"track_id": raw_id, "bbox": box, "confidence": 0.9}]


def test_person_hidden_mid_frame_gets_old_id_back() -> None:
    tracker = ByteTrackPersonTracker(None, InteractionConfig())
    yellow = _frame(MID, (0, 255, 255))
    tracker._relink(yellow, _person(1, MID), 0.0)
    assert tracker._relink(yellow, _person(7, MID), 1.0)[0]["track_id"] == 1


def test_new_person_entering_from_edge_keeps_new_id() -> None:
    tracker = ByteTrackPersonTracker(None, InteractionConfig())
    tracker._relink(_frame(MID, (0, 255, 255)), _person(1, MID), 0.0)
    assert tracker._relink(_frame(EDGE, (0, 255, 255)), _person(7, EDGE), 1.0)[0]["track_id"] == 7


def test_different_looking_person_or_expired_memory_keeps_new_id() -> None:
    tracker = ByteTrackPersonTracker(None, InteractionConfig())
    tracker._relink(_frame(MID, (0, 255, 255)), _person(1, MID), 0.0)
    assert tracker._relink(_frame(MID, (255, 0, 0)), _person(7, MID), 1.0)[0]["track_id"] == 7
    assert tracker._relink(_frame(MID, (0, 255, 255)), _person(8, MID), 60.0)[0]["track_id"] == 8


def test_person_who_left_at_edge_is_not_relinked() -> None:
    tracker = ByteTrackPersonTracker(None, InteractionConfig())
    tracker._relink(_frame(EDGE, (0, 255, 255)), _person(1, EDGE), 0.0)
    assert tracker._relink(_frame(MID, (0, 255, 255)), _person(7, MID), 1.0)[0]["track_id"] == 7


def test_young_duplicate_is_merged_when_old_partial_box_dies_inside_it() -> None:
    tracker = ByteTrackPersonTracker(None, InteractionConfig())
    yellow, head = _frame(MID, (0, 255, 255)), (260, 100, 340, 200)
    tracker._relink(yellow, _person(1, MID), 0.0)
    # Occlusion: old ID shrinks to the head while the tracker starts ID 5 on the full body.
    tracker._relink(yellow, _person(1, head) + _person(5, MID), 0.5)
    assert tracker._relink(yellow, _person(5, MID), 0.6)[0]["track_id"] == 1
    assert tracker._relink(yellow, _person(5, MID), 0.7)[0]["track_id"] == 1
