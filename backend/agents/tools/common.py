"""Interval/evidence helpers shared by the five fixed analytics tools."""
from datetime import timedelta

from pydantic import Field

from ..contracts import (Contract, CountMetric, Evidence, EventFilters, Identifier,
                         MAX_EVIDENCE_IDS, SecondsMetric, TimeWindow)
from .store import SourceUnavailable


class ObservationContext(Contract):
    """Trusted server configuration, never accepted in registry tool arguments.

    Health is camera-wide even though its zone_id is the camera's home zone.
    Expected cameras cannot be inferred from the presence of event rows.
    """
    context_id: Identifier
    store_id: Identifier
    zone_id: Identifier
    camera_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=100)
    shift: Identifier | None = None
    operating_windows: tuple[TimeWindow, ...] = Field(default=(), max_length=100)


def merge(intervals):
    result = []
    for start, end in sorted(intervals):
        if end <= start:
            continue
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


def intersect(left, right):
    return merge((max(a, c), min(b, d)) for a, b in left for c, d in right if max(a, c) < min(b, d))


def seconds(intervals):
    return sum((end - start).total_seconds() for start, end in merge(intervals))


def clipped(rows, window):
    return [(max(row['_start'], window.start), min(row['_end'], window.end)) for row in rows
            if max(row['_start'], window.start) < min(row['_end'], window.end)]


def evidence(table, rows, tool):
    ids = tuple(dict.fromkeys(row['event_id'] for row in rows))
    if not ids:
        return ()
    return (Evidence(source=table, ids=ids[:MAX_EVIDENCE_IDS], query=tool,
                     matched_count=len(ids), truncated=len(ids) > MAX_EVIDENCE_IDS),)


def metric(kind, value, table, rows, tool, reason="No supported observations"):
    refs = evidence(table, rows, tool)
    if value is None or not refs:
        return kind(value=None, unavailable_reason=reason)
    return kind(value=float(value), evidence=refs)


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    at = (len(values) - 1) * p
    lo = int(at)
    return values[lo] + (values[min(lo + 1, len(values)-1)] - values[lo]) * (at - lo)


def health(session, scope, request, contexts, *, zone=None, shift=None):
    """Return all-camera healthy intervals, supporting health rows, and limitations.

    Unhealthy observations override overlapping healthy records for that camera.
    Without expected-camera configuration, absence cannot establish observed zero.
    """
    configured = [c for c in contexts if c.store_id == scope.store_id and c.shift == shift
                  and (zone is None or c.zone_id == zone)
                  and (scope.allowed_zone_ids is None or c.zone_id in scope.allowed_zone_ids)]
    if request.filters.zone_id:
        configured = [c for c in configured if c.zone_id == request.filters.zone_id]
    if not configured:
        return [], [], ("Expected camera coverage is not configured; absence is not observed zero",)
    expected = set(cam for c in configured for cam in c.camera_ids)
    if scope.allowed_camera_ids is not None and not expected <= set(scope.allowed_camera_ids):
        return [], [], ("Scope omits a camera required for complete zone observation",)
    if request.filters.camera_id and expected != {request.filters.camera_id}:
        return [], [], ("Camera filter omits part of the configured zone observation",)
    rows = []
    try:
        for camera in sorted(expected):
            filters = EventFilters(run_id=request.filters.run_id, camera_id=camera)
            rows.extend(session.rows('pipeline_health', scope, filters, request.window, camera_wide=True))
    except SourceUnavailable as exc:
        return [], [], (str(exc),)
    healthy = [(request.window.start, request.window.end)]
    for camera in sorted(expected):
        own = [r for r in rows if r['camera_id'] == camera]
        good = merge(clipped([r for r in own if r['fps'] > 0 and r['frozen_or_dark'] == 0], request.window))
        bad = merge(clipped([r for r in own if not (r['fps'] > 0 and r['frozen_or_dark'] == 0)], request.window))
        # Subtract bad spans without double counting any employee or health seconds.
        for a, b in bad:
            good = merge((x, min(y, a)) for x, y in good if x < a) + merge((max(x, b), y) for x, y in good if y > b)
            good = merge(good)
        healthy = intersect(healthy, good)
    complete = seconds(healthy) == (request.window.end - request.window.start).total_seconds()
    return healthy, rows, (() if complete else ("Observation has blocked, missing, or unknown-health intervals",))


def count(rows, table, tool, healthy_rows=(), observed=False):
    return metric(CountMetric, len(rows), table if rows else 'pipeline_health', rows or healthy_rows, tool,
                  "No event rows and complete healthy observation is not established") if rows or observed else CountMetric(
                      value=None, unavailable_reason="No event rows and complete healthy observation is not established")
