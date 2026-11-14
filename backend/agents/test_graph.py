"""Offline LangGraph traversal/grounding; no live model or business-agent claim."""
from datetime import timedelta
import socket

import pytest
from pydantic import ValidationError

from .contracts import EventFilters, TimeWindow
from .graph import run_analytics
from .graph_contracts import AskRequest, GraphLimits, GraphRun, RouteDecision, SpecialistDraft
from .routing import JsonRouter, OfflineRouter
from .specialists import ALLOWED_TOOLS, SpecialistRegistration, claim_for
from .test_read_tools import START, WINDOW, database, event, put, scope
from .test_tool_integration import make_tools
from .tools.registry import ScopedToolRegistry


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('Graph tests must run offline')
    monkeypatch.setattr(socket.socket, 'connect', denied)


def request(question='Show footfall', **kwargs):
    return AskRequest(question=question, window=WINDOW, **kwargs)


def registry(database):
    return ScopedToolRegistry(make_tools(database), scope())


def fixed_route(req, access):
    return RouteDecision(target='customer_behavior')


def registration(handler, target='customer_behavior', stub=False):
    return {target:SpecialistRegistration(handler, ALLOWED_TOOLS[target], development_stub=stub)}


def fetch_entry(context, tools):
    call_id, result = tools.invoke('get_footfall', {'window':context.request.window.model_dump(mode='json'),
                                  'filters':context.request.filters.model_dump(exclude_none=True)})
    return claim_for(call_id, result, ('buckets', 0, 'entries'))


def test_customer_and_employee_paths_use_real_read_tools(database):
    put(database, 'footfall', [event('entry', track_id=1, direction='in')])
    result = run_analytics(request(), registry(database))
    assert [n.node for n in result.nodes] == ['route','customer_behavior','ground','finish']
    assert result.claims[0].value == 1 and result.claims[0].evidence[0].ids == ('entry',)
    assert result.development_stub and "Ruhab's" in result.response
    assert result.tool_calls[0].tool == 'get_footfall' and result.tool_calls[0].elapsed_ms >= 0
    assert result.latency_ms >= 0 and result.steps == 4
    assert GraphRun.model_validate_json(result.model_dump_json()) == result
    put(database, 'zone_dwell', [event('staff', 0, 120, track_id=2, role='employee', dwell_s=120)])
    employee = run_analytics(request('Show staffed coverage'), registry(database))
    assert employee.selected_node == 'employee_activity'
    assert employee.claims[0].value == 120 and employee.development_stub


def test_json_router_is_injected_and_specialist_registration_is_reused(database):
    calls = []
    def complete(messages):
        calls.append(messages)
        return '{"target":"customer_behavior"}'
    def handler(context, tools, prior, issues):
        call_id, result = tools.invoke('get_interactions', {'window':context.request.window.model_dump(mode='json')})
        return SpecialistDraft(claims=(claim_for(call_id, result, ('confirmed_count',)),))
    result = run_analytics(request('Read metrics'), registry(database), router=JsonRouter(complete), specialists=registration(handler))
    assert len(calls) == 1 and calls[0][-1]['content'] == 'Read metrics'
    assert not result.development_stub and result.claims[0].value == 0
    assert result.tool_calls[0].tool == 'get_interactions'


@pytest.mark.parametrize('question', ['Dispatch staff to z3', 'Identify this customer', 'Rank employees', 'What is the weather?'])
def test_out_of_scope_and_operational_requests_never_invoke_tools(database, question):
    result = run_analytics(request(question), registry(database))
    assert result.status == 'refused' and not result.tool_calls and not result.claims
    assert [n.node for n in result.nodes] == ['route','finish']


def test_provider_unavailable_or_invalid_target_is_safe(database):
    def failed(req, access):
        raise RuntimeError('private-provider-detail')
    for router in (failed, JsonRouter(lambda messages:'{"target":"dispatch"}')):
        result = run_analytics(request(), registry(database), router=router)
        assert result.status == 'unavailable' and result.errors == ('router_unavailable',)
        assert 'private-provider-detail' not in result.model_dump_json() and not result.tool_calls


@pytest.mark.parametrize('kwargs', [{'question':'x'}, {'window':{'start':'2026-11-03','end':'2026-11-04'}},
                                     {'node':'dispatch'}, {'scope':{'store_id':'store-2'}}])
def test_missing_invalid_inputs_cannot_choose_nodes_or_identity(kwargs):
    base = {'question':'Show footfall','window':WINDOW}
    with pytest.raises(ValidationError):
        AskRequest(**(base | kwargs))


