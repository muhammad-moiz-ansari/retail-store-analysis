"""Employee Activity Agent through the real graph and service, SYNTHETIC FIXTURE tools only."""
from datetime import timedelta

from ..contracts import EventFilters, TimeWindow
from ..graph import run_analytics
from ..graph_contracts import AskRequest, RouteDecision
from ..service import AnalyticsService
from ..tools.registry import ScopedToolRegistry
from .employee_activity import business_specialists, employee_activity_registration, intents
from .fixture_tools import FIXTURE_NOTE, FixtureAnalyticsTools
from .test_customer_behavior import DAY, START, offline, scope, values  # noqa: F401  (offline is an autouse fixture)

ZONES = {
    'z1': dict(staffed=20000, unknown=0, open=28800, ratio=0.69),
    'z2': dict(staffed=4000, unknown=1200, open=28800, ratio=0.14),
    'z3': dict(staffed=900, unknown=300),  # no operating window supplied
    'z4': dict(staffed=27000, unknown=0, open=28800, ratio=0.94),
}


def ask(question, tools, **filters):
    request = AskRequest(question=question, window=DAY, filters=EventFilters(**filters))
    return run_analytics(request, ScopedToolRegistry(tools, scope()),
                         router=lambda r, s: RouteDecision(target='employee_activity'),
                         specialists={'employee_activity': employee_activity_registration()})


def test_intents_default_to_coverage():
    assert intents('How is the floor looking?') == ('coverage',)
    assert intents('Where are the staffing gaps and were customers missed?') == ('coverage', 'unattended')


def test_coverage_orders_largest_gap_first_and_discloses_blind_time():
    run = ask('Where are the staffing gaps?', FixtureAnalyticsTools(coverage=ZONES))
    assert run.status == 'ok' and not run.development_stub
    zone_of = {claim.path: run.tool_results[claim.call_id].zones[claim.path[1]].zone_id for claim in run.claims}
    order = list(dict.fromkeys(zone_of.values()))
    assert order == ['z2', 'z1', 'z4', 'z3']
    assert values(run)[('zones', 1, 'unknown_observation')] == 1200
    assert ('zones', 0, 'unknown_observation') not in values(run)   # zero blind time is not repeated
    assert ('zones', 2, 'staffed_open_ratio') not in values(run)     # z3 has no operating window
    assert 'z2' in run.response.splitlines()[0]


def test_coverage_claims_respect_the_budget():
    many = {f'z{i:02d}': dict(staffed=100 * i, unknown=5, open=3600, ratio=round(i / 40, 3)) for i in range(1, 30)}
    run = ask('coverage', FixtureAnalyticsTools(coverage=many))
    assert 0 < len(run.claims) <= 30 and len(run.claims) % 3 == 0


def test_engagement_and_missed_customers():
    rows = [dict(event_id='u1', zone_id='z2', waited_s=420), dict(event_id='u2', zone_id='z1', waited_s=200, helped=True)]
    run = ask('Did staff engage customers or miss any?', FixtureAnalyticsTools(
        interactions=dict(confirmed=5, unverified=2, mean_duration=30), unattended=rows))
    assert values(run) == {('confirmed_count',): 5, ('mean_confirmed_duration',): 30, ('unverified_count',): 2,
                           ('episode_count',): 2, ('episodes', 0, 'waited'): 420}


def test_missing_coverage_context_is_unavailable_not_unstaffed():
    run = ask('coverage', FixtureAnalyticsTools())
    assert run.status == 'unavailable' and not run.claims


def test_service_registers_both_business_agents():
    service = AnalyticsService(FixtureAnalyticsTools(coverage=ZONES), specialists=business_specialists())
    run = service.ask(AskRequest(question='Show staffed coverage', window=DAY), scope=scope())
    assert run.selected_node == 'employee_activity' and not run.development_stub and run.claims
    assert run.trace_retained and service.get_run(run.run_id, scope=scope()) == run
    assert FIXTURE_NOTE in run.limitations
    customer = service.ask(AskRequest(question='Show customer footfall', window=TimeWindow(start=START, end=START + timedelta(hours=1))), scope=scope())
    assert customer.selected_node == 'customer_behavior' and customer.status == 'unavailable'
