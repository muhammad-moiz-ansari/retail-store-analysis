"""Clip Review: clip mapping, blind mode, verdict storage, precision and agreement. SYNTHETIC FIXTURE only."""
from datetime import timedelta

import pytest
from pydantic import ValidationError

from ..tools.registry import ScopedToolRegistry
from .clip_review import (RecordingSource, ReviewLedger, ReviewVerdict, agreement, from_interaction_rows,
                          from_unattended, review_items, summarise)
from .fixture_tools import FixtureAnalyticsTools
from .test_customer_behavior import DAY, START, scope

SOURCE = RecordingSource(run_id='fixture-run', camera_id='fixture-cam', store_id='store-1', video_ref='fixture-clip-01',
                         started_at=START, duration_s=1200)
ROWS = [dict(event_id=f'i{n}', run_id='fixture-run', store_id='store-1', camera_id='fixture-cam', zone_id='z1',
             ts_start=(START + timedelta(seconds=s)).isoformat(), ts_end=(START + timedelta(seconds=e)).isoformat(), verdict=v)
        for n, (s, e, v) in enumerate([(1, 20, 'interaction'), (100, 130, 'interaction'), (300, 300, 'unverified'),
                                       (1190, 1199, 'interaction'), (5000, 5010, 'interaction'), (40, 50, 'pass_by')])]


def at(minutes):
    return (START + timedelta(minutes=minutes)).isoformat()


def candidates():
    return from_interaction_rows(ROWS, synthetic=True)


def test_clips_are_padded_and_clamped_to_the_recording():
    items = {i.event_id: i for i in review_items(candidates(), [SOURCE])}
    assert set(items) == {'i0', 'i1', 'i2', 'i3', 'i4'}  # pass_by is not a reviewable verdict
    assert (items['i0'].clip.offset_start_s, items['i0'].clip.offset_end_s) == (0, 23)
    assert (items['i1'].clip.offset_start_s, items['i1'].clip.offset_end_s) == (97, 133)
    assert items['i2'].window.end - items['i2'].window.start == timedelta(seconds=1)
    assert items['i3'].clip.offset_end_s == 1200
    assert items['i4'].clip is None and items['i4'].unavailable_reason == 'outside_recording'
    assert all(i.synthetic for i in items.values())


def test_missing_recording_and_blind_mode():
    other = RecordingSource(**SOURCE.model_dump() | {'camera_id': 'other-cam'})
    items = review_items(candidates(), [other], blind=True)
    assert {i.unavailable_reason for i in items} == {'no_recording'}
    assert {i.cv_verdict for i in items} == {None}
    with pytest.raises(ValidationError):
        RecordingSource(**SOURCE.model_dump() | {'video_ref': '../../etc/passwd'})


def test_unattended_candidates_come_from_scoped_results():
    rows = [dict(event_id='u1', zone_id='z2', waited_s=240), dict(event_id='u2', zone_id='z2', waited_s=300, helped=True)]
    result = ScopedToolRegistry(FixtureAnalyticsTools(unattended=rows), scope()).invoke(
        'get_unattended', {'window': DAY.model_dump(mode='json')})
    found = from_unattended(result)
    assert [(c.event_id, c.cv_verdict, c.synthetic) for c in found] == [('u1', 'unhelped', True), ('u2', 'helped', True)]


def test_precision_uses_only_decisive_reviews_and_latest_verdict():
    ledger = ReviewLedger({c.event_id for c in candidates()})
    for event, decision in (('i0', 'confirmed'), ('i1', 'rejected'), ('i2', 'confirmed'), ('i3', 'unsure')):
        ledger.record(ReviewVerdict(event_id=event, reviewer_id='ruhab', decision=decision, reviewed_at=at(1)))
    ledger.record(ReviewVerdict(event_id='i1', reviewer_id='ruhab', decision='confirmed', reviewed_at=at(2)))
    ledger.record(ReviewVerdict(event_id='i1', reviewer_id='ruhab', decision='rejected', reviewed_at=at(0)))  # older, ignored
    summary = summarise(candidates(), ledger)
    rows = {(r.kind, r.cv_verdict): r for r in summary.by_verdict}
    confirmed = rows[('interaction', 'interaction')]
    assert (confirmed.events, confirmed.confirmed, confirmed.rejected, confirmed.unsure, confirmed.pending) == (4, 2, 0, 1, 1)
    assert confirmed.precision == 1.0
    assert rows[('interaction', 'unverified')].precision == 1.0 and summary.synthetic
    with pytest.raises(ValueError):
        ledger.record(ReviewVerdict(event_id='not-in-set', reviewer_id='ruhab', decision='confirmed', reviewed_at=at(1)))


def test_disagreeing_reviewers_make_an_event_unsure_and_kappa_is_reported():
    ledger = ReviewLedger()
    pairs = [('i0', 'confirmed', 'confirmed'), ('i1', 'rejected', 'rejected'), ('i2', 'confirmed', 'rejected'),
             ('i3', 'confirmed', 'confirmed')]
    for event, a, b in pairs:
        ledger.record(ReviewVerdict(event_id=event, reviewer_id='ruhab', decision=a, reviewed_at=at(1)))
        ledger.record(ReviewVerdict(event_id=event, reviewer_id='second', decision=b, reviewed_at=at(1)))
    summary = summarise(candidates(), ledger, second_reviewer_pair=('ruhab', 'second'))
    assert summary.agreement.shared_events == 4 and summary.agreement.percent_agreement == 0.75
    assert summary.agreement.cohen_kappa == pytest.approx(0.5)  # po=.75, pe=.5
    unverified = next(r for r in summary.by_verdict if r.cv_verdict == 'unverified')
    assert (unverified.unsure, unverified.precision) == (1, None)
    assert agreement(ledger.verdicts(), 'ruhab', 'nobody').cohen_kappa is None


def test_synthetic_and_real_events_are_not_mixed():
    real = from_interaction_rows(ROWS[:1], synthetic=False)
    with pytest.raises(ValueError):
        summarise(candidates() + real, ReviewLedger())
    assert summarise((), ReviewLedger()).synthetic is None
