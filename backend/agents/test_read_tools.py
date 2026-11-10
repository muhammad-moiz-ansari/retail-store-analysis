"""Hand-calculated SQL-reader checks; Saqib's schema is reused only for setup."""
from datetime import datetime, timedelta, timezone
import hashlib
import sqlite3

import pytest

from backend.events.ingest import connect, insert
from .contracts import (EventFilters, FootfallRequest, InteractionsRequest, TimeWindow,
                        TrustedAccessScope, ZoneDwellRequest)
from .tools.analytics import EventAnalytics
from .tools.common import ObservationContext
from .tools.store import read_session

START = datetime(2026, 11, 3, 9, tzinfo=timezone.utc)
WINDOW = TimeWindow(start=START, end=START+timedelta(seconds=600))


def scope(**kwargs):
    return TrustedAccessScope(actor_id='manager-1', store_id='store-1', role='manager', **kwargs)


def event(key, start=0, end=None, **kwargs):
    return dict(event_id=key, run_id='r1', store_id='store-1', camera_id='c1', zone_id='z1',
                ts_start=(START+timedelta(seconds=start)).isoformat(),
                ts_end=(START+timedelta(seconds=start if end is None else end)).isoformat()) | kwargs


@pytest.fixture
def database(tmp_path):
    path = tmp_path/'events.sqlite3'
    with connect(path) as conn:
        insert(conn, 'pipeline_health', [event('h1', 0, 600, fps=10, id_churn=0, frozen_or_dark=0)])
    conn.close()
    return path


def put(path, table, rows):
    with connect(path) as conn:
        insert(conn, table, rows)
    conn.close()


def reader(path, contexts=None):
    if contexts is None:
        contexts = (ObservationContext(context_id='synthetic-layout', store_id='store-1', zone_id='z1', camera_ids=('c1',)),)
    return EventAnalytics(path, synthetic=True, contexts=contexts)


def test_footfall_utc_boundaries_and_observed_zero(database):
    put(database, 'footfall', [event('in-start', track_id=1, direction='in'),
        event('out-minute', 60, track_id=2, direction='out'), event('at-end', 600, track_id=3, direction='in'),
        event('last-us', 599.999999, track_id=4, direction='in')])
    request = FootfallRequest(window=WINDOW, granularity='minute')
    result = reader(database).get_footfall(scope=scope(), request=request)
    assert result.status == 'ok' and result.synthetic and result.occupancy.value is None
    assert [b.entries.value for b in result.buckets] == [1, 0, 0, 0, 0, 0, 0, 0, 0, 1]
    assert result.buckets[1].exits.value == 1
    assert result.buckets[0].exits.evidence[0].source == 'pipeline_health'
    assert result.buckets[-1].entries.evidence[0].ids == ('last-us',)
    offset = FootfallRequest(window={'start': '2026-11-03T14:00:00+05:00', 'end': '2026-11-03T14:10:00+05:00'}, granularity='minute')
    assert reader(database).get_footfall(scope=scope(), request=offset) == result


def test_scope_allows_only_store_run_camera_zone_even_without_filters(database):
    put(database, 'footfall', [event('own', track_id=1, direction='in'),
        event('other-store', store_id='store-2', track_id=1, direction='in'),
        event('other-run', run_id='r2', track_id=1, direction='in'),
        event('other-camera', camera_id='c2', track_id=1, direction='in'),
        event('other-zone', zone_id='z2', track_id=1, direction='in')])
    access = scope(allowed_run_ids=('r1',), allowed_camera_ids=('c1',), allowed_zone_ids=('z1',))
    result = reader(database).get_footfall(scope=access, request=FootfallRequest(window=WINDOW))
    assert result.buckets[0].entries.value == 1
    assert result.buckets[0].entries.evidence[0].ids == ('own',)
    with pytest.raises(ValueError):
        reader(database).get_footfall(scope=access, request=FootfallRequest(window=WINDOW, filters={'zone_id':'z2'}))
    injection = FootfallRequest(window=WINDOW, filters={'run_id': "r1' OR 1=1 --"})
    assert reader(database).get_footfall(scope=scope(), request=injection).buckets[0].entries.value is None
    with pytest.raises(PermissionError):
        reader(database).get_footfall(scope=TrustedAccessScope(actor_id='e1', store_id='store-1', role='employee'), request=FootfallRequest(window=WINDOW))


