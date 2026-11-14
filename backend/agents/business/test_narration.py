"""Digest wording from grounded claims only, SYNTHETIC FIXTURE tools only."""
import re
from datetime import timedelta

import pytest

from ..graph_contracts import AskRequest
from ..service import AnalyticsService
from .employee_activity import business_specialists
from .fixture_tools import FixtureAnalyticsTools
from .narration import build_digest
from .signal_policy import evaluate_zone
from .test_customer_behavior import DAY, hourly, offline, scope  # noqa: F401
from .test_employee_activity import ZONES
from ..tools.registry import ScopedToolRegistry

TOOLS = dict(footfall=hourly, coverage=ZONES, interactions=dict(confirmed=13, unverified=4, mean_duration=21.5, mean_approach=150, approach_samples=9),
             unattended=[dict(event_id='u1', zone_id='z2', waited_s=240)], dwell={'z2': {'customer': (6, 900, 120, 300)}})


def runs(*questions):
    service = AnalyticsService(FixtureAnalyticsTools(**TOOLS), specialists=business_specialists())
    return [service.ask(AskRequest(question=q, window=DAY), scope=scope()) for q in questions]


def test_digest_sections_and_wording():
    decisions = evaluate_zone(ScopedToolRegistry(FixtureAnalyticsTools(**TOOLS), scope()), 'z2', DAY, DAY.end + timedelta(seconds=1))
    digest = build_digest(runs('Summarise customers today', 'Show staffed coverage'), title='Tuesday digest', decisions=decisions)
    text = digest.text()
    assert [s.heading for s in digest.sections] == ['Traffic', 'Assistance', 'Waiting customers', 'Staff coverage',
                                                   'Raised for staff follow-up']
    assert 'Busiest period: 14 entries (2026-11-03 11:00–12:00 UTC)' in text
    assert 'Quietest period: 2 entries (2026-11-03 13:00–14:00 UTC)' in text
    assert 'Confirmed interactions: 13' in text and 'not counted as assistance' in text
    assert 'Average time to first approach (from first seen on camera): 2.5 min' in text
    assert 'Staffed share of open time: 14% (zone z2)' in text
    assert 'Customer left waiting in zone z2 (medium priority)' in text
    assert 'Zone short of staff in zone z2 (medium priority)' in text  # 14% is under 25% but not under 12.5%
    assert 'Average confirmed interaction length: 21.5 s' in text
    assert digest.provenance == 'synthetic' and 'NOTE: built from synthetic data' in text
    assert digest.status == 'partial' and digest.citation_count > 0  # unattended source is always partial


def test_every_printed_number_comes_from_a_claim():
    batch = runs('Summarise customers today', 'Show staffed coverage')
    digest = build_digest(batch)
    claimed = {c.value for run in batch for c in run.claims}
    body = '\n'.join(line for s in digest.sections for line in s.lines)
    for line in body.splitlines():
        line = re.sub(r'\(.*?\)', '', line)  # bracketed context holds dates/zone IDs, not figures
        for number in re.findall(r'\d+(?:\.\d+)?', line):
            value = float(number)
            assert any(abs(v - value) < 0.05 or abs(v * 100 - value) < 0.5 or abs(v / 60 - value) < 0.05
                       or abs(v / 3600 - value) < 0.05 for v in claimed), line


def test_empty_and_development_runs_are_flagged():
    service = AnalyticsService(FixtureAnalyticsTools())
    stub = service.ask(AskRequest(question='Show customer footfall', window=DAY), scope=scope())
    digest = build_digest([stub])
    assert digest.status == 'no_evidence' and not digest.sections
    assert any('development adapter' in c for c in digest.caveats)
    assert any('No supported evidence' in c for c in digest.caveats)


def test_runs_must_share_a_window():
    service = AnalyticsService(FixtureAnalyticsTools(**TOOLS), specialists=business_specialists())
    other = DAY.model_copy(update={'end': DAY.end + timedelta(hours=1)})
    with pytest.raises(ValueError):
        build_digest([service.ask(AskRequest(question='footfall', window=DAY), scope=scope()),
                      service.ask(AskRequest(question='footfall', window=other), scope=scope())])
    with pytest.raises(ValueError):
        build_digest([])


def test_page_summaries_are_short_and_every_figure_is_cited():
    from .narration import page_summary
    batch = runs('Summarise customers today', 'Show staffed coverage')
    for page in ('dashboard', 'customer-info', 'employee-info', 'alerts'):
        summary = page_summary(batch, page)
        assert 2 <= len(summary.sentences) <= 5 and summary.provenance == 'synthetic'
        assert summary.sentences[0].citations == ()  # provenance sentence first for fixture data
        for sentence in summary.sentences[1:]:
            assert sentence.citations and sentence.text.endswith('.')
    customer = page_summary(batch, 'customer-info')
    assert customer.sentences[1].text.startswith('Busiest period: 14 entries')
    alerts = page_summary(batch, 'alerts')
    assert [s.text for s in alerts.sentences[1:]] == ['Stored unattended episodes: 1.', 'Longest unhelped wait: 4.0 min (zone z2).']
    empty = page_summary(runs('Show staffed coverage'), 'customer-info')
    assert empty.sentences[-1].text.startswith('No supported figures')


def test_narrative_check_rejects_invented_numbers():
    from .narration import verify_narrative
    batch = runs('Summarise customers today', 'Show staffed coverage')
    good = 'Traffic peaked at 14 entries around 11:00 on 2026-11-03; 13 interactions were confirmed and zone z2 was staffed 14% of open time.'
    assert verify_narrative(good, batch).supported
    bad = verify_narrative('Traffic peaked at 17 entries and 1,250 customers visited.', batch)
    assert not bad.supported and bad.unsupported_numbers == ('17', '1250')
    # Zone and camera IDs are labels, not figures: the digest itself prints "zone z3".
    assert verify_narrative('Customers waited in zone z9 near camera c7.', batch).supported
