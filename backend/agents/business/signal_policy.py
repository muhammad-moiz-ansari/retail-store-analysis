"""Operational signal policy (Ruhab): when a completed window becomes an aisle event.

Pure decisions over typed read-tool results. Nothing here dispatches, writes or calls a
handler: emitted `OperationalEvent`s are handed to Moiz's `OperationalDispatchAdapter`,
and Saqib's handler still decides eligibility and delivery.

Rules (thresholds live in `SignalPolicy`, one config per store):
- unattended_customer: at least one stored episode in the zone with helped=False and a
  wait >= min_wait_s. The stored derivation counts *any* interaction verdict as help, so it
  can only under-report unhelped waits; helped=False episodes are therefore safe to act on.
- unstaffed_zone: staffed/open ratio below min_staffed_ratio while customers were observed
  dwelling in the zone. Requires operating windows; without them the ratio is unavailable.
- Both: suppressed (with a reason code) when coverage is unavailable, the zone's unknown
  observation share exceeds max_unknown_share, or synthetic and real evidence would mix.
  Unknown evidence is never promoted into a confirmed gap.
- crowding: not emitted. No supported occupancy signal exists until MAP-3 layers land.
"""
from datetime import datetime
from hashlib import sha256
from typing import Literal

from pydantic import Field

from ..contracts import Contract, DataStatus, Identifier, TimeWindow
from ..operational import OperationalEvent, OperationalEvidence, SignalEvidence

POLICY_VERSION = 'ruhab-signal-policy-v1'
ReasonCode = Literal['emitted', 'no_demand', 'coverage_unavailable', 'demand_unavailable', 'zone_not_observed',
                     'unknown_observation_too_high', 'staffed_enough', 'no_operating_window', 'mixed_provenance',
                     'window_mismatch']


class SignalPolicy(Contract):
    min_wait_s: float = Field(default=180, ge=0, le=86400)
    high_wait_s: float = Field(default=360, ge=0, le=86400)
    high_episode_count: int = Field(default=3, ge=1)
    min_staffed_ratio: float = Field(default=0.25, ge=0, le=1)
    max_unknown_share: float = Field(default=0.2, ge=0, le=1)
    version: Identifier = POLICY_VERSION


class SignalDecision(Contract):
    event_type: Literal['unattended_customer', 'unstaffed_zone']
    zone_id: Identifier
    reason: ReasonCode
    event: OperationalEvent | None = None


def stable_id(*parts):
    return sha256('|'.join(str(p) for p in parts).encode()).hexdigest()[:32]


def _refs(metrics):
    refs = {}
    for metric in metrics:
        for ref in metric.evidence:
            refs.setdefault(ref.model_dump_json(), ref)
    return tuple(refs.values())[:10]


def _signal(result, zone_id, refs):
    return SignalEvidence(store_id=result.scope.store_id, zone_id=zone_id, window=result.window, status=result.status,
                          synthetic=result.synthetic, evidence=refs, limitations=tuple(result.limitations)[:20])


def _zone(coverage, zone_id):
    return next((z for z in coverage.zones if z.zone_id == zone_id), None)


def _coverage_gate(coverage, zone_id, window, policy):
    """Return (zone summary, reason) where reason is None when coverage evidence is usable."""
    if coverage is None or coverage.status == DataStatus.UNAVAILABLE:
        return None, 'coverage_unavailable'
    if coverage.window != window:
        return None, 'window_mismatch'
    zone = _zone(coverage, zone_id)
    if zone is None or zone.observed_staffed.value is None:
        return None, 'zone_not_observed'
    span = zone.open_seconds.value or (window.end - window.start).total_seconds()
    if (zone.unknown_observation.value or 0) / span > policy.max_unknown_share:
        return zone, 'unknown_observation_too_high'
    return zone, None


def _event(event_type, source, zone_id, window, now, demand, coverage, severity, policy):
    key = stable_id(policy.version, demand.store_id, zone_id, event_type, window.start.isoformat(), window.end.isoformat())
    return OperationalEvent(event_id=f'evt-{key}', idempotency_key=f'key-{key}', store_id=demand.store_id, zone_id=zone_id,
        event_type=event_type, source=source, source_timestamp=now, window=window,
        evidence=OperationalEvidence(demand=demand, coverage=coverage), severity=severity)


