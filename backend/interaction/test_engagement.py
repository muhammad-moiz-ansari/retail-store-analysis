"""Dependency-light checks for interaction state transitions."""

from .config import InteractionConfig
from .engagement import EngagementDetector
from .types import TrackedPerson


def person(track_id: int, role: str, x: int) -> TrackedPerson:
    return TrackedPerson(track_id, (x, 0, x + 20, 100), 0.9, role, 0.9)  # type: ignore[arg-type]


def test_interaction_requires_minimum_duration() -> None:
    detector = EngagementDetector(InteractionConfig(interaction_distance_px=100, min_interaction_seconds=2))
    people = [person(1, "employee", 0), person(2, "customer", 30)]
    assert detector.update(people, 0) == []
    events = detector.update(people, 2.1)
    assert len(events) == 1
    assert events[0].employee_track_id == 1
    assert events[0].customer_track_id == 2


def test_people_outside_range_do_not_interact() -> None:
    detector = EngagementDetector(InteractionConfig(interaction_distance_px=50, min_interaction_seconds=0))
    assert detector.update([person(1, "employee", 0), person(2, "customer", 200)], 0) == []
