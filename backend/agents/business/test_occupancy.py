"""Four live categories: transitions, co-presence, occlusion, unknown roles, blocked feeds, empty space.

All observations are SYNTHETIC FIXTURE values; no camera or map registration is involved.
"""
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from ..contracts import TimeWindow
from .occupancy import (CATEGORIES, CellObservation, CellState, OccupancyPolicy, OccupancyTracker, classify,
                        interaction_layers, presence_layers)

START = datetime(2026, 11, 3, 9, tzinfo=timezone.utc)


def window(i, length=60):
    return TimeWindow(start=START + timedelta(seconds=i * length), end=START + timedelta(seconds=(i + 1) * length))


def obs(i=0, cell='cell-a', observed=60, **seconds):
    return CellObservation(cell_id=cell, window=window(i), observed_s=observed, map_version='fixture-map-v1', **seconds)


@pytest.mark.parametrize('seconds, expected', [
    (dict(customer_s=30), ('customer', 'ok')),
    (dict(employee_s=12), ('employee', 'ok')),
    (dict(customer_s=30, employee_s=20), ('customer_employee', 'ok')),
    (dict(), ('no_one', 'ok')),
    (dict(customer_s=3), ('no_one', 'ok')),                                   # below presence threshold
    (dict(unknown_role_s=20), (None, 'unknown_role')),                        # unknown could be anyone
    (dict(customer_s=30, unknown_role_s=20), (None, 'unknown_role')),         # unknown could be an employee
    (dict(customer_s=30, employee_s=9, unknown_role_s=20), ('customer_employee', 'ok')),  # cannot change answer
])
def test_classification_rules(seconds, expected):
    assert classify(obs(**seconds)) == expected


def test_blocked_or_unmapped_views_are_masked_never_no_one():
    assert classify(obs(observed=30)) == (None, 'insufficient_coverage')
    assert classify(obs(observed=0, customer_s=0)) == (None, 'insufficient_coverage')
    unmapped = CellObservation(cell_id='c', window=window(0), mapped=False, observed_s=60, map_version='m')
    assert classify(unmapped) == (None, 'unmapped')
    assert set(CATEGORIES) == {'customer', 'employee', 'customer_employee', 'no_one'}


def test_hysteresis_holds_change_until_it_persists():
    tracker = OccupancyTracker(OccupancyPolicy(hold_windows=2))
    states = [tracker.update(o) for o in (obs(0, customer_s=40), obs(1, customer_s=30, employee_s=10),
                                          obs(2, customer_s=30, employee_s=10), obs(3, employee_s=50))]
    assert [s.category for s in states] == ['customer', 'customer', 'customer_employee', 'customer_employee']
    assert [s.pending for s in states] == [None, 'customer_employee', None, 'employee']
    assert states[1].observed_category == 'customer_employee'


def test_flicker_does_not_change_published_category():
    tracker = OccupancyTracker(OccupancyPolicy(hold_windows=2))
    seq = [obs(0, customer_s=40), obs(1), obs(2, customer_s=40), obs(3), obs(4, customer_s=40)]
    assert [tracker.update(o).category for o in seq] == ['customer'] * 5


def test_occlusion_masks_and_resets_pending_change():
    tracker = OccupancyTracker(OccupancyPolicy(hold_windows=2))
    states = [tracker.update(o) for o in (obs(0, customer_s=40), obs(1), obs(2, observed=10), obs(3), obs(4))]
    assert [(s.category, s.quality) for s in states] == [
        ('customer', 'ok'), ('customer', 'ok'), (None, 'insufficient_coverage'), ('customer', 'ok'), ('no_one', 'ok')]


def test_gap_between_windows_starts_fresh():
    tracker = OccupancyTracker()
    tracker.update(obs(0, customer_s=40))
    later = tracker.update(obs(5))
    assert later.category == 'no_one' and later.pending is None


def test_cells_are_independent_and_ids_are_not_roles():
    tracker = OccupancyTracker()
    a = tracker.update(obs(0, cell='aisle-3', customer_s=40))
    b = tracker.update(obs(0, cell='aisle-4', employee_s=40))
    assert (a.cell_id, a.category, b.cell_id, b.category) == ('aisle-3', 'customer', 'aisle-4', 'employee')


def test_invalid_states_and_observations_are_rejected():
    with pytest.raises(ValidationError):
        CellObservation(cell_id='c', window=window(0), observed_s=61, map_version='m')
    with pytest.raises(ValidationError):
        CellState(cell_id='c', window=window(0), category='no_one', quality='insufficient_coverage',
                  observed_category=None, map_version='m', policy_version='p')
    with pytest.raises(ValidationError):
        CellState(cell_id='c', window=window(0), category='unknown', quality='ok', observed_category='no_one',
                  map_version='m', policy_version='p')


def test_layers_keep_quantities_separate_and_mask_blind_cells():
    observations = [obs(0, cell='a', customer_s=40, employee_s=5), obs(0, cell='b', observed=10, customer_s=10),
                    obs(0, cell='c', unknown_role_s=30, employee_s=12)]
    customer, employee = presence_layers(observations, window(0))
    assert customer.unit == 'seconds' and customer.map_version == 'fixture-map-v1'
    assert [(c.cell_id, c.value, c.masked_reason) for c in customer.cells] == [
        ('a', 40, None), ('b', None, 'insufficient_coverage'), ('c', 0, None)]
    assert [c.value for c in employee.cells] == [5, None, 12]
    confirmed, unverified = interaction_layers([('a', 'interaction'), ('a', 'interaction'), ('c', 'unverified'),
                                                ('b', 'pass_by')], window(0), 'fixture-map-v1')
    assert [(c.cell_id, c.value) for c in confirmed.cells] == [('a', 2)]
    assert [(c.cell_id, c.value) for c in unverified.cells] == [('c', 1)]
    with pytest.raises(ValueError):
        presence_layers([obs(0), obs(1)], window(0))
