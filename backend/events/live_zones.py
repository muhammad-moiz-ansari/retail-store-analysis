"""What kind of zone a camera view is right now (FR-07): live, temporary, and with no floor plan.

The whole view is one zone, judged by the ratio of customers to employees in it:

    hot       more customers than employees (so also customers with no employee)
    gray      customers, with at least as many employees
    green     employees only
    inactive  nobody

`hot_ratio` is the number of customers one employee covers: the zone is hot when customers exceed
hot_ratio x employees. At the default 1.0, two customers with one employee is hot and one with one is gray.

Attention overrides the ratio: when every customer in view has had a confirmed interaction with an employee within
the last `served_s`, the zone is gray however many customers there are. It turns hot again when a customer who has
not been attended is in view, or when the last interaction is older than `served_s`. A customer is known by their
track, so one who is given a new track ID counts as not yet attended.

A new state is shown once it has held for `hold_s`, so a missed detection or a brief role flip does not make the
zone flicker. People of unknown role settle nothing: a frame with only unknown people keeps the state it had.
Frames the caller marks unobserved (frozen or dark) are skipped, so a blind camera never reads as inactive.
The state is `starting` until the first one has held. Nothing is stored.
"""

from __future__ import annotations

from ..interaction.types import CONFIRMED

STATES = ("hot", "gray", "green", "inactive")


def state_of(employees: int, customers: int, hot_ratio: float = 1.0) -> str:
    if customers:
        return "hot" if customers > hot_ratio * employees else "gray"
    return "green" if employees else "inactive"


class LiveZone:
    def __init__(self, hold_s: float = 1.5, max_gap_s: float = 2.0, hot_ratio: float = 1.0, served_s: float = 30.0) -> None:
        if hold_s < 0 or max_gap_s <= 0 or hot_ratio <= 0 or served_s < 0:
            raise ValueError("Live zone needs hold_s and served_s of 0 or more and a positive max_gap_s and hot_ratio")
        self.hold_s, self.max_gap_s, self.hot_ratio, self.served_s = hold_s, max_gap_s, hot_ratio, served_s
        self.reset()

    def reset(self) -> None:
        self._state = "starting"
        self._pending: tuple[str, float] | None = None  # (state seen, since when) while it has not held long enough
        self._seconds = dict.fromkeys(STATES, 0.0)  # how long the view has been in each state
        self._last, self._counts = None, (0, 0)
        self._served: dict[int, float] = {}  # customer track -> when an employee last interacted with them
        self._attended = False  # every customer in view was attended within served_s

    def update(self, people: list[dict], timestamp: float, observed: bool = True, interactions: list[dict] = ()) -> dict:
        """Add one processed frame (`people` and `interactions` as in the pipeline result) and return the zone as of
        `timestamp`. Only interactions the judge confirmed, or could not check, count as attention."""
        if self._last is not None and timestamp < self._last:
            self.reset()  # the clock went backwards: a new clip or a restarted stream
        # A frame stands for the time since the previous one, capped so an outage is not counted.
        seconds = 0.0 if self._last is None else min(timestamp - self._last, self.max_gap_s)
        self._last = timestamp
        employees = sum(person["role"] == "employee" for person in people)
        customers = sum(person["role"] == "customer" for person in people)
        unsure = bool(people) and not employees and not customers  # only people of unknown role
        for event in interactions:
            if event.get("verdict", "unverified") in CONFIRMED:
                track = event["customer_track_id"]
                self._served[track] = max(self._served.get(track, event["last_seen_at"]), event["last_seen_at"])
        self._served = {track: at for track, at in self._served.items() if timestamp - at <= self.served_s}
        if observed and not unsure:
            self._counts = (employees, customers)
            in_view = [person.get("track_id") for person in people if person["role"] == "customer"]
            self._attended = bool(in_view) and all(track in self._served for track in in_view)
            seen = "gray" if self._attended else state_of(employees, customers, self.hot_ratio)
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
        return {"view": self._state, "hot_ratio": self.hot_ratio, "served_seconds": self.served_s,
                "all_customers_attended": self._attended, "employees": self._counts[0], "customers": self._counts[1],
                "view_seconds": {state: round(total, 2) for state, total in self._seconds.items()}}
