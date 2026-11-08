"""Dependency-light checks for interaction state transitions."""

from .config import InteractionConfig
from .engagement import EngagementDetector, body_distance, merge_spans
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


def span(employee: int, customer: int, start: float, end: float, verdict: str = "interaction") -> dict:
    return {"employee_track_id": employee, "customer_track_id": customer, "started_at": start, "last_seen_at": end,
            "duration_seconds": end - start, "verdict": verdict}


def test_merge_spans_one_per_customer() -> None:
    # Set B IMG_8839: one employee serving two customers; employee ID 1 switches to 13 and back.
    merged = merge_spans([span(1, 4, 5.7, 21.3), span(1, 5, 7.7, 18.7), span(13, 4, 21.0, 28.3),
                          span(13, 5, 23.7, 28.3), span(1, 4, 27.7, 30.0), span(5, 4, 29.3, 32.3)], max_gap=4.0)
    # Customer 5 drops out for 5 s (18.7 to 23.7), past max_gap, so that span stays split.
    assert sorted((m["customer_track_id"], m["started_at"], m["last_seen_at"]) for m in merged) == [
        (4, 5.7, 32.3), (5, 7.7, 18.7), (5, 23.7, 28.3)]


def test_merge_spans_flipped_roles_gap_and_verdict() -> None:
    # IMG_8831: same two people with roles swapped 2 s later is one interaction; a far-later span is not.
    merged = merge_spans([span(1, 4, 9.7, 23.3, "no_interaction"), span(4, 1, 25.3, 30.0), span(1, 4, 40.0, 45.0)], max_gap=4.0)
    assert [(m["started_at"], m["last_seen_at"], m["verdict"]) for m in merged] == [(9.7, 30.0, "interaction"), (40.0, 45.0, "interaction")]
