"""Trace authorization/retention, repaired claims, and offline service replay."""

import pytest

from backend.events.fixtures import CAMERA_OF, generate
from backend.events.ingest import connect
from .contracts import EventFilters, TrustedAccessScope
from .graph_contracts import GraphLimits, SpecialistDraft
from .service import AnalyticsService
from .test_graph import fetch_entry, fixed_route, no_network, registration, request
from .test_read_tools import fingerprint, WINDOW, database, event, put, scope
from .test_tool_integration import make_tools
from .tools.common import ObservationContext
from .tools.contextual import PostgresAnalyticsTools
from .traces import MemoryTraceStore


def test_trace_roundtrip_owner_store_and_full_scope_access(database):
    access = scope(allowed_camera_ids=('c1',))
    service = AnalyticsService(make_tools(database))
    result = service.ask(request(), scope=access)
    assert result.trace_retained and service.get_run(result.run_id, scope=access) == result
    assert result.tool_calls[0].arguments['window'] == result.request.window.model_dump(mode='json')
    assert result.tool_calls[0].arguments['granularity'] == 'hour'
    others = [scope(), scope(allowed_camera_ids=('c1',), allowed_zone_ids=('z1',)),
              TrustedAccessScope(actor_id='other', store_id='store-1', role='manager', allowed_camera_ids=('c1',)),
              TrustedAccessScope(actor_id='manager-1', store_id='store-2', role='manager', allowed_camera_ids=('c1',))]
    for other in others:
        with pytest.raises(KeyError, match='not found'):
            service.get_run(result.run_id, scope=other)
    result.tool_results.clear()
    assert service.get_run(result.run_id, scope=access).tool_results
    with pytest.raises(KeyError, match='not found'):
        service.get_run('absent', scope=access)


def test_ttl_fifo_and_restart_loss_are_explicit(database):
    clock = [0.0]
    store = MemoryTraceStore(max_runs=1, ttl_seconds=2, clock=lambda:clock[0])
    service = AnalyticsService(make_tools(database), traces=store)
    first = service.ask(request(), scope=scope())
    second = service.ask(request(), scope=scope())
    with pytest.raises(KeyError):
        service.get_run(first.run_id, scope=scope())
    assert service.get_run(second.run_id, scope=scope()) == second
    clock[0] = 2.0
    with pytest.raises(KeyError):
        service.get_run(second.run_id, scope=scope())
    with pytest.raises(KeyError):
        AnalyticsService(make_tools(database)).get_run(second.run_id, scope=scope())


def test_trace_byte_limit_and_store_failure_do_not_fabricate_retention(database):
    store = MemoryTraceStore(max_run_bytes=1024)
    service = AnalyticsService(make_tools(database), traces=store)
    result = service.ask(request(), scope=scope())
    assert not result.trace_retained and 'trace_not_retained' in result.errors
    assert result.claims  # Existing grounded answer is retained, not replaced by an error number.
    with pytest.raises(KeyError):
        service.get_run(result.run_id, scope=scope())
    class FailedStore:
        def put(self, run):
            raise RuntimeError('private-storage-detail')
    failed = AnalyticsService(make_tools(database), traces=FailedStore()).ask(request(), scope=scope())
    assert 'private-storage-detail' not in failed.model_dump_json()


def test_injected_store_cannot_return_another_users_trace(database):
    result = AnalyticsService(make_tools(database)).ask(request(), scope=scope())
    class BadStore:
        def get(self, run_id, access):
            return result
    service = AnalyticsService(make_tools(database), traces=BadStore())
    with pytest.raises(KeyError):
        service.get_run(result.run_id, scope=TrustedAccessScope(actor_id='other',store_id='store-1',role='manager'))
    with pytest.raises(KeyError):
        service.get_run('wrong-id', scope=scope())


def test_trace_identifiers_are_append_only(database):
    store = MemoryTraceStore()
    result = AnalyticsService(make_tools(database), traces=store).ask(request(), scope=scope())
    with pytest.raises(ValueError, match='append-only'):
        store.put(result)
    assert store.get(result.run_id, scope()) == result


def test_mixed_claims_keep_valid_evidence_and_remove_invalid_after_one_repair(database):
    put(database, 'footfall', [event('entry', track_id=1, direction='in')])
    good = None
    def handler(context, tools, prior, issues):
        nonlocal good
        if good is None:
            good = fetch_entry(context, tools)
        return SpecialistDraft(claims=(good, good.model_copy(update={'value':999.0})))
    service = AnalyticsService(make_tools(database), router=fixed_route, specialists=registration(handler))
    result = service.ask(request(), scope=scope())
    assert result.repair_attempts == 1 and result.status == 'partial'
    assert len(result.claims) == 1 and result.claims[0].value == 1 and '999' not in result.response
    assert result.citations == result.claims[0].evidence
    assert 'unsupported_claims_removed' in service.get_run(result.run_id, scope=scope()).errors


def test_rounding_tolerance_publishes_only_canonical_reader_values(database):
    put(database, 'footfall', [event('entry', track_id=1, direction='in')])
    def rounded(context, tools, prior, issues):
        claim = fetch_entry(context, tools)
        return SpecialistDraft(claims=(claim.model_copy(update={'value':1.0000000005}),))
    result = AnalyticsService(make_tools(database), router=fixed_route, specialists=registration(rounded)).ask(request(), scope=scope())
    assert result.claims[0].value == 1 and result.repair_attempts == 0
    assert '1.0000000005' not in result.response


def test_default_adapters_respect_requested_metric_and_missing_zone(database):
    service = AnalyticsService(make_tools(database))
    dwell = service.ask(request('Show dwell'), scope=scope())
    assert dwell.status == 'insufficient_evidence' and not dwell.tool_calls
    assert 'zone filter is required' in dwell.response
    dwell_zone = service.ask(request('Show customer dwell', filters=EventFilters(zone_id='z1')), scope=scope())
    assert dwell_zone.tool_calls[0].tool == 'get_zone_dwell'
    unattended = service.ask(request('Show unattended customers'), scope=scope())
    assert unattended.tool_calls[0].tool == 'get_unattended'
    interactions = service.ask(request('Show interactions'), scope=scope())
    assert interactions.tool_calls[0].tool == 'get_interactions'


def test_result_size_limit_and_tracing_environment_stay_offline(database, monkeypatch):
    monkeypatch.setenv('LANGSMITH_TRACING', 'true')
    service = AnalyticsService(make_tools(database), limits=GraphLimits(max_result_bytes=1024))
    result = service.ask(request(), scope=scope())
    assert result.status == 'unavailable' and 'result_size_limit' in result.errors
    assert not result.tool_results and not result.claims


def test_seeded_graph_replay_and_custom_registration_reuse_tools(postgres_dsn):
    path = postgres_dsn
    with connect(path) as conn:
        generate(conn)
    conn.close()
    contexts = tuple(ObservationContext(context_id='synthetic-layout',store_id='store-1',zone_id=z,camera_ids=(c,),
        available_sources=('footfall','zone_dwell','interactions','unattended_episodes')) for z,c in CAMERA_OF.items())
    tools = PostgresAnalyticsTools(path, synthetic=True, contexts=contexts)
    service = AnalyticsService(tools)
    before = fingerprint(path)
    queries = [request('Show footfall'), request('Show staffed coverage', filters=EventFilters(zone_id='z3'))]
    for query in queries:
        result = service.ask(query, scope=scope())
        assert result.claims and result.development_stub and result.trace_retained
        assert all(tool_result.synthetic for tool_result in result.tool_results.values())
        assert service.get_run(result.run_id, scope=scope()) == result
    assert fingerprint(path) == before
