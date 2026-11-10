from datetime import timedelta
import sqlite3

import pytest

from .contracts import CoverageRequest, TimeWindow, UnattendedRequest
from .test_read_tools import START, WINDOW, database, event, put, scope
from .tools.common import ObservationContext
from .tools.contextual import SQLiteAnalyticsTools


def tools(path, *, cameras=('c1',), windows=(), shift=None, zone='z1'):
    context = ObservationContext(context_id='synthetic-operating-policy', store_id='store-1', zone_id=zone,
                                 camera_ids=cameras, operating_windows=windows, shift=shift,
                                 available_sources=('footfall', 'zone_dwell', 'interactions', 'unattended_episodes'))
    return SQLiteAnalyticsTools(path, synthetic=True, contexts=(context,))


def test_unattended_threshold_uses_stored_wait_and_clips_output(database):
    put(database, 'unattended_episodes', [event('u1', 0, 300, customer_track_id=7, waited_s=300, helped=1),
        event('u2', 0, 180, customer_track_id=8, waited_s=180, helped=0),
        event('short', 0, 100, customer_track_id=9, waited_s=100, helped=0),
        event('other-store', 0, 300, customer_track_id=7, waited_s=300, helped=1, store_id='store-2')])
    window = TimeWindow(start=START+timedelta(seconds=120), end=START+timedelta(seconds=240))
    result = tools(database).get_unattended(scope=scope(), request=UnattendedRequest(window=window, min_seconds=180, limit=1))
    assert result.status == 'partial' and result.truncated and result.episode_count.value == 2
    episode = result.episodes[0]
    assert episode.event_id == 'u1' and episode.waited.value == 120 and episode.helped
    assert episode.provenance == 'stored_derivation_verdict_unfiltered'
    assert episode.waited.evidence[0].ids == ('u1',)
    assert result.episode_count.evidence[0].ids == ('u1', 'u2')
    assert 'does not filter interaction verdict' in result.limitations[0]


def test_coverage_merges_overlapping_staff_and_clips_to_trusted_open_window(database):
    put(database, 'zone_dwell', [event('e1', 0, 300, track_id=1, role='employee', dwell_s=300),
        event('e2', 120, 420, track_id=2, role='employee', dwell_s=300),
        event('customer', 0, 600, track_id=3, role='customer', dwell_s=600),
        event('other', 0, 600, store_id='store-2', track_id=1, role='employee', dwell_s=600)])
    opened = TimeWindow(start=START+timedelta(seconds=60), end=START+timedelta(seconds=540))
    result = tools(database, windows=(opened,)).get_coverage(scope=scope(), request=CoverageRequest(window=WINDOW))
    row = result.zones[0]
    assert result.status == 'ok'
    assert row.observed_staffed.value == 360 and row.open_seconds.value == 480
    assert row.unknown_observation.value == 0 and row.staffed_open_ratio.value == .75
    assert row.evaluated_windows == (opened,) and row.operating_windows == (opened,)
    assert row.operating_context_id == 'synthetic-operating-policy'
    assert row.observed_staffed.evidence[0].ids == ('e1', 'e2')


def test_blocked_health_overrides_overlapping_healthy_record(database):
    put(database, 'zone_dwell', [event('e1', 0, 420, track_id=1, role='employee', dwell_s=420)])
    put(database, 'pipeline_health', [event('blocked', 240, 360, fps=10, id_churn=0, frozen_or_dark=1)])
    result = tools(database, windows=(WINDOW,)).get_coverage(scope=scope(), request=CoverageRequest(window=WINDOW))
    row = result.zones[0]
    assert result.status == 'partial'
    assert row.observed_staffed.value == 300 and row.unknown_observation.value == 120
    assert row.open_seconds.value == 600 and row.staffed_open_ratio.value is None
    assert row.unknown_observation.evidence[0].ids == ('h1', 'blocked')


def test_expected_missing_camera_and_scope_restriction_never_mean_zero_staff(database):
    result = tools(database, cameras=('c1','c2')).get_coverage(scope=scope(), request=CoverageRequest(window=WINDOW))
    assert result.zones[0].unknown_observation.value == 600
    restricted = tools(database, cameras=('c1','c2')).get_coverage(scope=scope(allowed_camera_ids=('c1',)), request=CoverageRequest(window=WINDOW))
    assert restricted.zones[0].observed_staffed.value is None
    assert restricted.zones[0].unknown_observation.value is None


def test_no_open_hours_no_ratio_and_no_shift_fallback(database):
    result = tools(database).get_coverage(scope=scope(), request=CoverageRequest(window=WINDOW))
    assert result.zones[0].observed_staffed.value == 0
    assert result.zones[0].unknown_observation.value == 0
    assert result.zones[0].open_seconds.value is None and result.zones[0].staffed_open_ratio.value is None
    bad = tools(database).get_coverage(scope=scope(), request=CoverageRequest(window=WINDOW, shift='night'))
    assert bad.status == 'unavailable' and not bad.zones
    configured = tools(database, windows=(WINDOW,), shift='day').get_coverage(scope=scope(), request=CoverageRequest(window=WINDOW, shift='day'))
    assert configured.zones[0].staffed_open_ratio.value == 0


def test_camera_wide_health_can_support_authorized_non_home_zone(database):
    put(database, 'zone_dwell', [event('e3', 0, 60, zone_id='z3', track_id=1, role='employee', dwell_s=60)])
    result = tools(database, zone='z3', windows=(WINDOW,)).get_coverage(
        scope=scope(allowed_zone_ids=('z3',)), request=CoverageRequest(window=WINDOW, filters={'zone_id':'z3'}))
    assert result.zones[0].observed_staffed.value == 60 and result.zones[0].unknown_observation.value == 0
    assert result.zones[0].staffed_open_ratio.value == .1


@pytest.mark.parametrize('table', ['pipeline_health', 'zone_dwell', 'unattended_episodes'])
def test_contextual_missing_sources_preserve_unavailability(database, table):
    with sqlite3.connect(database) as conn:
        conn.execute(f'DROP TABLE {table}')  # fixed test setup, not a public SQL tool
    if table == 'unattended_episodes':
        result = tools(database).get_unattended(scope=scope(), request=UnattendedRequest(window=WINDOW))
        assert result.status == 'unavailable' and result.episode_count.value is None
    else:
        result = tools(database).get_coverage(scope=scope(), request=CoverageRequest(window=WINDOW))
        if table == 'zone_dwell':
            assert result.status == 'unavailable'
        else:
            assert result.zones[0].observed_staffed.value is None
            assert result.zones[0].unknown_observation.value is None
