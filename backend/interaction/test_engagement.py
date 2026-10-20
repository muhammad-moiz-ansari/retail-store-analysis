"""Dependency-light checks for interaction state transitions."""

from .config import InteractionConfig
from .engagement import EngagementDetector, body_distance
from .types import TrackedPerson


def person(track_id: int, role: str, x: int, height: int = 100, top: int = 0, width: int = 20) -> TrackedPerson:
    return TrackedPerson(track_id, (x, top, x + width, top + height), 0.9, role, 0.9)  # type: ignore[arg-type]


def test_interaction_requires_minimum_duration() -> None:
    detector = EngagementDetector(InteractionConfig(min_interaction_seconds=2))
    people = [person(1, "employee", 0), person(2, "customer", 30)]  # feet bands 0.1 heights apart
    assert detector.update(people, 0) == []
    events = detector.update(people, 2.1)
    assert len(events) == 1
    assert events[0].employee_track_id == 1
    assert events[0].customer_track_id == 2
    assert events[0].measured_by == "feet"


def test_people_outside_range_do_not_interact() -> None:
    detector = EngagementDetector(InteractionConfig(min_interaction_seconds=0))
    assert detector.update([person(1, "employee", 0), person(2, "customer", 200)], 0) == []  # 2 heights apart


def test_feet_take_precedence_and_include_the_depth_gap() -> None:
    a, b = person(1, "employee", 0), person(2, "customer", 30, top=40)  # feet bands y 65-100 vs 105-140
    distance, part, close = body_distance(a, b, InteractionConfig())
    assert part == "feet" and round(distance, 2) == 0.11 and close  # gap is edge to edge: hypot(10, 5)


def test_feet_cut_off_by_frame_bottom_fall_back_to_hips_with_tighter_limit() -> None:
    config = InteractionConfig()
    a = person(1, "employee", 0)
    near, far = person(2, "customer", 70), person(3, "customer", 110)  # band gaps 0.5 and 0.9 heights
    assert body_distance(a, near, config, frame_height=100)[1:] == ("hips", True)
    assert body_distance(a, far, config, frame_height=100)[1:] == ("hips", False)  # 0.9 would pass for feet


def test_feet_and_hips_hidden_behind_a_nearer_person_fall_back_to_head() -> None:
    employee = person(1, "employee", 0, height=200, width=120, top=10)
    customer = person(2, "customer", 90, height=170, top=20)  # standing just behind the employee
    assert body_distance(employee, customer, InteractionConfig(), [employee, customer])[1] == "head"


def test_people_at_different_depths_are_not_close_even_when_overlapping() -> None:
    near_camera = person(1, "employee", 0, height=300)
    far_behind = person(2, "customer", 10, height=100)
    assert body_distance(near_camera, far_behind, InteractionConfig())[2] is False


def test_passer_by_walking_close_past_the_employee_is_not_an_interaction() -> None:
    detector = EngagementDetector(InteractionConfig(min_interaction_seconds=2))
    events = []
    for step in range(31):  # customer walks from x=-40 to x=80 past the employee at x=0, 0.4 heights/s
        t = step / 10
        events = detector.update([person(1, "employee", 0), person(2, "customer", int(-40 + 40 * t))], t)
        assert events == []


def test_pair_moving_camera_still_interacts() -> None:
    detector = EngagementDetector(InteractionConfig(min_interaction_seconds=2))
    for step in range(22):  # camera pans: both shift together, relative position unchanged
        shift = 10 * step
        events = detector.update([person(1, "employee", shift), person(2, "customer", 30 + shift)], step / 10)
    assert len(events) == 1
