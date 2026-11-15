"""Read-only anomaly candidates over authorized, time-matched analytics results."""

from typing import Literal

from pydantic import Field

from .contracts import Contract, CoverageResult, Evidence, Identifier, TimeWindow, TrustedAccessScope
from .tools.operations import PipelineHealthResult, QueueResult


class InvestigationContext(Contract):
    alert_id: Identifier
    zone_id: Identifier
    scope: TrustedAccessScope
    window: TimeWindow
    synthetic: bool
    min_fps: float = Field(gt=0)
    max_queue_length: int = Field(ge=0, strict=True)
    min_staffed_ratio: float = Field(ge=0, le=1)


class Candidate(Contract):
    signal: Literal["pipeline_issue", "low_staffed_coverage", "long_queue"]
    evidence: tuple[Evidence, ...] = Field(min_length=1, max_length=10)


class Investigation(Contract):
    alert_id: Identifier
    candidates: tuple[Candidate, ...]
    unavailable_sources: tuple[str, ...]


def investigate(context: InvestigationContext, *, coverage: CoverageResult | None,
                queue: QueueResult | None, health: PipelineHealthResult | None) -> Investigation:
    """Require a trusted alert-to-store binding from the caller before reading results."""
    scope = context.scope
    if scope.role != "manager" or (scope.allowed_zone_ids is not None and
                                    context.zone_id not in scope.allowed_zone_ids):
        raise PermissionError("Alert is outside investigation scope")
    for result in (coverage, queue, health):
        if result is not None and (result.scope != scope or result.window != context.window or
                                   result.filters.zone_id != context.zone_id or
                                   result.synthetic != context.synthetic):
            raise PermissionError("Investigation evidence selection does not match the alert")

    candidates, missing = [], []
    if health is None or not health.samples:
        missing.append("pipeline_health")
    else:
        refs = tuple(s.evidence for s in health.samples
                     if s.frozen_or_dark == 1 or (s.fps.value is not None and s.fps.value < context.min_fps))
        if refs:
            candidates.append(Candidate(signal="pipeline_issue", evidence=refs[:10]))

    zone = next((z for z in coverage.zones if z.zone_id == context.zone_id), None) if coverage else None
    ratio = zone.staffed_open_ratio if zone else None
    if ratio is None or ratio.value is None:
        missing.append("coverage")
    elif ratio.value < context.min_staffed_ratio:
        candidates.append(Candidate(signal="low_staffed_coverage", evidence=ratio.evidence[:10]))

    if queue is None or not queue.samples:
        missing.append("queue")
    else:
        refs = tuple(s.evidence for s in queue.samples if s.zone_id == context.zone_id and
                     s.queue_length.value is not None and s.queue_length.value > context.max_queue_length)
        if refs:
            candidates.append(Candidate(signal="long_queue", evidence=refs[:10]))
    return Investigation(alert_id=context.alert_id, candidates=tuple(candidates), unavailable_sources=tuple(missing))
