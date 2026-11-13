"""Stored unattended derivations and observation-aware union coverage."""
from ..contracts import (CountMetric, CoverageRequest, CoverageResult, CoverageSummary, RatioMetric,
                         SecondsMetric, TimeWindow, TrustedAccessScope, UnattendedEpisode,
                         UnattendedRequest, UnattendedResult)
from .analytics import EventAnalytics
from .common import clipped, count, evidence, health, intersect, merge, metric, seconds
from .store import SourceUnavailable, read_session


class PostgresAnalyticsTools(EventAnalytics):
    """All five analytics interfaces; DB path and observation context are server-injected."""

    def get_unattended(self, *, scope: TrustedAccessScope, request: UnattendedRequest) -> UnattendedResult:
        self._context(scope, request, status='empty')
        name = 'get_unattended'
        provenance = ("Stored unattended derivation does not filter interaction verdict; helped is not confirmed assistance",)
        try:
            with read_session(self.dsn) as session:
                rows = session.rows('unattended_episodes', scope, request.filters, request.window)
                rows = [r for r in rows if r['waited_s'] >= request.min_seconds and clipped([r], request.window)]
                if any(r['helped'] not in (0, 1) for r in rows):
                    raise SourceUnavailable("Invalid stored unattended helped flag")
                _, hrows, limits = health(session, scope, request, self.contexts, source='unattended_episodes',
                                          observed_cameras={r['camera_id'] for r in rows})
                episodes = tuple(UnattendedEpisode(event_id=r['event_id'], run_id=r['run_id'], camera_id=r['camera_id'],
                    zone_id=r['zone_id'], customer_track_id=r['customer_track_id'], helped=bool(r['helped']),
                    window=TimeWindow(start=max(r['_start'], request.window.start), end=min(r['_end'], request.window.end)),
                    waited=metric(SecondsMetric, seconds(clipped([r], request.window)), 'unattended_episodes', [r], name))
                    for r in rows[:request.limit])
                truncated = len(rows) > request.limit
                limits += ("Episode rows truncated; episode_count includes all selected stored episodes",) if truncated else ()
                return UnattendedResult(**self._context(scope, request, status='partial', limitations=provenance+limits,
                    truncated=truncated), episodes=episodes, episode_count=count(rows, 'unattended_episodes', name, hrows, not limits))
        except SourceUnavailable as exc:
            return UnattendedResult(**self._context(scope, request, status='unavailable', limitations=provenance+(str(exc),)),
                                    episode_count=CountMetric(value=None, unavailable_reason="Stored episode source unavailable"))

    def get_coverage(self, *, scope: TrustedAccessScope, request: CoverageRequest) -> CoverageResult:
        self._context(scope, request, status='empty')
        name = 'get_coverage'
        base = ("Coverage is healthy observed employee-presence union, not roster availability or employee-seconds",)
        try:
            with read_session(self.dsn) as session:
                rows = session.rows('zone_dwell', scope, request.filters, request.window)
                contexts = [c for c in self.contexts if c.store_id == scope.store_id and c.shift == request.shift
                            and (scope.allowed_zone_ids is None or c.zone_id in scope.allowed_zone_ids)
                            and (request.filters.zone_id is None or c.zone_id == request.filters.zone_id)]
                if request.shift is not None and not contexts:
                    raise SourceUnavailable("Requested shift has no trusted observation/operating context")
                zones = sorted({r['zone_id'] for r in rows} | {c.zone_id for c in contexts})
                if request.filters.zone_id:
                    zones = [request.filters.zone_id]
                summaries, limitations = [], []
                for zone in zones:
                    configured = [c for c in contexts if c.zone_id == zone]
                    if len(configured) > 1:
                        raise SourceUnavailable("Ambiguous trusted context for the requested zone/shift")
                    context = configured[0] if configured else None
                    operating = intersect(merge((w.start, w.end) for w in context.operating_windows),
                                          [(request.window.start, request.window.end)]) if context and context.operating_windows else []
                    target = operating if context and context.operating_windows else [(request.window.start, request.window.end)]
                    healthy, hrows, problems = health(session, scope, request, self.contexts, source='zone_dwell',
                        zone=zone, shift=request.shift, observed_cameras={r['camera_id'] for r in rows if r['zone_id'] == zone})
                    healthy = intersect(healthy, target)
                    staff = [r for r in rows if r['zone_id'] == zone and r['role'] == 'employee']
                    supported = [r for r in staff if seconds(intersect(clipped([r], request.window), healthy)) > 0]
                    staffed = seconds(intersect(clipped(staff, request.window), healthy))
                    unknown = max(0.0, seconds(target) - seconds(healthy))
                    # Health rows ground observation and context ID/windows disclose
                    # the independent trusted operating denominator. Never invent a table.
                    refs = evidence('pipeline_health', hrows, name)
                    presence = SecondsMetric(value=None, unavailable_reason="No configured, supported observation evidence")
                    missing = SecondsMetric(value=None, unavailable_reason="Observation coverage cannot be quantified")
                    opening = SecondsMetric(value=None, unavailable_reason="Trusted operating windows are not supplied")
                    ratio = RatioMetric(value=None, unavailable_reason="A complete observed operating denominator is required")
                    if refs:
                        presence = SecondsMetric(value=float(staffed), evidence=evidence('zone_dwell', supported, name)+refs)
                        missing = SecondsMetric(value=float(unknown), evidence=refs)
                        if context and context.operating_windows:
                            opening = SecondsMetric(value=float(seconds(operating)), evidence=refs)
                            if unknown == 0 and seconds(operating) > 0:
                                ratio = RatioMetric(value=staffed/seconds(operating), evidence=presence.evidence)
                    if not context or not context.operating_windows:
                        limitations.append(f"{zone}: no trusted operating-hours denominator; staffed/open ratio unavailable")
                    if unknown > 0 or not refs:
                        limitations.extend(f"{zone}: {message}" for message in problems)
                    summaries.append(CoverageSummary(zone_id=zone, observed_staffed=presence, unknown_observation=missing,
                        open_seconds=opening, staffed_open_ratio=ratio,
                        evaluated_windows=tuple(TimeWindow(start=a, end=b) for a, b in target),
                        operating_windows=tuple(TimeWindow(start=a, end=b) for a, b in operating),
                        operating_context_id=context.context_id if context else None))
                truncated = len(summaries) > request.limit
                if truncated:
                    limitations.append("Zone rows truncated after interval calculations")
                if not summaries:
                    limitations.append("No scoped zones or trusted observation context; no coverage zero inferred")
                return CoverageResult(**self._context(scope, request, status='partial' if limitations else 'ok',
                    limitations=base+tuple(limitations), truncated=truncated), zones=tuple(summaries[:request.limit]))
        except SourceUnavailable as exc:
            return CoverageResult(**self._context(scope, request, status='unavailable', limitations=base+(str(exc),)))
