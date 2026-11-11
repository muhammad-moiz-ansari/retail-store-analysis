"""Registry/security and seeded replay, in addition to hand-calculated unit tests."""
from datetime import timedelta

import pytest
from pydantic import ValidationError

from backend.events.fixtures import CAMERA_OF, generate
from backend.events.ingest import connect, validate
from .contracts import (CoverageRequest, FootfallRequest, InteractionsRequest, TimeWindow,
                        TrustedAccessScope, UnattendedRequest, ZoneDwellRequest)
from .test_read_tools import fingerprint, START, WINDOW, database, event, put, scope
from .tools.common import ObservationContext
from .tools.contextual import PostgresAnalyticsTools
from .tools.registry import ScopedToolRegistry


def make_tools(path, *, available=('footfall', 'zone_dwell', 'interactions', 'unattended_episodes')):
    return PostgresAnalyticsTools(path, synthetic=True, contexts=(ObservationContext(
        context_id='synthetic-layout', store_id='store-1', zone_id='z1', camera_ids=('c1',),
        available_sources=available),))


def test_registry_rejects_identity_override_sql_dispatch_and_employee(database):
    registry = ScopedToolRegistry(make_tools(database), scope(allowed_zone_ids=('z1',)))
    args = {'window': WINDOW.model_dump(mode='json')}
    assert registry.invoke('get_footfall', args).scope.store_id == 'store-1'
    for injected in ({'scope': {'store_id':'store-2'}}, {'store_id':'store-2'}, {'path':'other.sqlite3'},
                     {'contexts':[]}, {'query':'DELETE FROM footfall'}):
        with pytest.raises(ValidationError):
            registry.invoke('get_footfall', args | injected)
    for name in ('run_readonly_sql', 'dispatch', 'get_queue', '__dict__'):
        with pytest.raises(ValueError):
            registry.invoke(name, args)
    with pytest.raises(ValueError):
        registry.invoke('get_footfall', args | {'filters': {'zone_id':'z2'}})
    with pytest.raises(PermissionError):
        ScopedToolRegistry(make_tools(database), TrustedAccessScope(actor_id='e1', store_id='store-1', role='employee'))
    assert len(registry.input_schemas()) == 5


def test_all_five_readers_have_no_cross_store_results_or_writes(database):
    for store, key in (('store-1','own'),('store-2','other')):
        put(database, 'footfall', [event(key, track_id=1, direction='in', store_id=store)])
        put(database, 'zone_dwell', [event(key+'d', 0, 300, track_id=1, role='employee', dwell_s=300, store_id=store)])
        put(database, 'interactions', [event(key+'i', 10, 30, employee_track_id=1, customer_track_id=2,
                                             duration_s=20, verdict='interaction', store_id=store)])
        put(database, 'unattended_episodes', [event(key+'u', 0, 300, customer_track_id=2, helped=0, waited_s=300, store_id=store)])
    before = fingerprint(database)
    registry = ScopedToolRegistry(make_tools(database), scope())
    for name in registry.input_schemas():
        args = {'window': WINDOW.model_dump(mode='json')}
        if name == 'get_zone_dwell':
            args['filters'] = {'zone_id':'z1'}
        result = registry.invoke(name, args)
        encoded = result.model_dump_json()
        assert 'other' not in encoded and result.scope == scope()
        assert type(result).model_validate_json(encoded) == result
    assert (fingerprint(database)) == before


def test_healthy_camera_without_declared_feed_cannot_establish_zero(database):
    registry = ScopedToolRegistry(make_tools(database, available=()), scope())
    result = registry.invoke('get_footfall', {'window':WINDOW.model_dump(mode='json')})
    assert result.status == 'partial' and result.buckets[0].entries.value is None
    assert 'feed is not declared' in ' '.join(result.limitations)


def test_zone_restricted_history_cannot_claim_first_approach(database):
    put(database, 'tracks', [event('t1', 0, 600, track_id=1, role='customer', frames_observed=600)])
    put(database, 'interactions', [event('i1', 60, 90, employee_track_id=2, customer_track_id=1, duration_s=30, verdict='interaction')])
    result = make_tools(database).get_interactions(scope=scope(allowed_zone_ids=('z1',)), request=InteractionsRequest(window=WINDOW))
    assert result.confirmed_count.value == 1 and result.unverified_count.value == 0
    assert result.mean_approach.value is None and result.status == 'partial'


