"""Bounded, injectable LangGraph analytics, without HTTP or dispatch capability."""
from math import isclose
from time import perf_counter
from typing import TypedDict
from uuid import uuid4

from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langsmith.run_helpers import tracing_context

from .graph_contracts import (AskRequest, GraphLimits, GraphRun, GroundingIssue, NodeTrace,
                              RouteDecision, SpecialistContext, SpecialistDraft, ToolTrace)
from .routing import OfflineRouter, prohibited_question
from .specialists import ALLOWED_TOOLS, development_specialists, metric_at
from .tools.registry import REQUEST_TYPES, ScopedToolRegistry


class GraphState(TypedDict, total=False):
    run_id: str
    request: AskRequest
    scope: object
    selected_node: str
    draft: SpecialistDraft
    verified: tuple
    issues: tuple
    errors: tuple
    repairs: int
    steps: int
    tool_results: dict


class BudgetExceeded(Exception):
    pass


class ReadToolFacade:
    """Run-local allowed tools; request scope/window cannot be broadened by a specialist."""
    def __init__(self, registry, request, limits):
        self._registry, self._request, self._limits = registry, request, limits
        self._results, self.calls, self.errors = {}, [], []
        self.allowed = frozenset()
        self.node = ''

    def invoke(self, name, arguments):
        if len(self.calls) >= self._limits.max_tool_calls:
            self.errors.append('tool_limit')
            raise BudgetExceeded('tool_limit')
        call_id = f'tool-{len(self.calls)+1}'
        started, status = perf_counter(), 'error'
        allowed = isinstance(name, str) and name in self.allowed and name in REQUEST_TYPES
        try:
            if not allowed:
                raise PermissionError('Tool is not registered for this specialist')
            request = REQUEST_TYPES[name].model_validate(arguments)
            if request.window != self._request.window:
                raise PermissionError('Tool window must match the validated analytics request')
            for field in ('run_id', 'camera_id', 'zone_id'):
                required = getattr(self._request.filters, field)
                if required is not None and getattr(request.filters, field) != required:
                    raise PermissionError('Specialist cannot broaden request filters')
            result = self._registry.invoke(name, arguments)
            if (result.scope != self._registry.scope or result.window != request.window
                    or result.filters != request.filters or result.tool != name):
                raise PermissionError('Tool returned a different scope/window/filter context')
            if len(result.model_dump_json().encode()) > self._limits.max_result_bytes:
                self.errors.append('result_size_limit')
                raise BudgetExceeded('result_size_limit')
            self._results[call_id] = result.model_copy(deep=True)
            status = result.status.value
            return call_id, result.model_copy(deep=True)
        except Exception:
            self.errors.append('tool_failed' if allowed else 'tool_denied')
            raise
        finally:
            self.calls.append(ToolTrace(call_id=call_id, tool=name if allowed else 'denied', node=self.node,
                                        elapsed_ms=(perf_counter()-started)*1000, status=status))

    def snapshot(self):
        return {key: result.model_copy(deep=True) for key, result in self._results.items()}


def ground(draft, results, scope):
    valid, issues = [], []
    for index, claim in enumerate(draft.claims):
        result = results.get(claim.call_id)
        try:
            metric = metric_at(result, claim.path)
        except ValueError:
            issues.append(GroundingIssue(claim_index=index, code='missing_metric'))
            continue
        code = None
        if result.scope != scope or claim.store_id != scope.store_id or claim.window != result.window or claim.filters != result.filters:
            code = 'wrong_context'
        elif metric.value is None or claim.unit != metric.unit or not isclose(claim.value, metric.value, rel_tol=1e-9, abs_tol=1e-9):
            code = 'wrong_value'
        elif claim.evidence != metric.evidence:
            code = 'wrong_evidence'
        if code:
            issues.append(GroundingIssue(claim_index=index, code=code))
        else:
            valid.append(claim)
    return tuple(valid), tuple(issues)


def render_claim(claim, result):
    """Only server-owned metric names and exact result context reach answer prose."""
    label = str(claim.path[-1]).replace('_', ' ')
    details = []
    if len(claim.path) >= 3 and isinstance(claim.path[1], int):
        parent = getattr(result, claim.path[0])[claim.path[1]]
        if hasattr(parent, 'role'):
            details.append(parent.role)
        if hasattr(parent, 'zone_id'):
            details.append(parent.zone_id)
        if hasattr(parent, 'window'):
            details.append(parent.window.start.isoformat() + ' to ' + parent.window.end.isoformat())
    suffix = f" ({'; '.join(details)})" if details else ''
    return f'{result.tool}: {label} = {claim.value:g} {claim.unit}{suffix}.'


