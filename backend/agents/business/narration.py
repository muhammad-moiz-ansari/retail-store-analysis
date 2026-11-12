"""Insight Narration / Digest (Ruhab): manager-readable text built only from grounded claims.

The digest never computes new numbers. Every figure it prints is a verified `Claim` value
from a `GraphRun`, and wording comes from fixed server-side templates, not a model.
Provenance (synthetic vs real), run status and limitations are carried into the digest so
a fixture-backed digest can never read like a real-store report.
"""
from typing import Literal

from pydantic import Field

from ..contracts import Contract, TimeWindow
from .signal_policy import SignalDecision

LABELS = {
    ('get_footfall', 'entries'): 'entries', ('get_footfall', 'exits'): 'exits',
    ('get_zone_dwell', 'sample_count'): 'dwell visits', ('get_zone_dwell', 'total'): 'total dwell',
    ('get_zone_dwell', 'p50'): 'median dwell', ('get_zone_dwell', 'p90'): '90th-percentile dwell',
    ('get_interactions', 'confirmed_count'): 'confirmed interactions',
    ('get_interactions', 'unverified_count'): 'unverified interactions (not counted as assistance)',
    ('get_interactions', 'mean_confirmed_duration'): 'average confirmed interaction length',
    ('get_interactions', 'mean_approach'): 'average time to first approach (from first seen on camera)',
    ('get_interactions', 'approach_sample_count'): 'customers in the approach-time sample',
    ('get_unattended', 'episode_count'): 'stored unattended episodes', ('get_unattended', 'waited'): 'longest unhelped wait',
    ('get_coverage', 'staffed_open_ratio'): 'staffed share of open time', ('get_coverage', 'observed_staffed'): 'observed staffed time',
    ('get_coverage', 'unknown_observation'): 'time the camera could not see',
}
SECTIONS = {'get_footfall': 'Traffic', 'get_zone_dwell': 'Dwell', 'get_interactions': 'Assistance',
            'get_unattended': 'Waiting customers', 'get_coverage': 'Staff coverage'}
EVENT_TEXT = {'unattended_customer': 'customer left waiting', 'unstaffed_zone': 'zone short of staff'}


class DigestSection(Contract):
    heading: str
    lines: tuple[str, ...] = Field(min_length=1)


class Digest(Contract):
    title: str
    window: TimeWindow
    provenance: Literal['synthetic', 'real', 'mixed', 'unknown']
    status: Literal['ok', 'partial', 'no_evidence']
    sections: tuple[DigestSection, ...] = ()
    caveats: tuple[str, ...] = ()
    citation_count: int = Field(ge=0)

    def text(self):
        parts = [self.title, f'Window: {_span(self.window)}']
        if self.provenance != 'real':
            source = 'data of unknown provenance' if self.provenance == 'unknown' else f'{self.provenance} data'
            parts.append(f'NOTE: built from {source}, not a verified real-store feed.')
        for section in self.sections:
            parts += ['', section.heading] + [f'- {line}' for line in section.lines]
        if self.caveats:
            parts += ['', 'Caveats'] + [f'- {c}' for c in self.caveats]
        return '\n'.join(parts)


def _span(window):
    return f"{window.start.strftime('%Y-%m-%d %H:%M')}–{window.end.strftime('%H:%M')} UTC"


def _number(value, unit):
    if unit == 'count':
        return f'{value:.0f}'
    if unit == 'ratio':
        return f'{value * 100:.0f}%'
    if unit == 'seconds':
        if value >= 7200:
            return f'{value / 3600:.1f} h'
        return f'{value / 60:.1f} min' if value >= 120 else f'{round(value, 1):g} s'
    return f'{value:g}{"%" if unit == "percent" else ""}'


def _context(claim, result):
    if len(claim.path) >= 3 and isinstance(claim.path[1], int):
        parent = getattr(result, claim.path[0])[claim.path[1]]
        bits = []
        if getattr(parent, 'role', None):
            bits.append(parent.role)
        if getattr(parent, 'zone_id', None):
            bits.append(f'zone {parent.zone_id}')
        if claim.path[0] == 'buckets':
            bits.append(_span(parent.window))
        return f" ({', '.join(bits)})" if bits else ''
    zone = result.filters.zone_id
    return f' (zone {zone})' if zone else ''


def _footfall_lines(items):
    entries = [c for c, _ in items if c.path[-1] == 'entries']
    high = max(entries, key=lambda c: c.value, default=None)
    low = min(entries, key=lambda c: c.value, default=None) if len(entries) > 1 else None
    lines = []
    for claim, results in items:
        prefix = 'Busiest period: ' if low is not None and claim is high else 'Quietest period: ' if claim is low else ''
        lines.append(f'{prefix}{_number(claim.value, claim.unit)} {LABELS[("get_footfall", claim.path[-1])]}'
                     f'{_context(claim, results[claim.call_id])}')
    return lines


def build_digest(runs, *, title='Store digest', decisions: tuple[SignalDecision, ...] = ()):
    runs = tuple(runs)
    if not runs:
        raise ValueError('A digest needs at least one analytics run')
    windows = {run.request.window for run in runs}
    if len(windows) != 1:
        raise ValueError('All runs in one digest must share a window')
    by_section, caveats, synthetic = {}, [], set()
    for run in runs:
        if run.development_stub:
            caveats.append('A development adapter, not a business agent, produced part of this digest.')
        for claim in run.claims:
            result = run.tool_results[claim.call_id]
            by_section.setdefault(result.tool, []).append((claim, run.tool_results))
        synthetic |= {r.synthetic for r in run.tool_results.values()}
        caveats += list(run.limitations)
        if run.status not in ('ok', 'partial'):
            caveats.append(f'No supported evidence for: "{run.request.question}".')
    sections = []
    for tool, heading in SECTIONS.items():
        items = by_section.get(tool, [])
        if not items:
            continue
        if tool == 'get_footfall':
            lines = _footfall_lines(items)
        else:
            lines = [f'{LABELS[(tool, c.path[-1])].capitalize()}: {_number(c.value, c.unit)}{_context(c, results[c.call_id])}'
                     for c, results in items]
        sections.append(DigestSection(heading=heading, lines=tuple(lines)))
    alerts = [d for d in decisions if d.event is not None]
    if alerts:
        sections.append(DigestSection(heading='Raised for staff follow-up', lines=tuple(
            f'{EVENT_TEXT[d.event_type].capitalize()} in zone {d.zone_id} ({d.event.severity} priority)' for d in alerts)))
    synthetic |= {d.event.evidence.demand.synthetic for d in alerts}
    # No tool result means provenance cannot be shown, so it is never presented as real.
    provenance = ('unknown' if not synthetic else 'mixed' if len(synthetic) > 1
                  else 'synthetic' if synthetic == {True} else 'real')
    status = 'no_evidence' if not sections else 'partial' if any(r.status != 'ok' for r in runs) else 'ok'
    citations = {ref.model_dump_json() for run in runs for ref in run.citations}
    return Digest(title=title, window=windows.pop(), provenance=provenance, status=status, sections=tuple(sections),
                  caveats=tuple(dict.fromkeys(caveats)), citation_count=len(citations))