def test_track_collisions_across_simultaneously_visible_runs_and_cameras(database):
    put(database, 'tracks', [event('r1c1', 0, 600, track_id=1, role='customer', frames_observed=600),
        event('r2c2', 100, 600, run_id='r2', camera_id='c2', track_id=1, role='customer', frames_observed=500),
        event('unrelated-store', -100, 600, store_id='store-2', track_id=1, role='customer', frames_observed=700)])
    put(database, 'interactions', [event('i1', 60, 70, employee_track_id=2, customer_track_id=1, duration_s=10, verdict='interaction'),
        event('i2', 150, 160, run_id='r2', camera_id='c2', employee_track_id=2, customer_track_id=1, duration_s=10, verdict='interaction')])
    result = make_tools(database).get_interactions(scope=scope(), request=InteractionsRequest(window=WINDOW))
    assert result.confirmed_count.value == 2
    assert result.mean_approach.value == 55 and result.approach_sample_count.value == 2
    assert result.mean_approach.evidence[1].ids == ('r1c1', 'r2c2')
    # The unexpected c2 observation prevents a false healthy zero from c1 alone.
    assert result.status == 'partial' and result.unverified_count.value is None
    assert any('outside the configured' in limit for limit in result.limitations)


def test_scan_budget_returns_unavailable_not_capped_aggregate(database, monkeypatch):
    from .tools import store
    put(database, 'footfall', [event(f'e{i}', i, track_id=i, direction='in') for i in range(3)])
    monkeypatch.setattr(store, 'SCAN_LIMIT', 2)
    result = make_tools(database).get_footfall(scope=scope(), request=FootfallRequest(window=WINDOW))
    assert result.status == 'unavailable' and not result.buckets


def test_operating_intervals_merge_and_closed_window_does_not_divide_by_zero(database):
    closed = TimeWindow(start=START+timedelta(days=1), end=START+timedelta(days=1, seconds=600))
    context = ObservationContext(context_id='synthetic-closed', store_id='store-1', zone_id='z1', camera_ids=('c1',),
                                 available_sources=('zone_dwell',), operating_windows=(closed,))
    result = PostgresAnalyticsTools(database, synthetic=True, contexts=(context,)).get_coverage(
        scope=scope(), request=CoverageRequest(window=WINDOW))
    assert result.zones[0].open_seconds.value == 0
    assert result.zones[0].staffed_open_ratio.value is None


def test_seeded_day_reuses_saqib_generator_and_preserves_database(postgres_dsn):
    path = postgres_dsn
    with connect(path) as conn:
        counts = generate(conn)
        assert validate(conn) == []
    conn.close()
    contexts = tuple(ObservationContext(context_id='synthetic-day-layout', store_id='store-1', zone_id=zone,
        camera_ids=(camera,), available_sources=('footfall','zone_dwell','interactions','unattended_episodes'))
        for zone, camera in CAMERA_OF.items())
    registry = ScopedToolRegistry(PostgresAnalyticsTools(path, synthetic=True, contexts=contexts), scope())
    window = {'start':'2026-11-03T09:00:00Z','end':'2026-11-03T21:00:00Z'}
    before = fingerprint(path)
    results = {name: registry.invoke(name, {'window':window} | ({'filters':{'zone_id':'z3'}} if name == 'get_zone_dwell' else {}))
               for name in registry.input_schemas()}
    assert all(r.synthetic and r.status != 'unavailable' for r in results.values())
    footfall = results['get_footfall']
    assert sum(b.entries.value or 0 for b in footfall.buckets) + sum(b.exits.value or 0 for b in footfall.buckets) == counts['footfall'] == 2216
    interactions = results['get_interactions']
    assert interactions.confirmed_count.value + (interactions.unverified_count.value or 0) == counts['interactions'] == 772
    assert results['get_unattended'].episode_count.value == counts['unattended_episodes'] == 381
    coverage = {z.zone_id:z for z in results['get_coverage'].zones}
    assert coverage['z3'].unknown_observation.value == 2400
    assert coverage['z3'].staffed_open_ratio.value is None
    assert fingerprint(path) == before
