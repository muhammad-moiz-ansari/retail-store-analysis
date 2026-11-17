"""What kind of zone a camera view is right now (FR-07): live, temporary, and with no floor plan.

The whole view is one zone, judged by who is in it:

    hot       customers only
    gray      customers and employees together
    green     employees only
    inactive  nobody

A new state is shown once it has held for `hold_s`, so a missed detection or a brief role flip does not make the
zone flicker. People of unknown role settle nothing: a frame with only unknown people keeps the state it had.
Frames the caller marks unobserved (frozen or dark) are skipped, so a blind camera never reads as inactive.
The state is `starting` until the first one has held. Nothing is stored.
"""

from __future__ import annotations

STATES = ("hot", "gray", "green", "inactive")


def state_of(employees: int, customers: int) -> str:
    if customers:
        return "gray" if employees else "hot"
    return "green" if employees else "inactive"


class LiveZone:
    def __init__(self, hold_s: float = 1.5, max_gap_s: float = 2.0) -> None:
        if hold_s < 0 or max_gap_s <= 0:
            raise ValueError("Live zone needs hold_s of 0 or more and a positive max_gap_s")
        self.hold_s, self.max_gap_s = hold_s, max_gap_s
        self.reset()

    def reset(self) -> None:
        self._state = "starting"
        self._pending: tuple[str, float] | None = None  # (state seen, since when) while it has not held long enough
        self._seconds = dict.fromkeys(STATES, 0.0)  # how long the view has been in each state
        self._last, self._counts = None, (0, 0)

    def update(self, people: list[dict], timestamp: float, observed: bool = True) -> dict:
        """Add one processed frame (`people` as in the pipeline result) and return the zone as of `timestamp`."""
        if self._last is not None and timestamp < self._last:
            self.reset()  # the clock went backwards: a new clip or a restarted stream
        # A frame stands for the time since the previous one, capped so an outage is not counted.
        seconds = 0.0 if self._last is None else min(timestamp - self._last, self.max_gap_s)
        self._last = timestamp
        employees = sum(person["role"] == "employee" for person in people)
        customers = sum(person["role"] == "customer" for person in people)
        unsure = bool(people) and not employees and not customers  # only people of unknown role
        if observed and not unsure:
            self._counts = (employees, customers)
            seen = state_of(employees, customers)
            if seen == self._state:
                self._pending = None
            else:
                if not self._pending or self._pending[0] != seen:
                    self._pending = (seen, timestamp)
                if timestamp - self._pending[1] >= self.hold_s:
                    self._state, self._pending = seen, None
        else:
            self._pending = None  # nothing reliable was seen, so a change in progress starts over
        if observed and self._state in self._seconds:
            self._seconds[self._state] += seconds
        return self.snapshot()

    def snapshot(self) -> dict:
        return {"view": self._state, "employees": self._counts[0], "customers": self._counts[1],
                "view_seconds": {state: round(total, 2) for state, total in self._seconds.items()}}