def unattended_decision(zone_id, window, now: datetime, unattended, coverage, policy=SignalPolicy()):
    kind = 'unattended_customer'
    if unattended is None or unattended.status == DataStatus.UNAVAILABLE:
        return SignalDecision(event_type=kind, zone_id=zone_id, reason='demand_unavailable')
    if unattended.window != window:
        return SignalDecision(event_type=kind, zone_id=zone_id, reason='window_mismatch')
    waits = [e for e in unattended.episodes if e.zone_id == zone_id and not e.helped
             and e.waited.value is not None and e.waited.value >= policy.min_wait_s]
    if not waits:
        return SignalDecision(event_type=kind, zone_id=zone_id, reason='no_demand')
    zone, blocked = _coverage_gate(coverage, zone_id, window, policy)
    if blocked:
        return SignalDecision(event_type=kind, zone_id=zone_id, reason=blocked)
    if unattended.synthetic != coverage.synthetic:
        return SignalDecision(event_type=kind, zone_id=zone_id, reason='mixed_provenance')
    longest = max(e.waited.value for e in waits)
    severity = 'high' if longest >= policy.high_wait_s or len(waits) >= policy.high_episode_count else 'medium'
    demand = _signal(unattended, zone_id, _refs(e.waited for e in waits))
    cover = _signal(coverage, zone_id, _refs((zone.observed_staffed, zone.unknown_observation)))
    return SignalDecision(event_type=kind, zone_id=zone_id, reason='emitted',
                          event=_event(kind, 'customer_behavior', zone_id, window, now, demand, cover, severity, policy))


def unstaffed_decision(zone_id, window, now: datetime, dwell, coverage, policy=SignalPolicy()):
    kind = 'unstaffed_zone'
    customers = None if dwell is None else next((s for s in dwell.by_role if s.role == 'customer'), None)
    if dwell is None or dwell.status == DataStatus.UNAVAILABLE or customers is None or customers.sample_count.value is None:
        return SignalDecision(event_type=kind, zone_id=zone_id, reason='demand_unavailable')
    if dwell.window != window or dwell.filters.zone_id != zone_id:
        return SignalDecision(event_type=kind, zone_id=zone_id, reason='window_mismatch')
    if not customers.sample_count.value:
        return SignalDecision(event_type=kind, zone_id=zone_id, reason='no_demand')
    zone, blocked = _coverage_gate(coverage, zone_id, window, policy)
    if blocked:
        return SignalDecision(event_type=kind, zone_id=zone_id, reason=blocked)
    if zone.staffed_open_ratio.value is None:
        return SignalDecision(event_type=kind, zone_id=zone_id, reason='no_operating_window')
    if zone.staffed_open_ratio.value >= policy.min_staffed_ratio:
        return SignalDecision(event_type=kind, zone_id=zone_id, reason='staffed_enough')
    if dwell.synthetic != coverage.synthetic:
        return SignalDecision(event_type=kind, zone_id=zone_id, reason='mixed_provenance')
    severity = 'high' if zone.staffed_open_ratio.value < policy.min_staffed_ratio / 2 else 'medium'
    demand = _signal(dwell, zone_id, _refs((customers.sample_count,)))
    cover = _signal(coverage, zone_id, _refs((zone.staffed_open_ratio, zone.observed_staffed, zone.unknown_observation)))
    return SignalDecision(event_type=kind, zone_id=zone_id, reason='emitted',
                          event=_event(kind, 'employee_activity', zone_id, window, now, demand, cover, severity, policy))


def evaluate_zone(registry, zone_id, window: TimeWindow, now: datetime, policy=SignalPolicy()):
    """Read the three needed results through a trusted ScopedToolRegistry and decide both events."""
    window = TimeWindow.model_validate(window)
    args = {'window': window.model_dump(mode='json'), 'filters': {'zone_id': zone_id}}
    unattended = registry.invoke('get_unattended', args | {'min_seconds': policy.min_wait_s, 'limit': 1000})
    dwell = registry.invoke('get_zone_dwell', args)
    coverage = registry.invoke('get_coverage', args | {'limit': 1000})
    return (unattended_decision(zone_id, window, now, unattended, coverage, policy),
            unstaffed_decision(zone_id, window, now, dwell, coverage, policy))
