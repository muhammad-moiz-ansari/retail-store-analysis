"""Customer Behavior Agent through the real graph, using SYNTHETIC FIXTURE tools only."""
from datetime import datetime, timedelta, timezone
import socket

import pytest

from ..contracts import EventFilters, TimeWindow, TrustedAccessScope
from ..graph import run_analytics
from ..graph_contracts import AskRequest, GroundingIssue, RouteDecision, SpecialistDraft
from ..tools.registry import ScopedToolRegistry
from .customer_behavior import customer_behavior_agent, customer_behavior_registration, granularity, intents
from .fixture_tools import FIXTURE_NOTE, FixtureAnalyticsTools

START = datetime(2026, 11, 3, 9, tzinfo=timezone.utc)
DAY = TimeWindow(start=START, end=START + timedelta(hours=8))
HOURLY = [3, 9, 14, 6, 2, 11, 5, 4]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: (_ for _ in ()).throw(AssertionError('offline only')))


def scope():
    return TrustedAccessScope(actor_id='fixture-manager', store_id='store-1', role='manager')


def hourly(window):
    index = int((window.start - START).total_seconds() // 3600)
    return HOURLY[index], max(0, HOURLY[index] - 1)


def ask(question, tools, window=DAY, **filters):
    request = AskRequest(question=question, window=window, filters=EventFilters(**filters))
    return run_analytics(request, ScopedToolRegistry(tools, scope()),
                         router=lambda r, s: RouteDecision(target='customer_behavior'),
                         specialists={'customer_behavior': customer_behavior_registration()})


def values(run):
    return {claim.path: claim.value for claim in run.claims}


def test_intents_and_granularity():
    assert intents('What was the busiest hour?') == ('footfall',)
    assert intents('How long did customers dwell and were they assisted?') == ('dwell', 'interactions')
    assert intents('Summarise customers today') == ('footfall', 'interactions', 'unattended')
    assert granularity(TimeWindow(start=START, end=START + timedelta(minutes=30))) == 'minute'
    assert granularity(DAY) == 'hour'
    assert granularity(TimeWindow(start=START, end=START + timedelta(days=7))) == 'day'


def test_footfall_reports_peak_and_quietest_full_bucket():
    run = ask('Show footfall traffic', FixtureAnalyticsTools(footfall=hourly))
    assert run.status == 'ok' and not run.development_stub
    assert values(run) == {('buckets', 2, 'entries'): 14, ('buckets', 2, 'exits'): 13, ('buckets', 4, 'entries'): 2}
    assert 'Development adapter' not in run.response
    assert FIXTURE_NOTE in run.limitations and all(r.synthetic for r in run.tool_results.values())


def test_clipped_edge_bucket_is_not_called_quietest():
    window = TimeWindow(start=START, end=START + timedelta(hours=3, minutes=10))
    run = ask('Show footfall', FixtureAnalyticsTools(footfall=lambda w: (1 if w.end - w.start < timedelta(hours=1) else 5 + w.start.hour, 0)),
              window=window)
    paths = set(values(run))
    assert ('buckets', 3, 'entries') not in paths
    assert values(run)[('buckets', 2, 'entries')] == 16 and values(run)[('buckets', 0, 'entries')] == 14


def test_unobserved_buckets_are_skipped_not_zero():
    run = ask('Show footfall', FixtureAnalyticsTools(footfall=lambda w: (None, None) if w.start.hour < 15 else (7, 2)))
    assert values(run) == {('buckets', 6, 'entries'): 7, ('buckets', 6, 'exits'): 2}


def test_dwell_needs_a_zone_and_discloses_unknown_roles():
    tools = FixtureAnalyticsTools(dwell={'z1': {'customer': (12, 1800, 95, 410), 'employee': (3, 5400, 1800, 1900), 'unknown': (2, 60, 30, 40)}})
    assert ask('How long did customers dwell?', tools).status == 'insufficient_evidence'
    assert 'zone filter is required' in ask('How long did customers dwell?', tools).response
    run = ask('How long did customers dwell?', tools, zone_id='z1')
    assert values(run) == {('by_role', 0, 'sample_count'): 12, ('by_role', 0, 'total'): 1800,
                           ('by_role', 0, 'p50'): 95, ('by_role', 0, 'p90'): 410, ('by_role', 2, 'sample_count'): 2}
    clean = ask('dwell', FixtureAnalyticsTools(dwell={'z1': {'customer': (4, 200, 50, 70)}}), zone_id='z1')
    assert ('by_role', 2, 'sample_count') not in values(clean)


def test_interactions_disclose_unverified_separately():
    run = ask('Were customers assisted?', FixtureAnalyticsTools(interactions=dict(confirmed=13, unverified=4, mean_duration=21.5, mean_approach=48, approach_samples=9)))
    assert values(run) == {('confirmed_count',): 13, ('unverified_count',): 4, ('mean_confirmed_duration',): 21.5,
                           ('mean_approach',): 48, ('approach_sample_count',): 9}


def test_zero_confirmed_keeps_count_but_not_fake_duration():
    run = ask('interactions', FixtureAnalyticsTools(interactions=dict(confirmed=0, unverified=2)))
    assert values(run) == {('confirmed_count',): 0, ('unverified_count',): 2}


def test_unattended_longest_unhelped_wait():
    rows = [dict(event_id='u1', zone_id='z1', waited_s=240, helped=True),
            dict(event_id='u2', zone_id='z2', waited_s=200),
            dict(event_id='u3', zone_id='z1', waited_s=600, helped=True),
            dict(event_id='u4', zone_id='z3', waited_s=320)]
    run = ask('Which customers were left waiting?', FixtureAnalyticsTools(unattended=rows))
    assert run.status == 'partial'  # stored derivation provenance is always disclosed
    assert values(run) == {('episode_count',): 4, ('episodes', 3, 'waited'): 320}
    assert any('helped is not confirmed' in note for note in run.limitations)


def test_overview_and_unavailable_sources_publish_nothing_false():
    run = ask('Summarise customers today', FixtureAnalyticsTools(footfall=hourly, status={'get_interactions': 'unavailable'}))
    assert [c.tool for c in run.tool_calls] == ['get_footfall', 'get_interactions', 'get_unattended']
    assert set(values(run)) == {('buckets', 2, 'entries'), ('buckets', 2, 'exits'), ('buckets', 4, 'entries')}
    assert run.status == 'partial'
    nothing = ask('Show footfall', FixtureAnalyticsTools())
    assert nothing.status == 'unavailable' and not nothing.claims


def test_repair_only_drops_rejected_claims():
    tools = FixtureAnalyticsTools(interactions=dict(confirmed=2, unverified=1))
    first = ask('interactions', tools)
    prior = SpecialistDraft(claims=first.claims, notices=('zone_required',))
    fixed = customer_behavior_agent(None, None, prior, (GroundingIssue(claim_index=0, code='wrong_value'),))
    assert fixed.claims == first.claims[1:] and fixed.notices == ('zone_required',)
