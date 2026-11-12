"""Live occupancy categories for MAP-3 (Ruhab's semantics), as pure logic.

Exactly four categories: customer, employee, customer_employee, no_one. Anything that
cannot support one of them is masked with a separate `quality` code and category None;
there is no fifth category, and missing data is never reported as no_one.

Inputs are per-cell, per-window observations already projected onto the supplied map by
Saqib's MAP-2 registration. Cell IDs are stable location keys, never role labels, and
they are not authorization scopes. Physical distance is not implied by any value here.

Rules per window (thresholds in `OccupancyPolicy`):
1. unmapped cell                                  -> masked, quality 'unmapped'
2. healthy observed share < min_coverage           -> masked, 'insufficient_coverage'
3. a role is present when its seconds >= min_presence_s
4. unknown-role presence that could change the answer -> masked, 'unknown_role'
   (it cannot change the answer only when both roles are already present)
5. both present -> customer_employee (co-presence only; never an interaction)
6. one present  -> customer / employee;  neither, no unknown -> no_one (observed empty)

`OccupancyTracker` adds hysteresis: a published category changes only after the new
category holds for `hold_windows` consecutive valid windows. Masked windows publish
None, and a gap between windows or a masked window resets the pending change.
"""
from typing import Literal

from pydantic import Field, model_validator

from ..contracts import Contract, Identifier, TimeWindow

Category = Literal['customer', 'employee', 'customer_employee', 'no_one']
Quality = Literal['ok', 'unmapped', 'insufficient_coverage', 'unknown_role']
CATEGORIES = ('customer', 'employee', 'customer_employee', 'no_one')


class OccupancyPolicy(Contract):
    min_coverage: float = Field(default=0.8, gt=0, le=1)
    min_presence_s: float = Field(default=5, ge=0)
    hold_windows: int = Field(default=2, ge=1, le=20)
    version: Identifier = 'ruhab-occupancy-v1'


class CellObservation(Contract):
    """Seconds within one window for one map cell; presence is time any person of that role was there."""
    cell_id: Identifier
    window: TimeWindow
    mapped: bool = True
    observed_s: float = Field(ge=0)
    customer_s: float = Field(default=0, ge=0)
    employee_s: float = Field(default=0, ge=0)
    unknown_role_s: float = Field(default=0, ge=0)
    map_version: Identifier

    @model_validator(mode='after')
    def within_window(self):
        span = (self.window.end - self.window.start).total_seconds()
        if any(v > span + 1e-9 for v in (self.observed_s, self.customer_s, self.employee_s, self.unknown_role_s)):
            raise ValueError('Observation seconds cannot exceed the window')
        return self


class CellState(Contract):
    cell_id: Identifier
    window: TimeWindow
    category: Category | None
    quality: Quality
    observed_category: Category | None  # this window alone, before hysteresis
    pending: Category | None = None     # a change that has not yet held long enough
    map_version: Identifier
    policy_version: Identifier

    @model_validator(mode='after')
    def masked_means_no_category(self):
        if (self.quality == 'ok') != (self.observed_category is not None):
            raise ValueError('Only ok windows carry an observed category')
        if self.quality != 'ok' and self.category is not None:
            raise ValueError('Masked windows publish no category')
        return self


def classify(observation: CellObservation, policy=OccupancyPolicy()) -> tuple[Category | None, Quality]:
    if not observation.mapped:
        return None, 'unmapped'
    span = (observation.window.end - observation.window.start).total_seconds()
    if observation.observed_s / span < policy.min_coverage:
        return None, 'insufficient_coverage'
    customer = observation.customer_s >= policy.min_presence_s
    employee = observation.employee_s >= policy.min_presence_s
    unknown = observation.unknown_role_s >= policy.min_presence_s
    if unknown and not (customer and employee):
        return None, 'unknown_role'
    if customer and employee:
        return 'customer_employee', 'ok'
    if customer:
        return 'customer', 'ok'
    if employee:
        return 'employee', 'ok'
    return 'no_one', 'ok'


class OccupancyTracker:
    """Per-cell hysteresis across consecutive windows; feed windows in time order."""

    def __init__(self, policy=OccupancyPolicy()):
        self.policy = policy
        self._last = {}  # cell -> (window end, published category, pending category, streak)

    def update(self, observation: CellObservation) -> CellState:
        observed, quality = classify(observation, self.policy)
        previous = self._last.get(observation.cell_id)
        contiguous = previous is not None and previous[0] == observation.window.start
        published, pending, streak = (previous[1], previous[2], previous[3]) if contiguous else (None, None, 0)
        if observed is None:
            published, pending, streak = (published if contiguous else None), None, 0
            state_category = None
        elif published is None or observed == published:
            published, pending, streak = observed, None, 0
            state_category = published
        else:
            streak = streak + 1 if pending == observed else 1
            pending = observed
            if streak >= self.policy.hold_windows:
                published, pending, streak = observed, None, 0
            state_category = published
        self._last[observation.cell_id] = (observation.window.end, published, pending, streak)
        return CellState(cell_id=observation.cell_id, window=observation.window, category=state_category,
                         quality=quality, observed_category=observed, pending=pending,
                         map_version=observation.map_version, policy_version=self.policy.version)


class LayerValue(Contract):
    cell_id: Identifier
    value: float | None = Field(ge=0)
    masked_reason: Quality | None = None


class HeatmapLayer(Contract):
    """One quantity per layer; layers are never combined into a category or a density."""
    layer: Literal['customer_presence', 'employee_presence', 'confirmed_interactions', 'unverified_interactions']
    unit: Literal['seconds', 'count']
    window: TimeWindow
    map_version: Identifier
    cells: tuple[LayerValue, ...]


def presence_layers(observations, window: TimeWindow, policy=OccupancyPolicy()):
    """Customer and employee presence-time layers; masked cells carry no value."""
    layers = []
    for name, field in (('customer_presence', 'customer_s'), ('employee_presence', 'employee_s')):
        cells = []
        for obs in observations:
            if obs.window != window:
                raise ValueError('All observations must share the layer window')
            _, quality = classify(obs, policy)
            # Unknown roles mask the category, but a role's own observed presence is still a valid layer value.
            masked = quality in ('unmapped', 'insufficient_coverage')
            cells.append(LayerValue(cell_id=obs.cell_id, value=None if masked else getattr(obs, field),
                                    masked_reason=quality if masked else None))
        layers.append(HeatmapLayer(layer=name, unit='seconds', window=window,
                                   map_version=_one_version(observations), cells=tuple(cells)))
    return tuple(layers)


def interaction_layers(records, window: TimeWindow, map_version):
    """records: iterable of (cell_id, verdict). Confirmed and unverified stay separate layers."""
    counts = {'interaction': {}, 'unverified': {}}
    for cell_id, verdict in records:
        if verdict in counts:
            counts[verdict][cell_id] = counts[verdict].get(cell_id, 0) + 1
    return tuple(HeatmapLayer(layer=name, unit='count', window=window, map_version=map_version,
                              cells=tuple(LayerValue(cell_id=c, value=float(n)) for c, n in sorted(counts[verdict].items())))
                 for name, verdict in (('confirmed_interactions', 'interaction'), ('unverified_interactions', 'unverified')))


def _one_version(observations):
    versions = {obs.map_version for obs in observations}
    if len(versions) != 1:
        raise ValueError('A layer needs exactly one map version')
    return versions.pop()
