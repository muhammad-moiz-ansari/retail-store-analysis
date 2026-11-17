import pytest

from backend.events.live_zones import LiveZone, state_of

E, C, U = {"role": "employee"}, {"role": "customer"}, {"role": "unknown"}


def run(zone: LiveZone, frames: list[tuple[float, list[dict]]], observed=True) -> dict:
    state = zone.snapshot()
    for t, people in frames:
        state = zone.update(people, t, observed)
    return state


def test_the_four_states_come_from_who_is_in_view():
    assert state_of(employees=0, customers=2) == "hot"
    assert state_of(employees=1, customers=1) == "gray"
    assert state_of(employees=2, customers=0) == "green"
    assert state_of(employees=0, customers=0) == "inactive"


def test_a_state_shows_after_it_has_held_and_time_is_added_per_state():
    zone = LiveZone(hold_s=1.5)
    assert zone.snapshot()["view"] == "starting"
    assert run(zone, [(0.0, [C]), (1.0, [C])])["view"] == "starting"  # held 1 s so far
    assert run(zone, [(2.0, [C])])["view"] == "hot"
    assert run(zone, [(t / 2, [C, E]) for t in range(5, 12)])["view"] == "gray"
    assert run(zone, [(t / 2, [E]) for t in range(12, 20)])["view"] == "green"
    state = run(zone, [(t / 2, []) for t in range(20, 30)])
    assert state["view"] == "inactive" and (state["employees"], state["customers"]) == (0, 0)
    seconds = state["view_seconds"]
    assert all(seconds[name] > 0 for name in ("hot", "gray", "green", "inactive"))
    assert sum(seconds.values()) == pytest.approx(14.5 - 1.0)  # all but the first second, which was still "starting"


def test_a_missed_detection_or_brief_role_flip_does_not_change_the_zone():
    zone = LiveZone(hold_s=1.5)
    run(zone, [(t / 2, [C, E]) for t in range(0, 8)])
    assert run(zone, [(4.0, [C]), (4.5, [C])])["view"] == "gray"  # employee missed for 1 s
    assert run(zone, [(5.0, [C, E])])["view"] == "gray"
    assert run(zone, [(5.5, [C]), (6.0, [E]), (6.5, [C]), (7.0, [E])])["view"] == "gray"  # no state held 1.5 s
    assert zone.snapshot()["view_seconds"]["hot"] == 0.0


def test_unknown_people_and_blind_frames_never_read_as_inactive():
    zone = LiveZone(hold_s=1.0)
    run(zone, [(float(t), [C]) for t in range(0, 4)])
    assert run(zone, [(float(t), [U]) for t in range(4, 10)])["view"] == "hot"  # unknown role settles nothing
    assert run(zone, [(float(t), []) for t in range(10, 20)], observed=False)["view"] == "hot"  # camera blind
    assert zone.snapshot()["view_seconds"]["inactive"] == 0.0
    blind = LiveZone(hold_s=1.0)
    assert run(blind, [(float(t), []) for t in range(0, 30)], observed=False)["view"] == "starting"
    # Unknown people alongside a known role do not block it.
    assert run(LiveZone(hold_s=1.0), [(float(t), [U, E]) for t in range(0, 3)])["view"] == "green"


def test_an_outage_is_capped_and_a_clock_reset_starts_over():
    zone = LiveZone(hold_s=0.0, max_gap_s=2.0)
    state = run(zone, [(0.0, [E]), (30.0, [E])])
    assert state["view_seconds"]["green"] == 2.0
    state = zone.update([E], 1.0)
    assert state["view_seconds"]["green"] == 0.0 and state["view"] == "green"


@pytest.mark.parametrize("kwargs", [{"hold_s": -1}, {"max_gap_s": 0}])
def test_invalid_settings_are_rejected(kwargs):
    with pytest.raises(ValueError):
        LiveZone(**kwargs)
