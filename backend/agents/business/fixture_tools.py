"""SYNTHETIC FIXTURE ONLY: hand-authored in-memory analytics results for offline tests.

`FixtureAnalyticsTools` satisfies Moiz's `AnalyticsTools` Protocol without PostgreSQL.
Every result it returns is marked `synthetic=True` and carries a FIXTURE limitation,
so nothing built on it can be mistaken for real camera output.
"""
from datetime import timedelta, timezone, datetime

from ..contracts import (CountMetric, CoverageResult, CoverageSummary, DataStatus, DwellSummary, Evidence,
                         FootfallBucket, FootfallResult, InteractionsResult, RatioMetric, SecondsMetric,
                         TimeWindow, UnattendedEpisode, UnattendedResult, ZoneDwellResult)

FIXTURE_NOTE = "FIXTURE: hand-authored synthetic result, not real camera or event data"
STEP_SECONDS = {'minute': 60, 'hour': 3600, 'day': 86400}


def evidence(tool, source, ids):
    ids = tuple(ids)
    return (Evidence(source=source, ids=ids, query=tool, matched_count=len(ids)),) if ids else ()


def metric(kind, value, tool, source, ids, reason="FIXTURE: not observed"):
    if value is None:
        return kind(value=None, unavailable_reason=reason)
    return kind(value=float(value), evidence=evidence(tool, source, ids or (f'{source}-fixture',)))


def _context(scope, request, status, limitations=()):
    status = DataStatus(status)
    return dict(scope=scope, window=request.window, filters=request.filters, synthetic=True,
                status=status, limitations=(FIXTURE_NOTE, *limitations))