def run_analytics(request: AskRequest, registry: ScopedToolRegistry, *, router=None, specialists=None, limits=None) -> GraphRun:
    """Callable Phase 3 boundary. Registry/scope must come from trusted server code."""
    request = AskRequest.model_validate(request)
    registry.scope.validate_filters(request.filters)
    limits = GraphLimits.model_validate(limits or {})
    router = router if router is not None else OfflineRouter()
    registrations = development_specialists() if specialists is None else dict(specialists)
    for name, registration in registrations.items():
        if name not in ALLOWED_TOOLS or not registration.allowed_tools <= ALLOWED_TOOLS[name]:
            raise ValueError('Specialist registration exceeds the fixed analytics capability set')
    run_id = str(uuid4())
    context = SpecialistContext(run_id=run_id, scope=registry.scope, request=request)
    tools = ReadToolFacade(registry, request, limits)
    nodes, latest = [], {}
    started = perf_counter()

    def route(state):
        try:
            decision = RouteDecision(target='unsupported') if prohibited_question(request.question) else RouteDecision.model_validate(router(request, registry.scope))
            return {'selected_node': decision.target}
        except Exception:
            return {'selected_node':'unsupported', 'errors':state['errors']+('router_unavailable',)}

    def specialist(state, repair=False):
        registration = registrations.get(state['selected_node'])
        if registration is None:
            return {'errors':state['errors']+('specialist_unavailable',), 'repairs':int(repair), 'draft':SpecialistDraft()}
        tools.allowed = registration.allowed_tools
        tools.node = 'repair' if repair else state['selected_node']
        try:
            draft = SpecialistDraft.model_validate(registration.handler(context, tools,
                state['draft'] if repair else None, state['issues'] if repair else ()))
            return {'draft':draft, 'repairs':int(repair)}
        except Exception:
            return {'errors':state['errors']+('specialist_failed',), 'repairs':int(repair)}

    def grounding(state):
        verified, issues = ground(state['draft'], tools.snapshot(), registry.scope)
        return {'verified':verified, 'issues':issues}

    def wrap(name, function):
        def wrapped(state):
            nonlocal latest
            if len(nodes) >= limits.max_steps:
                raise BudgetExceeded('step_limit')
            tick = perf_counter()
            try:
                update = function(state)
            finally:
                nodes.append(NodeTrace(node=name, elapsed_ms=(perf_counter()-tick)*1000))
            update |= {'steps':len(nodes), 'tool_results':tools.snapshot()}
            latest = state | update
            return update
        return wrapped

    builder = StateGraph(GraphState)
    builder.add_node('route', wrap('route', route))
    for target in ALLOWED_TOOLS:
        builder.add_node(target, wrap(target, specialist))
    builder.add_node('ground', wrap('ground', grounding))
    builder.add_node('repair', wrap('repair', lambda state: specialist(state, repair=True)))
    builder.add_node('finish', wrap('finish', lambda state: {}))
    builder.add_edge(START, 'route')
    builder.add_conditional_edges('route', lambda state: state['selected_node'],
                                  {**{name:name for name in ALLOWED_TOOLS}, 'unsupported':'finish'})
    for target in ALLOWED_TOOLS:
        builder.add_edge(target, 'ground')
    builder.add_conditional_edges('ground', lambda state: 'repair' if state['issues'] and state['repairs'] == 0 else 'finish')
    builder.add_edge('repair', 'ground')
    builder.add_edge('finish', END)
    initial = GraphState(run_id=run_id, request=request, scope=registry.scope, selected_node='unsupported',
                         draft=SpecialistDraft(), verified=(), issues=(), errors=(), repairs=0, steps=0, tool_results={})
    latest = initial
    # No telemetry/provider traffic, even if a host has LangSmith environment flags.
    with tracing_context(enabled=False):
        try:
            latest = builder.compile().invoke(initial, {'recursion_limit':limits.max_steps+2, 'callbacks':[]})
        except (BudgetExceeded, GraphRecursionError):
            latest = latest | {'errors':latest['errors']+('step_limit',)}
    errors = tuple(dict.fromkeys(latest['errors']+tuple(tools.errors)))
    verified = latest['verified']
    results = tools.snapshot()
    registration = registrations.get(latest['selected_node'])
    stub = registration.development_stub if registration else False
    if latest['selected_node'] == 'unsupported':
        status = 'unavailable' if errors else 'refused'
    elif not verified:
        status = 'unavailable' if errors or results and all(r.status == 'unavailable' for r in results.values()) else 'insufficient_evidence'
    else:
        status = 'partial' if errors or latest['issues'] or any(r.status != 'ok' for r in results.values()) else 'ok'
    if latest['issues']:
        errors += ('unsupported_claims_removed',)
    lines = [render_claim(claim, results[claim.call_id]) for claim in verified]
    if stub:
        lines.insert(0, "Development adapter only; Ruhab's business-agent implementation is not registered.")
    if not verified:
        lines.append({'refused':'This request is outside supported read-only analytics.', 'unavailable':'Analytics are unavailable for this request.'}.get(status, 'Insufficient supported metric evidence for this request.'))
    citations = tuple(dict((ref.model_dump_json(), ref) for claim in verified for ref in claim.evidence).values())
    limitations = tuple(dict.fromkeys(note for result in results.values() for note in result.limitations))[:50]
    return GraphRun(run_id=run_id, request_id=request.request_id or run_id, request=request, scope=registry.scope,
        selected_node=latest['selected_node'], development_stub=stub, status=status, claims=verified, citations=citations,
        tool_results=results, nodes=tuple(nodes), tool_calls=tuple(tools.calls), errors=errors,
        limitations=limitations, repair_attempts=latest['repairs'], steps=len(nodes),
        latency_ms=(perf_counter()-started)*1000, response='\n'.join(lines))
