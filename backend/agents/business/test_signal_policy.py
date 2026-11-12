"""Signal policy decisions and adapter hand-off, SYNTHETIC FIXTURE tools and FAKE handler only."""
from datetime import timedelta

from ..operational import DispatchOutcome, OperationalDispatchAdapter, TrustedOperationalScope
from ..tools.registry import ScopedToolRegistry
from .fixture_tools import FixtureAnalyticsTools
from .signal_policy import SignalPolicy, evaluate_zone, unattended_decision
from .test_customer_behavior import DAY, offline, scope  # noqa: F401

NOW = DAY.end + timedelta(seconds=5)
WAITS = [dict(event_id='u1', zone_id='z2', waited_s=240), dict(event_id='u2', zone_id='z2', waited_s=90),
         dict(event_id='u3', zone_id='z2', waited_s=900, helped=True), dict(event_id='u4', zone_id='z1', waited_s=500)]
COVERAGE = {'z1': dict(staffed=20000, unknown=0, open=28800, ratio=0.69),
            'z2': dict(staffed=2000, unknown=600, open=28800, ratio=0.07),
            'z3': dict(staffed=1000, unknown=9000, open=28800, ratio=0.03),
            'z4': dict(staffed=500, unknown=0)}
DWELL = {z: {'customer': (6, 900, 120, 300)} for z in ('z1', 'z2', 'z3', 'z4')} | {'z5': {'customer': (0, 0, None, None)}}


def registry(**overrides):
    scenario = dict(unattended=WAITS, coverage=COVERAGE, dwell=DWELL) | overrides
    return ScopedToolRegistry(FixtureAnalyticsTools(**scenario), scope())


def decide(zone, **overrides):
    unattended, unstaffed = evaluate_zone(registry(**overrides), zone, DAY, NOW)
    return unattended, unstaffed


def test_understaffed_zone_with_waiting_customer_emits_both_events():
    unattended, unstaffed = decide('z2')
    assert (unattended.reason, unstaffed.reason) == ('emitted', 'emitted')
    assert unattended.event.event_type == 'unattended_customer' and unattended.event.source == 'customer_behavior'
    assert unattended.event.severity == 'medium'
    assert {i for ref in unattended.event.evidence.demand.evidence for i in ref.ids} == {'u1'}  # helped/short waits excluded
    assert unstaffed.event.severity == 'high' and unstaffed.event.source == 'employee_activity'
    assert unattended.event.evidence.demand.synthetic and unattended.event.window == DAY
    assert any('helped is not confirmed' in note for note in unattended.event.evidence.demand.limitations)


def test_well_staffed_zone_flags_long_wait_but_not_unstaffed():
    unattended, unstaffed = decide('z1')
    assert unattended.reason == 'emitted' and unattended.event.severity == 'high'
    assert unstaffed.reason == 'staffed_enough' and unstaffed.event is None


def test_blind_zone_is_suppressed_not_called_unstaffed():
    unattended, unstaffed = decide('z3', unattended=WAITS + [dict(event_id='u9', zone_id='z3', waited_s=400)])
    assert unattended.reason == unstaffed.reason == 'unknown_observation_too_high'


def test_missing_inputs_suppress_with_reasons():
    assert decide('z4')[1].reason == 'no_operating_window'
    assert decide('z5')[1].reason == 'no_demand'
    assert decide('z2', coverage=None)[0].reason == 'coverage_unavailable'
    assert decide('z2', unattended=None)[0].reason == 'demand_unavailable'
    assert decide('z9')[0].reason == 'no_demand' and decide('z9')[1].reason == 'demand_unavailable'
    strict = SignalPolicy(max_unknown_share=0.01)
    reg = registry()
    args = {'window': DAY.model_dump(mode='json'), 'filters': {'zone_id': 'z2'}}
    decision = unattended_decision('z2', DAY, NOW, reg.invoke('get_unattended', args), reg.invoke('get_coverage', args), strict)
    assert decision.reason == 'unknown_observation_too_high'


def test_ids_are_stable_and_the_fake_handler_sees_a_duplicate():
    first, second = decide('z2')[0].event, decide('z2')[0].event
    assert first == second and first.event_id.startswith('evt-')
    ledger = {}

    def fake_handler(*, event, scope):  # FAKE: no task, employee or voice message exists
        seen = (event.store_id, event.idempotency_key) in ledger
        ledger[(event.store_id, event.idempotency_key)] = True
        identity = dict(event_id=event.event_id, idempotency_key=event.idempotency_key, store_id=event.store_id, zone_id=event.zone_id)
        return DispatchOutcome(**identity, decision='duplicate') if seen else DispatchOutcome(
            **identity, decision='dispatched', task_id='fake-task', selected_employee_id='fake-employee')

    adapter = OperationalDispatchAdapter(fake_handler)
    producer = TrustedOperationalScope(service_id='fixture-producer', store_id='store-1', allowed_zone_ids=('z1', 'z2'))
    assert adapter.handle(first, scope=producer).decision == 'dispatched'
    assert adapter.handle(second, scope=producer).decision == 'duplicate'
    assert adapter.handle(first, scope=producer).synthetic


def test_policy_version_changes_identity():
    reg = registry()
    args = {'window': DAY.model_dump(mode='json'), 'filters': {'zone_id': 'z2'}}
    inputs = (reg.invoke('get_unattended', args), reg.invoke('get_coverage', args))
    a = unattended_decision('z2', DAY, NOW, *inputs).event
    b = unattended_decision('z2', DAY, NOW, *inputs, SignalPolicy(version='ruhab-signal-policy-v2')).event
    assert a.idempotency_key != b.idempotency_key
