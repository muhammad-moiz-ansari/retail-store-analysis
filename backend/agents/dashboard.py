"""Read-only dashboard adapter over the existing five tools; no ingestion/business policy."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .contracts import (Contract, CountMetric, EventFilters, Evidence, Identifier, Metric,
                        TimeWindow, TrustedAccessScope)
from .tools.common import ObservationContext
from .tools.contextual import SQLiteAnalyticsTools
from .tools.registry import ScopedToolRegistry


class DashboardFilters(Contract):
    runId: Identifier | None = None
    cameraId: Identifier | None = None
    zoneId: Identifier  # Dwell/coverage cannot invent an all-zone distribution.

    def event_filters(self):
        return EventFilters(run_id=self.runId, camera_id=self.cameraId, zone_id=self.zoneId)


class DashboardRequest(Contract):
    storeId: Identifier
    window: TimeWindow
    filters: DashboardFilters


class DashboardMembership(Contract):
    user_id: Identifier
    store_id: Identifier
    run_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=1000)
    camera_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=100)
    zone_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=100)
    default_request: DashboardRequest

    def scope(self):
        return TrustedAccessScope(actor_id=self.user_id, store_id=self.store_id, role='manager',
            allowed_run_ids=self.run_ids, allowed_camera_ids=self.camera_ids, allowed_zone_ids=self.zone_ids)

    def authorize(self, request):
        if request.storeId != self.store_id:
            raise PermissionError('Selection outside dashboard membership')
        try:
            self.scope().validate_filters(request.filters.event_filters())
        except ValueError as exc:
            raise PermissionError('Selection outside dashboard membership') from exc

    @model_validator(mode='after')
    def valid_default(self):
        try:
            self.authorize(self.default_request)
        except PermissionError as exc:
            raise ValueError('Default selection outside configured membership') from exc
        return self


class DashboardConfig(Contract):
    version: Literal[1]
    event_db: Path
    synthetic: bool = Field(strict=True)  # Operator attests provenance of every allowed run.
    memberships: tuple[DashboardMembership, ...] = Field(min_length=1, max_length=1000)
    contexts: tuple[ObservationContext, ...] = Field(default=(), max_length=1000)

    @model_validator(mode='after')
    def unambiguous(self):
        if len({m.user_id for m in self.memberships}) != len(self.memberships):
            raise ValueError('One explicit store membership per user is required')
        keys = [(c.store_id, c.zone_id, c.shift) for c in self.contexts]
        if len(set(keys)) != len(keys):
            raise ValueError('Duplicate observation context')
        return self


def utc(stamp):
    return stamp.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def public_request(request):
    result = request.model_dump(mode='json', exclude_none=True)
    result['window'] = {'start': utc(request.window.start), 'end': utc(request.window.end)}
    return result


def present(metric, result, *, reason=None):
    """Retain partialness and independent evidence sampling; absence is not zero."""
    value = metric.value
    missing = reason or metric.unavailable_reason
    status = 'unavailable' if value is None else 'partial' if result.status.value == 'partial' else 'empty' if value == 0 else 'ok'
    limitations = list(result.limitations)
    if result.truncated:
        limitations.append('Source result rows were truncated; inspect metric semantics before aggregation')
    if missing:
        limitations.append(missing)
    if value is None and not missing:
        missing = 'No supported metric in the selected source result'
        limitations.append(missing)
    return dict(value=value, unit=metric.unit, status=status, reason=missing, estimated=metric.estimated,
        evidence=[dict(query=e.query, source=e.source, ids=list(e.ids), matchedCount=e.matched_count,
                       truncated=e.truncated) for e in metric.evidence], limitations=list(dict.fromkeys(limitations)))


def footfall_total(result, field):
    # Day granularity bounds a 31-day selection to <=32 buckets; still fail closed if truncated.
    parts = [getattr(bucket, field) for bucket in result.buckets]
    if result.truncated or not parts or any(part.value is None for part in parts):
        return CountMetric(value=None, unavailable_reason='Complete footfall buckets are not available')
    refs = {}
    for part in parts:
        for e in part.evidence:
            refs.setdefault((e.query, e.source), []).append(e)
    combined = []
    for (query, source), items in refs.items():
        ids = tuple(dict.fromkeys(i for item in items for i in item.ids))
        # Truncated bucket samples cannot be safely unioned into a truthful matched_count.
        if any(item.truncated for item in items):
            return CountMetric(value=None, unavailable_reason='Footfall bucket evidence is sampled; total aggregation deferred')
        combined.append(Evidence(query=query, source=source, ids=ids[:200], matched_count=len(ids), truncated=len(ids) > 200))
    return CountMetric(value=float(sum(part.value for part in parts)), evidence=tuple(combined))


def dashboard_snapshot(config, membership, request, *, now=None):
    membership.authorize(request)
    registry = ScopedToolRegistry(SQLiteAnalyticsTools(config.event_db, synthetic=config.synthetic, contexts=config.contexts), membership.scope())
    args = dict(window=request.window.model_dump(mode='json'), filters=request.filters.event_filters().model_dump(exclude_none=True), limit=1000)
    footfall = registry.invoke('get_footfall', args | {'granularity': 'day'})
    interactions = registry.invoke('get_interactions', args)
    dwell = registry.invoke('get_zone_dwell', args)
    unattended = registry.invoke('get_unattended', args)
    coverage = registry.invoke('get_coverage', args)
    customer = next((row.p50 for row in dwell.by_role if row.role == 'customer'), Metric(value=None, unit='seconds', unavailable_reason='No customer dwell samples'))
    ratio = next((row.staffed_open_ratio for row in coverage.zones if row.zone_id == request.filters.zoneId), Metric(value=None, unit='ratio', unavailable_reason='No selected-zone coverage result'))
    metrics = {
        'entries': present(footfall_total(footfall, 'entries'), footfall),
        'exits': present(footfall_total(footfall, 'exits'), footfall),
        'confirmedInteractions': present(interactions.confirmed_count, interactions),
        'unverifiedInteractions': present(interactions.unverified_count, interactions),
        'meanConfirmedDuration': present(interactions.mean_confirmed_duration, interactions),
        'customerDwellP50': present(customer, dwell),
        'unattendedEpisodes': present(unattended.episode_count, unattended),
        'staffedOpenRatio': present(ratio, coverage),
    }
    stamp = now or datetime.now(timezone.utc)
    return dict(version=1, request=public_request(request),
        provenance=dict(mode='backend', synthetic=config.synthetic,
            label='Backend event analytics — synthetic source' if config.synthetic else 'Backend event analytics'),
        generatedAt=utc(stamp), validUntil=utc(stamp+timedelta(seconds=60)), metrics=metrics,
        limitations=['Database results describe the selected observation window, not a guarantee of a live camera feed.',
                     'The five tools use separate read snapshots; a concurrently updated database may change between tool calls.',
                     'No registered map, account-to-track linkage, business-agent output or operational delivery is inferred.'])