def test_missing_observation_is_null_and_missing_table_is_unavailable(database):
    result = reader(database, contexts=()).get_footfall(scope=scope(), request=FootfallRequest(window=WINDOW))
    assert result.status == 'partial' and result.buckets[0].entries.value is None
    with sqlite3.connect(database) as conn:
        conn.execute('DROP TABLE footfall')
    result = reader(database).get_footfall(scope=scope(), request=FootfallRequest(window=WINDOW))
    assert result.status == 'unavailable' and not result.buckets
    missing = database.parent/'does-not-exist.sqlite3'
    assert reader(missing).get_footfall(scope=scope(), request=FootfallRequest(window=WINDOW)).status == 'unavailable'
    assert not missing.exists()


def test_clipped_dwell_linear_quantiles_and_role_separation(database):
    put(database, 'zone_dwell', [event('d1', 0, 60, track_id=1, role='customer', dwell_s=999),
        event('d2', 30, 200, track_id=2, role='customer', dwell_s=999),
        event('outside', 0, 30, track_id=3, role='employee', dwell_s=30)])
    window = TimeWindow(start=START+timedelta(seconds=30), end=START+timedelta(seconds=150))
    result = reader(database).get_zone_dwell(scope=scope(), request=ZoneDwellRequest(window=window, filters={'zone_id':'z1'}))
    customers, employees, unknown = result.by_role
    assert customers.sample_count.value == 2 and customers.total.value == 150
    assert customers.p50.value == 75 and customers.p90.value == 111
    assert employees.sample_count.value == 0 and employees.p50.value is None
    assert unknown.total.value == 0
    assert customers.total.evidence[0].ids == ('d1','d2')


def test_interactions_use_confirmed_and_scoped_first_track_reference(database):
    put(database, 'tracks', [event('t1', 0, 600, track_id=1, role='customer', frames_observed=600),
        event('t2', -100, 600, store_id='store-2', track_id=1, role='customer', frames_observed=600),
        event('t3', -200, 600, camera_id='c2', track_id=1, role='customer', frames_observed=600),
        event('t4', -300, 600, run_id='r2', track_id=1, role='customer', frames_observed=600)])
    put(database, 'interactions', [event('i1', 60, 120, employee_track_id=2, customer_track_id=1, duration_s=999, verdict='interaction'),
        event('i2', 180, 240, employee_track_id=2, customer_track_id=1, duration_s=999, verdict='interaction'),
        event('u1', 30, 40, employee_track_id=2, customer_track_id=1, duration_s=10, verdict='unverified')])
    result = reader(database).get_interactions(scope=scope(allowed_run_ids=('r1',), allowed_camera_ids=('c1',)), request=InteractionsRequest(window=WINDOW, limit=1))
    assert result.confirmed_count.value == 2 and result.unverified_count.value == 1
    assert result.mean_confirmed_duration.value == 60
    assert result.mean_approach.value == 60 and result.approach_sample_count.value == 1
    assert result.mean_approach.evidence[0].ids == ('i1',)
    assert result.mean_approach.evidence[1].ids == ('t1',)
    assert result.approach_reference == 'camera_first_seen'
    later = InteractionsRequest(window=TimeWindow(start=START+timedelta(seconds=180), end=WINDOW.end))
    assert reader(database).get_interactions(scope=scope(), request=later).mean_approach.value is None


def test_missing_tracks_preserves_counts_but_not_approach(database):
    put(database, 'interactions', [event('i1', 60, 120, employee_track_id=2, customer_track_id=1, duration_s=60, verdict='interaction')])
    with sqlite3.connect(database) as conn:
        conn.execute('DROP TABLE tracks')
    result = reader(database).get_interactions(scope=scope(), request=InteractionsRequest(window=WINDOW))
    assert result.status == 'partial' and result.confirmed_count.value == 1 and result.mean_approach.value is None


def test_read_only_snapshot_does_not_change_database(database):
    before = hashlib.sha256(database.read_bytes()).hexdigest(), database.stat().st_mtime_ns
    with read_session(database) as session:
        with pytest.raises(sqlite3.OperationalError):
            session.conn.execute('DELETE FROM footfall')
    reader(database).get_footfall(scope=scope(), request=FootfallRequest(window=WINDOW))
    assert (hashlib.sha256(database.read_bytes()).hexdigest(), database.stat().st_mtime_ns) == before


def test_bucket_and_evidence_caps_do_not_change_aggregates(database):
    put(database, 'footfall', [event(f'in-{i:03}', i/1000, track_id=i, direction='in') for i in range(205)])
    result = reader(database).get_footfall(scope=scope(), request=FootfallRequest(window=WINDOW, granularity='minute', limit=1))
    assert result.truncated and len(result.buckets) == 1
    assert result.buckets[0].entries.value == 205
    citation = result.buckets[0].entries.evidence[0]
    assert citation.matched_count == 205 and len(citation.ids) == 200 and citation.truncated