def test_one_repair_pass_corrects_exact_metric_claim(database):
    put(database, 'footfall', [event('entry', track_id=1, direction='in')])
    observed = []
    correct = None
    def handler(context, tools, prior, issues):
        nonlocal correct
        observed.append((prior is not None, tuple(i.code for i in issues)))
        if prior is None:
            correct = fetch_entry(context, tools)
            return SpecialistDraft(claims=(correct.model_copy(update={'value':999.0}),))
        return SpecialistDraft(claims=(correct,))
    result = run_analytics(request(), registry(database), router=fixed_route, specialists=registration(handler))
    assert observed == [(False,()), (True,('wrong_value',))]
    assert [n.node for n in result.nodes] == ['route','customer_behavior','ground','repair','ground','finish']
    assert result.repair_attempts == 1 and result.claims[0].value == 1
    assert '999' not in result.response and len(result.tool_calls) == 1


@pytest.mark.parametrize('change', ['value','unit','window','store','filters','evidence','path'])
def test_unsupported_claims_are_removed_after_one_repair(database, change):
    put(database, 'footfall', [event('entry', track_id=1, direction='in'),
                             event('out1', track_id=2, direction='out'), event('out2', track_id=3, direction='out')])
    claim = None
    def handler(context, tools, prior, issues):
        nonlocal claim
        if claim is None:
            claim = fetch_entry(context, tools)
            modifications = {
                'value':{'value':2.0},  # 2 exists elsewhere in this result; it does not support entries.
                'unit':{'unit':'seconds'}, 'store':{'store_id':'store-2'},
                'window':{'window':TimeWindow(start=START+timedelta(seconds=1), end=WINDOW.end)},
                'filters':{'filters':EventFilters(zone_id='z2')},
                'evidence':{'evidence':(claim.evidence[0].model_copy(update={'ids':('out1',)}),)},
                'path':{'path':('buckets', 50, 'entries')},
            }
            claim = claim.model_copy(update=modifications[change])
        return SpecialistDraft(claims=(claim,))
    result = run_analytics(request(), registry(database), router=fixed_route, specialists=registration(handler))
    assert result.status == 'insufficient_evidence' and result.repair_attempts == 1
    assert not result.claims and not result.citations and 'unsupported_claims_removed' in result.errors
    assert 'entries =' not in result.response


def test_specialists_cannot_publish_freeform_numeric_answers(database):
    def bad(context, tools, prior, issues):
        return {'claims':[], 'answer':'There were 999 customers'}
    result = run_analytics(request(), registry(database), router=fixed_route, specialists=registration(bad))
    assert result.status == 'unavailable' and '999' not in result.response


def test_tool_and_step_budgets_are_bounded(database):
    def repeated(context, tools, prior, issues):
        fetch_entry(context, tools)
        fetch_entry(context, tools)
        return SpecialistDraft()
    result = run_analytics(request(), registry(database), router=fixed_route, specialists=registration(repeated), limits=GraphLimits(max_tool_calls=1))
    assert len(result.tool_calls) == 1 and 'tool_limit' in result.errors and not result.claims
    stopped = run_analytics(request(), registry(database), limits=GraphLimits(max_steps=1))
    assert stopped.steps == 1 and not stopped.tool_calls and 'step_limit' in stopped.errors


def test_allowed_tools_and_request_window_filters_cannot_be_broadened(database):
    def denied(context, tools, prior, issues):
        tools.invoke('get_coverage', {'window':context.request.window.model_dump(mode='json')})
    result = run_analytics(request(), registry(database), router=fixed_route, specialists=registration(denied))
    assert 'tool_denied' in result.errors and not result.tool_results
    def broadened(context, tools, prior, issues):
        tools.invoke('get_footfall', {'window':context.request.window.model_dump(mode='json')})
    restricted = run_analytics(request(filters=EventFilters(zone_id='z1')), registry(database), router=fixed_route, specialists=registration(broadened))
    assert 'tool_failed' in restricted.errors and not restricted.tool_results
    with pytest.raises(ValueError):
        run_analytics(request(), registry(database), specialists={'customer_behavior':SpecialistRegistration(denied, frozenset(('dispatch',)))})


def test_missing_sources_return_insufficient_or_unavailable_not_invented_metrics(postgres_dsn):
    from psycopg.conninfo import make_conninfo
    missing = make_conninfo(postgres_dsn, options='-csearch_path=retailpulse_missing')
    result = run_analytics(request(), registry(missing))
    assert result.status == 'unavailable' and not result.claims


@pytest.mark.parametrize('question', ['Where are the staffing gaps?', 'Is aisle 2 understaffed?', 'Any coverage gap today?'])
def test_offline_router_sends_staffing_questions_to_employee_activity(question):
    # ACCEPTANCE.md A4 asks "Where are the staffing gaps?"; it used to fall through to 'unsupported' and be refused.
    assert OfflineRouter()(request(question), scope()).target == 'employee_activity'
