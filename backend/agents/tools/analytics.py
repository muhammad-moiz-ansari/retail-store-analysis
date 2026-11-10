"""Read-only footfall, dwell and interaction metrics over Saqib's existing schema."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..contracts import (CountMetric, DwellSummary, EventFilters, FootfallBucket, FootfallRequest, FootfallResult,
                         InteractionsRequest, InteractionsResult, SecondsMetric, TimeWindow,
                         TrustedAccessScope, ZoneDwellRequest, ZoneDwellResult)
from .common import ObservationContext, clipped, count, evidence, health, intersect, metric, percentile, seconds
from .store import SourceUnavailable, read_session


class EventAnalytics:
    def __init__(self, path: Path | str, *, synthetic: bool, contexts=()):
        self.path = Path(path)
        self.synthetic = synthetic
        self.contexts = tuple(ObservationContext.model_validate(c) for c in contexts)

    def _context(self, scope, request, *, status, limitations=(), truncated=False):
        scope.validate_filters(request.filters)
        if scope.role != 'manager':
            raise PermissionError("Aggregate analytics require a trusted manager scope")
        return dict(scope=scope, window=request.window, filters=request.filters, synthetic=self.synthetic,
                    status=status, limitations=tuple(dict.fromkeys(limitations)), truncated=truncated)

    def get_footfall(self, *, scope: TrustedAccessScope, request: FootfallRequest) -> FootfallResult:
        self._context(scope, request, status='empty')
        name = 'get_footfall'
        occupancy = CountMetric(value=None, unavailable_reason="Initial occupancy and complete entrance coverage are not supplied")
        base = ("Footfall is stored net per-track crossing, not every entrance crossing; runs are not person-deduplicated",)
        try:
            with read_session(self.path) as session:
                rows = session.rows('footfall', scope, request.filters, request.window)
                if any(r['direction'] not in ('in', 'out') for r in rows):
                    raise SourceUnavailable("Unknown footfall direction")
                healthy, hrows, limits = health(session, scope, request, self.contexts, source='footfall',
                                                observed_cameras={r['camera_id'] for r in rows})
                step = {'minute': 60, 'hour': 3600, 'day': 86400}[request.granularity]
                epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
                start = epoch + timedelta(seconds=((request.window.start - epoch).total_seconds() // step) * step)
                buckets = []
                while start < request.window.end:
                    window = TimeWindow(start=max(start, request.window.start), end=min(start+timedelta(seconds=step), request.window.end))
                    observed = seconds(intersect(healthy, [(window.start, window.end)])) == (window.end-window.start).total_seconds()
                    bucket_health = [r for r in hrows if r['_start'] < window.end and r['_end'] > window.start]
                    own = [r for r in rows if window.start <= r['_start'] < window.end]
                    buckets.append(FootfallBucket(window=window, **{
                        key: count([r for r in own if r['direction'] == direction], 'footfall', name, bucket_health, observed)
                        for key, direction in (('entries', 'in'), ('exits', 'out'))}))
                    start += timedelta(seconds=step)
                truncated = len(buckets) > request.limit
                limits += ("Result buckets truncated; metrics were computed before the result cap",) if truncated else ()
                return FootfallResult(**self._context(scope, request, status='partial' if limits else 'ok',
                                       limitations=base+limits, truncated=truncated), buckets=tuple(buckets[:request.limit]), occupancy=occupancy)
        except SourceUnavailable as exc:
            return FootfallResult(**self._context(scope, request, status='unavailable', limitations=base+(str(exc),)), occupancy=occupancy)

    def get_zone_dwell(self, *, scope: TrustedAccessScope, request: ZoneDwellRequest) -> ZoneDwellResult:
        self._context(scope, request, status='empty')
        name = 'get_zone_dwell'
        try:
            with read_session(self.path) as session:
                rows = session.rows('zone_dwell', scope, request.filters, request.window)
                if any(r['role'] not in ('customer', 'employee', 'unknown') for r in rows):
                    raise SourceUnavailable("Unknown zone_dwell role")
                rows = [r for r in rows if clipped([r], request.window)]
                _, hrows, limits = health(session, scope, request, self.contexts, source='zone_dwell', zone=request.filters.zone_id,
                                          observed_cameras={r['camera_id'] for r in rows})
                summaries = []
                for role in ('customer', 'employee', 'unknown'):
                    own = [r for r in rows if r['role'] == role]
                    values = [seconds(clipped([r], request.window)) for r in own]
                    summaries.append(DwellSummary(role=role, sample_count=count(own, 'zone_dwell', name, hrows, not limits),
                        total=metric(SecondsMetric, sum(values) if own or not limits else None,
                                     'zone_dwell' if own else 'pipeline_health', own or hrows, name),
                        p50=metric(SecondsMetric, percentile(values, .5), 'zone_dwell', own, name, 'No positive clipped dwell samples'),
                        p90=metric(SecondsMetric, percentile(values, .9), 'zone_dwell', own, name, 'No positive clipped dwell samples')))
                truncated = len(summaries) > request.limit
                limits += ("Role rows truncated; distributions use all selected samples",) if truncated else ()
                return ZoneDwellResult(**self._context(scope, request, status='partial' if limits else 'ok',
                    limitations=("Dwell samples are clipped visits, not unique people",)+limits, truncated=truncated),
                    by_role=tuple(summaries[:request.limit]))
        except SourceUnavailable as exc:
            return ZoneDwellResult(**self._context(scope, request, status='unavailable', limitations=(str(exc),)))

    def get_interactions(self, *, scope: TrustedAccessScope, request: InteractionsRequest) -> InteractionsResult:
        self._context(scope, request, status='empty')
        name = 'get_interactions'
        missing_count = CountMetric(value=None, unavailable_reason="Event source unavailable")
        missing_seconds = SecondsMetric(value=None, unavailable_reason="Event source unavailable")
        try:
            with read_session(self.path) as session:
                rows = session.rows('interactions', scope, request.filters, request.window)
                confirmed = [r for r in rows if r['verdict'] == 'interaction']
                unverified = [r for r in rows if r['verdict'] == 'unverified']
                _, hrows, limits = health(session, scope, request, self.contexts, source='interactions',
                                          observed_cameras={r['camera_id'] for r in rows})
                observed = not limits
                if len(confirmed)+len(unverified) != len(rows):
                    limits += ("Unknown verdicts excluded from confirmed/unverified metrics",)
                approaches, approach_rows, track_rows = [], [], []
                try:
                    if scope.allowed_zone_ids is not None:
                        raise SourceUnavailable("First-confirmed approach history cannot be established under zone-restricted access")
                    # A camera track's dominant zone can differ from its interaction zone.
                    # Omit only the request's zone filter, never trusted zone restrictions.
                    filters = EventFilters(run_id=request.filters.run_id, camera_id=request.filters.camera_id)
                    tracks = session.rows('tracks', scope, filters)
                    history = session.rows('interactions', scope, filters)
                    key = lambda r, column: (r['store_id'], r['run_id'], r['camera_id'], r[column])
                    indexed = {}
                    for track in tracks:
                        indexed.setdefault(key(track, 'track_id'), []).append(track)
                    first = {}
                    for event in history:
                        if event['verdict'] == 'interaction':
                            first.setdefault(key(event, 'customer_track_id'), event['event_id'])
                    for event in confirmed:
                        matches = indexed.get(key(event, 'customer_track_id'), [])
                        if len(matches) != 1 or first.get(key(event, 'customer_track_id')) != event['event_id']:
                            continue
                        track = matches[0]
                        if track['role'] == 'customer' and track['_start'] <= event['_start'] <= track['_end']:
                            approaches.append((event['_start'] - track['_start']).total_seconds())
                            approach_rows.append(event)
                            track_rows.append(track)
                except SourceUnavailable as exc:
                    limits += (str(exc),)
                if len(approaches) < len(confirmed):
                    limits += ("Approach samples exclude later interactions and missing, ambiguous or invalid customer-track joins",)
                approach = SecondsMetric(value=None, unavailable_reason="No supported first-confirmed camera-first-seen samples")
                sample = CountMetric(value=None, unavailable_reason="No supported approach samples")
                if approaches:
                    refs = evidence('interactions', approach_rows, name) + evidence('tracks', track_rows, name)
                    approach = SecondsMetric(value=sum(approaches)/len(approaches), evidence=refs)
                    sample = CountMetric(value=float(len(approaches)), evidence=refs)
                return InteractionsResult(**self._context(scope, request, status='partial' if limits else 'ok',
                    limitations=("Approach reference is camera_first_seen, not store or zone entry",)+limits),
                    confirmed_count=count(confirmed, 'interactions', name, hrows, observed),
                    unverified_count=count(unverified, 'interactions', name, hrows, observed),
                    mean_confirmed_duration=metric(SecondsMetric, sum(seconds(clipped([r], request.window)) for r in confirmed)/len(confirmed)
                        if confirmed else None, 'interactions', confirmed, name, 'No confirmed interactions'),
                    mean_approach=approach, approach_sample_count=sample)
        except SourceUnavailable as exc:
            return InteractionsResult(**self._context(scope, request, status='unavailable', limitations=(str(exc),)),
                confirmed_count=missing_count, unverified_count=missing_count, mean_confirmed_duration=missing_seconds,
                mean_approach=missing_seconds, approach_sample_count=missing_count)