class FixtureAnalyticsTools:
    """Per-tool scenario data; omitted tools return an explicit unavailable result.

    Scenario keys (all optional):
      footfall: callable(bucket_window) -> (entries | None, exits | None)
      dwell: {zone_id: {role: (samples, total_s, p50_s, p90_s)}}
      interactions: dict(confirmed, unverified, mean_duration, mean_approach, approach_samples)
      unattended: list of dict(event_id, zone_id, track, start_s, waited_s, helped)
      coverage: {zone_id: dict(staffed, unknown, open, ratio)}
      status: {tool_name: 'partial' | 'unavailable'}
    """

    def __init__(self, **scenario):
        self.scenario = scenario
        self.calls = []

    def _status(self, name, default='ok'):
        status = self.scenario.get('status', {}).get(name, default)
        notes = (f'FIXTURE: {name} declared {status}',) if status in ('partial', 'unavailable') else ()
        return status, notes

    def get_footfall(self, *, scope, request):
        self.calls.append('get_footfall')
        name = 'get_footfall'
        status, notes = self._status(name, 'ok' if 'footfall' in self.scenario else 'unavailable')
        occupancy = CountMetric(value=None, unavailable_reason="FIXTURE: initial occupancy not supplied")
        if status == 'unavailable':
            return FootfallResult(**_context(scope, request, status, notes or ('FIXTURE: no footfall feed',)), occupancy=occupancy)
        step = STEP_SECONDS[request.granularity.value]
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        start = epoch + timedelta(seconds=((request.window.start - epoch).total_seconds() // step) * step)
        buckets, index = [], 0
        while start < request.window.end:
            window = TimeWindow(start=max(start, request.window.start), end=min(start + timedelta(seconds=step), request.window.end))
            entries, exits = self.scenario['footfall'](window)
            buckets.append(FootfallBucket(window=window,
                entries=metric(CountMetric, entries, name, 'footfall', [f'in-{index}-{i}' for i in range(int(entries or 0))]),
                exits=metric(CountMetric, exits, name, 'footfall', [f'out-{index}-{i}' for i in range(int(exits or 0))])))
            start += timedelta(seconds=step)
            index += 1
        truncated = len(buckets) > request.limit
        return FootfallResult(**_context(scope, request, 'partial' if truncated else status,
                                         notes + (('FIXTURE: buckets truncated',) if truncated else ())),
                              truncated=truncated, buckets=tuple(buckets[:request.limit]), occupancy=occupancy)

    def get_zone_dwell(self, *, scope, request):
        self.calls.append('get_zone_dwell')
        name = 'get_zone_dwell'
        zone = request.filters.zone_id
        rows = self.scenario.get('dwell', {}).get(zone)
        status, notes = self._status(name, 'ok' if rows is not None else 'unavailable')
        if status == 'unavailable':
            return ZoneDwellResult(**_context(scope, request, status, notes or ('FIXTURE: zone not observed',)))
        summaries = []
        for role in ('customer', 'employee', 'unknown'):
            samples, total, p50, p90 = rows.get(role, (0, 0, None, None))
            ids = [f'dwell-{zone}-{role}-{i}' for i in range(samples)]
            summaries.append(DwellSummary(role=role,
                sample_count=metric(CountMetric, samples, name, 'zone_dwell', ids or [f'health-{zone}'] ),
                total=metric(SecondsMetric, total, name, 'zone_dwell', ids or [f'health-{zone}']),
                p50=metric(SecondsMetric, p50, name, 'zone_dwell', ids, 'No positive clipped dwell samples'),
                p90=metric(SecondsMetric, p90, name, 'zone_dwell', ids, 'No positive clipped dwell samples')))
        return ZoneDwellResult(**_context(scope, request, status, notes), by_role=tuple(summaries))

    def get_interactions(self, *, scope, request):
        self.calls.append('get_interactions')
        name = 'get_interactions'
        data = self.scenario.get('interactions')
        status, notes = self._status(name, 'ok' if data is not None else 'unavailable')
        if status == 'unavailable':
            missing = CountMetric(value=None, unavailable_reason='FIXTURE: source unavailable')
            missing_s = SecondsMetric(value=None, unavailable_reason='FIXTURE: source unavailable')
            return InteractionsResult(**_context(scope, request, status, notes or ('FIXTURE: no interaction feed',)),
                confirmed_count=missing, unverified_count=missing, mean_confirmed_duration=missing_s,
                mean_approach=missing_s, approach_sample_count=missing)
        confirmed = [f'int-{i}' for i in range(data.get('confirmed', 0))]
        unverified = [f'unv-{i}' for i in range(data.get('unverified', 0))]
        return InteractionsResult(**_context(scope, request, status, notes),
            confirmed_count=metric(CountMetric, len(confirmed), name, 'interactions', confirmed),
            unverified_count=metric(CountMetric, len(unverified), name, 'interactions', unverified),
            mean_confirmed_duration=metric(SecondsMetric, data.get('mean_duration'), name, 'interactions', confirmed, 'No confirmed interactions'),
            mean_approach=metric(SecondsMetric, data.get('mean_approach'), name, 'interactions', confirmed, 'No approach samples'),
            approach_sample_count=metric(CountMetric, data.get('approach_samples'), name, 'interactions', confirmed, 'No approach samples'))

    def get_unattended(self, *, scope, request):
        self.calls.append('get_unattended')
        name = 'get_unattended'
        rows = self.scenario.get('unattended')
        # The real reader is always partial: stored derivation does not filter verdict.
        status, notes = self._status(name, 'partial' if rows is not None else 'unavailable')
        notes += ("Stored unattended derivation does not filter interaction verdict; helped is not confirmed assistance",)
        if status == 'unavailable':
            return UnattendedResult(**_context(scope, request, status, notes),
                                    episode_count=CountMetric(value=None, unavailable_reason='FIXTURE: source unavailable'))
        rows = [r for r in rows if r['waited_s'] >= request.min_seconds
                and (request.filters.zone_id is None or r['zone_id'] == request.filters.zone_id)]
        episodes = tuple(UnattendedEpisode(event_id=r['event_id'], run_id='fixture-run', camera_id='fixture-cam',
            zone_id=r['zone_id'], customer_track_id=r.get('track', i), helped=r.get('helped', False),
            window=TimeWindow(start=request.window.start + timedelta(seconds=r.get('start_s', 0)),
                              end=request.window.start + timedelta(seconds=r.get('start_s', 0) + r['waited_s'])),
            waited=metric(SecondsMetric, r['waited_s'], name, 'unattended_episodes', [r['event_id']]))
            for i, r in enumerate(rows[:request.limit]))
        truncated = len(rows) > request.limit
        return UnattendedResult(**_context(scope, request, status, notes), truncated=truncated, episodes=episodes,
            episode_count=metric(CountMetric, len(rows), name, 'unattended_episodes',
                                 [r['event_id'] for r in rows] or ['health-fixture']))

    def get_coverage(self, *, scope, request):
        self.calls.append('get_coverage')
        name = 'get_coverage'
        zones = self.scenario.get('coverage')
        status, notes = self._status(name, 'ok' if zones is not None else 'unavailable')
        if status == 'unavailable':
            return CoverageResult(**_context(scope, request, status, notes or ('FIXTURE: no coverage context',)))
        summaries = []
        for zone_id, row in sorted(zones.items()):
            if request.filters.zone_id is not None and zone_id != request.filters.zone_id:
                continue
            ids = [f'cov-{zone_id}']
            summaries.append(CoverageSummary(zone_id=zone_id,
                observed_staffed=metric(SecondsMetric, row.get('staffed'), name, 'zone_dwell', ids),
                unknown_observation=metric(SecondsMetric, row.get('unknown'), name, 'pipeline_health', ids),
                open_seconds=metric(SecondsMetric, row.get('open'), name, 'pipeline_health', ids, 'No operating window supplied'),
                staffed_open_ratio=metric(RatioMetric, row.get('ratio'), name, 'zone_dwell', ids, 'No operating window supplied')))
        return CoverageResult(**_context(scope, request, status, notes), zones=tuple(summaries[:request.limit]))
