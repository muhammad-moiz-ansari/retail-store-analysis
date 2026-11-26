import pytest

from backend.events.live_zones import LiveZone, state_of

E, C, U = {"role": "employee"}, {"role": "customer"}, {"role": "unknown"}


def run(zone: LiveZone, frames: list[tuple[float, list[dict]]], observed=True) -> dict:
    state = zone.snapshot()
    for t, people in frames:
        state = zone.update(people, t, observed)
    return state


def test_the_four_states_come_from_the_ratio_of_customers_to_employees():
    assert state_of(employees=0, customers=2) == "hot"
    assert state_of(employees=1, customers=2) == "hot"  # more customers than employees
    assert state_of(employees=1, customers=1) == "gray"
    assert state_of(employees=3, customers=2) == "gray"
    assert state_of(employees=2, customers=0) == "green"
    assert state_of(employees=0, customers=0) == "inactive"


def test_the_ratio_is_a_setting():
    # One employee covers up to two customers: three is hot, two is not.
    assert state_of(employees=1, customers=2, hot_ratio=2.0) == "gray"
    assert state_of(employees=1, customers=3, hot_ratio=2.0) == "hot"
    assert state_of(employees=0, customers=1, hot_ratio=2.0) == "hot"
    zone = LiveZone(hold_s=0.0, hot_ratio=2.0)
    assert run(zone, [(0.0, [C, C, E]), (1.0, [C, C, E])])["view"] == "gray"
    assert run(zone, [(2.0, [C, C, C, E])])["view"] == "hot"
    assert zone.snapshot()["hot_ratio"] == 2.0


def test_a_second_customer_turns_a_staffed_zone_hot():
    zone = LiveZone(hold_s=1.0)
    assert run(zone, [(float(t), [C, E]) for t in range(0, 3)])["view"] == "gray"
    assert run(zone, [(float(t), [C, C, E]) for t in range(3, 6)])["view"] == "hot"
    assert run(zone, [(float(t), [C, C, E, E]) for t in range(6, 9)])["view"] == "gray"


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


def customer(track: int) -> dict:
    return {"role": "customer", "track_id": track}


def talk(track: int, at: float, verdict: str = "interaction") -> dict:
    return {"employee_track_id": 1, "customer_track_id": track, "last_seen_at": at, "verdict": verdict}


def test_attending_every_customer_makes_an_outnumbered_zone_gray_until_the_timeframe_runs_out():
    zone = LiveZone(hold_s=0.0, served_s=30.0)
    two = [E, customer(7), customer(8)]
    assert zone.update(two, 0.0)["view"] == "hot"  # two customers, one employee
    assert zone.update(two, 5.0, interactions=[talk(7, 5.0)])["view"] == "hot"  # one of the two attended
    state = zone.update(two, 10.0, interactions=[talk(8, 10.0)])
    assert state["view"] == "gray" and state["all_customers_attended"]
    assert zone.update(two, 34.0)["view"] == "gray"  # both still inside 30 s
    assert zone.update(two, 36.0)["view"] == "hot"  # customer 7 was last attended at 5 s
    # A newcomer nobody has attended makes it hot again; attending them makes it gray.
    zone.update(two, 40.0, interactions=[talk(7, 40.0), talk(8, 40.0)])
    assert zone.update(two + [customer(9)], 41.0)["view"] == "hot"
    assert zone.update(two + [customer(9)], 42.0, interactions=[talk(9, 42.0)])["view"] == "gray"


def test_attended_customers_stay_gray_after_the_employee_leaves_and_rejected_pairs_do_not_count():
    zone = LiveZone(hold_s=0.0, served_s=30.0)
    zone.update([E, customer(7)], 0.0, interactions=[talk(7, 0.0)])
    assert zone.update([customer(7)], 10.0)["view"] == "gray"  # customer alone, attended 10 s ago
    assert zone.update([customer(7)], 31.0)["view"] == "hot"
    rejected = LiveZone(hold_s=0.0)
    assert rejected.update([E, customer(7), customer(8)], 0.0, interactions=[talk(7, 0.0, "no_interaction"), talk(8, 0.0, "no_interaction")])["view"] == "hot"
    unchecked = LiveZone(hold_s=0.0)
    assert unchecked.update([E, customer(7), customer(8)], 0.0, interactions=[talk(7, 0.0, "unverified"), talk(8, 0.0, "unverified")])["view"] == "gray"


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


@pytest.mark.parametrize("kwargs", [{"hold_s": -1}, {"max_gap_s": 0}, {"hot_ratio": 0}, {"served_s": -1}])
def test_invalid_settings_are_rejected(kwargs):
    with pytest.raises(ValueError):
        LiveZone(**kwargs)
