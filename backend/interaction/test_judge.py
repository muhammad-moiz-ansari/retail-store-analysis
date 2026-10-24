"""Interaction judge flow in InteractionPipeline, with a fake judge instead of the YOLO models."""

from collections import deque

import numpy as np

from .config import InteractionConfig
from .engagement import EngagementDetector
from .pipeline import InteractionPipeline
from .pose import JudgeResult
from .types import TrackedPerson


class FakeJudge:
    def __init__(self, labels):
        self.labels, self.calls = list(labels), []

    def classify_interaction(self, frames, boxes=None):
        self.calls.append(len(frames))
        return JudgeResult(self.labels.pop(0), 0.75)


def pipeline(judge) -> InteractionPipeline:
    p = InteractionPipeline.__new__(InteractionPipeline)  # skip loading YOLO
    p.config = InteractionConfig(min_interaction_seconds=2, judge_recheck_seconds=4)
    p.engagement, p.judge = EngagementDetector(p.config), judge
    p._recent, p._verdicts = deque(), {}
    p.tracker = type("T", (), {"detect_and_track": lambda self, frame, t: [
        {"track_id": 1, "bbox": (10, 10, 30, 110), "confidence": .9, "label": "employee"},
        {"track_id": 2, "bbox": (40, 10, 60, 110), "confidence": .9, "label": "customer"}]})()
    p.classifier = type("C", (), {"classify": lambda self, frame, bbox, tid, t, tracked: (*tracked, {})})()
    return p


def run(p, until: float) -> list[dict]:
    frame, results = np.zeros((200, 200, 3), np.uint8), []
    for step in range(int(until * 10) + 1):
        results.append(p.process_frame(frame, step / 10))
    return results


def test_rejected_pair_is_never_flagged_and_is_rechecked() -> None:
    judge = FakeJudge(["no_interaction"] * 3)
    results = run(pipeline(judge), 8)
    assert not any(r["interaction_active"] for r in results)
    assert results[-1]["interactions"][0]["verdict"] == "no_interaction"
    assert len(judge.calls) == 2 and judge.calls[0] == 4  # at 2 s and the 4 s recheck at 6 s, 4 frames each


def test_confirmed_pair_is_flagged_from_the_first_qualifying_frame() -> None:
    judge = FakeJudge(["interaction"])
    results = run(pipeline(judge), 3)
    first = next(r for r in results if r["interactions"])
    assert first["interaction_active"] and first["interactions"][0]["verdict"] == "interaction"
    assert len(judge.calls) == 1  # confirmed pairs are not re-judged


def test_broken_judge_keeps_the_proximity_result() -> None:
    class Broken:
        def classify_interaction(self, frames, boxes=None):
            raise RuntimeError("CUDA out of memory")
    results = run(pipeline(Broken()), 3)
    assert results[-1]["interaction_active"] and results[-1]["interactions"][0]["verdict"] == "unverified"


def head(nose_x: float, ears_x: float, conf: float = 0.9) -> list:
    """COCO keypoints with only nose (0) and ears (3, 4) set; ears 10 px apart around ears_x."""
    points = [[0.0, 0.0, 0.0] for _ in range(17)]
    points[0], points[3], points[4] = [nose_x, 20, conf], [ears_x - 5, 20, conf], [ears_x + 5, 20, conf]
    return points


EMPLOYEE_BOX, CUSTOMER_BOX = (0, 0, 40, 100), (60, 0, 100, 100)  # customer stands to the employee's right


def test_head_turned_to_the_other_person_confirms() -> None:
    from .pose import judge_frames
    frames = [(head(28, 20), None)] * 4  # employee's nose is right of the ears: looking at the customer
    assert judge_frames(frames, [(EMPLOYEE_BOX, CUSTOMER_BOX)] * 4, 60, 0.5).label == "interaction"


def test_walking_away_side_by_side_is_rejected() -> None:
    from .pose import judge_frames
    backs = [(head(20, 20, conf=0.1), head(80, 80, conf=0.1))] * 4  # faces not visible: backs to the camera
    looking_away = [(head(12, 20), head(88, 80))] * 4  # both heads turned away from each other
    for frames in (backs, looking_away):
        assert judge_frames(frames, [(EMPLOYEE_BOX, CUSTOMER_BOX)] * 4, 60, 0.5).label == "no_interaction"


def test_no_pose_found_leaves_the_proximity_result() -> None:
    from .pose import judge_frames
    assert judge_frames([(None, None)] * 4, [(EMPLOYEE_BOX, CUSTOMER_BOX)] * 4, 60, 0.5).label == "unknown"


def test_head_in_profile_with_far_ear_hidden_confirms() -> None:
    from .pose import judge_frames
    profile = head(28, 20)
    profile[3][2] = 0.05  # far ear hidden behind the head
    assert judge_frames([(profile, None)] * 4, [(EMPLOYEE_BOX, CUSTOMER_BOX)] * 4, 60, 0.5).label == "interaction"
