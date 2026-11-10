"""Development adapters and Ruhab's registration boundary, not her business logic."""
from dataclasses import dataclass
from typing import Callable

from .contracts import Metric
from .graph_contracts import Claim, GroundingIssue, SpecialistContext, SpecialistDraft

ALLOWED_TOOLS = {
    'customer_behavior': frozenset(('get_footfall', 'get_zone_dwell', 'get_interactions', 'get_unattended')),
    'employee_activity': frozenset(('get_coverage', 'get_interactions', 'get_unattended')),
}


def metric_at(result, path):
    """Resolve only model fields/tuple indexes; no arbitrary Python attributes."""
    current = result
    for token in path:
        if isinstance(token, int) and isinstance(current, tuple) and 0 <= token < len(current):
            current = current[token]
        elif isinstance(token, str) and token in getattr(type(current), 'model_fields', {}):
            current = getattr(current, token)
        else:
            raise ValueError('Metric path does not exist')
    if not isinstance(current, Metric):
        raise ValueError('Path must reference an exact metric')
    return current


def claim_for(call_id, result, path):
    metric = metric_at(result, path)
    if metric.value is None:
        return None
    return Claim(call_id=call_id, path=path, value=metric.value, unit=metric.unit,
                 store_id=result.scope.store_id, window=result.window, filters=result.filters, evidence=metric.evidence)


@dataclass(frozen=True)
class SpecialistRegistration:
    handler: Callable
    allowed_tools: frozenset[str]
    development_stub: bool = True


def customer_behavior_adapter(context: SpecialistContext, tools, prior=None, issues=()) -> SpecialistDraft:
    """Fixture/read-tool demonstration only; no segmentation or hot/gray-zone policy."""
    arguments = {'window': context.request.window.model_dump(mode='json'), 'filters': context.request.filters.model_dump(exclude_none=True)}
    if context.request.filters.zone_id:
        call_id, result = tools.invoke('get_zone_dwell', arguments)
        paths = [('by_role', 0, 'sample_count'), ('by_role', 0, 'total'), ('by_role', 0, 'p50')]
    else:
        call_id, result = tools.invoke('get_footfall', arguments | {'granularity':'hour', 'limit':3})
        paths = [('buckets', i, 'entries') for i in range(len(result.buckets))]
    return SpecialistDraft(claims=tuple(claim for path in paths if (claim := claim_for(call_id, result, path)) is not None))


def employee_activity_adapter(context: SpecialistContext, tools, prior=None, issues=()) -> SpecialistDraft:
    """Fixture/read-tool demonstration only; no availability or employee ranking."""
    arguments = {'window':context.request.window.model_dump(mode='json'), 'filters':context.request.filters.model_dump(exclude_none=True), 'limit':3}
    call_id, result = tools.invoke('get_coverage', arguments)
    paths = [('zones', i, name) for i in range(len(result.zones)) for name in ('observed_staffed', 'unknown_observation')]
    return SpecialistDraft(claims=tuple(claim for path in paths if (claim := claim_for(call_id, result, path)) is not None))


def development_specialists():
    return {
        'customer_behavior': SpecialistRegistration(customer_behavior_adapter, ALLOWED_TOOLS['customer_behavior']),
        'employee_activity': SpecialistRegistration(employee_activity_adapter, ALLOWED_TOOLS['employee_activity']),
    }
