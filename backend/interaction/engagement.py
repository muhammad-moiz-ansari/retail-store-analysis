"""Stateful employee/customer proximity interaction detection."""

from __future__ import annotations

from math import hypot

from .config import InteractionConfig
from .types import InteractionEvent, TrackedPerson


class EngagementDetector:
    def __init__(self, config: InteractionConfig) -> None:
        self.config = config
        self._events: dict[tuple[int, int], InteractionEvent] = {}

    def update(self, people: list[TrackedPerson], timestamp: float) -> list[InteractionEvent]:
        """Update interaction state and return active/just-finished eligible events."""
        employees = [person for person in people if person.role == "employee"]
        customers = [person for person in people if person.role == "customer"]
        seen: set[tuple[int, int]] = set()
        for employee in employees:
            for customer in customers:
                distance = hypot(employee.center[0] - customer.center[0], employee.center[1] - customer.center[1])
                if distance > self.config.interaction_distance_px:
                    continue
                key = (employee.track_id, customer.track_id)
                seen.add(key)
                event = self._events.get(key)
                if event is None:
                    self._events[key] = InteractionEvent(*key, timestamp, timestamp, distance)
                else:
                    event.last_seen_at, event.distance_px, event.active = timestamp, distance, True

        output: list[InteractionEvent] = []
        for key, event in list(self._events.items()):
            if key not in seen and timestamp - event.last_seen_at > self.config.max_missing_seconds:
                event.active = False
                del self._events[key]
            if event.duration_seconds >= self.config.min_interaction_seconds:
                output.append(event)
        return output

    def active_events(self) -> list[InteractionEvent]:
        return list(self._events.values())
