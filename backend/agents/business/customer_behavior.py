"""Customer Behavior Agent (Ruhab): footfall, dwell, assistance and waiting summaries.

Policy, in plain terms:
- Footfall is summarised as the peak and quietest *full-length* bucket, so a clipped
  edge bucket never looks artificially quiet. Granularity follows the window length.
- Dwell is per zone and per role; customer distribution is reported, and the unknown-role
  sample count is disclosed whenever it is non-zero so role ambiguity stays visible.
- Interactions publish confirmed figures; unverified counts are always disclosed beside
  them and never merged into the confirmed total.
- Unattended waits report the stored episode count and the longest *unhelped* wait, but
  only when the episode list is complete (not truncated).
- Unavailable tool results publish nothing; null metrics are never turned into zero.
"""
from ..specialists import SpecialistRegistration, ALLOWED_TOOLS
from ..graph_contracts import SpecialistDraft
from .common import base_arguments, bounded_limit, claims_for, mentions, repaired, usable

INTENT_WORDS = {
    'footfall': ('footfall', 'traffic', 'entries', 'entry', 'exits', 'visitors', 'visits', 'busy', 'busiest', 'peak', 'quiet', 'quietest'),
    'dwell': ('dwell', 'linger', 'lingering', 'stay', 'stayed', 'time spent'),
    'interactions': ('interaction', 'interactions', 'assist', 'assisted', 'assistance', 'helped', 'approach', 'served'),
    'unattended': ('unattended', 'waiting', 'waited', 'wait', 'ignored', 'unserved'),
}
OVERVIEW = ('footfall', 'interactions', 'unattended')


def intents(question):
    found = tuple(name for name, words in INTENT_WORDS.items() if mentions(question, *words))
    return found or OVERVIEW


def granularity(window):
    span = (window.end - window.start).total_seconds()
    if span <= 3600:
        return 'minute'
    return 'hour' if span <= 2 * 86400 else 'day'


def footfall_paths(result):
    observed = [(i, b) for i, b in enumerate(result.buckets) if b.entries.value is not None]
    if not observed:
        return []
    full = max((b.window.end - b.window.start) for _, b in observed)
    candidates = [(i, b) for i, b in observed if b.window.end - b.window.start == full]
    peak = max(candidates, key=lambda item: (item[1].entries.value, -item[0]))[0]
    paths = [('buckets', peak, 'entries'), ('buckets', peak, 'exits')]
    if len(candidates) > 1:
        quiet = min(candidates, key=lambda item: (item[1].entries.value, item[0]))[0]
        if quiet != peak:
            paths.append(('buckets', quiet, 'entries'))
    return paths


def dwell_paths(result):
    paths = []
    for index, summary in enumerate(result.by_role):
        if summary.role == 'customer':
            paths += [('by_role', index, name) for name in ('sample_count', 'total', 'p50', 'p90')]
        elif summary.role == 'unknown' and summary.sample_count.value:
            paths.append(('by_role', index, 'sample_count'))
    return paths


def unattended_paths(result):
    paths = [('episode_count',)]
    unhelped = [(i, e) for i, e in enumerate(result.episodes) if not e.helped and e.waited.value is not None]
    if unhelped and not result.truncated:
        longest = max(unhelped, key=lambda item: (item[1].waited.value, -item[0]))[0]
        paths.append(('episodes', longest, 'waited'))
    return paths


def customer_behavior_agent(context, tools, prior=None, issues=()):
    if prior is not None:
        return repaired(prior, issues)
    claims, notices = [], []
    for intent in intents(context.request.question):
        if intent == 'footfall':
            grain = granularity(context.request.window)
            seconds = {'minute': 60, 'hour': 3600, 'day': 86400}[grain]
            span = (context.request.window.end - context.request.window.start).total_seconds()
            call_id, result = tools.invoke('get_footfall', base_arguments(
                context, granularity=grain, limit=bounded_limit(int(span // seconds) + 2)))
            paths = footfall_paths(result) if usable(result) and not result.truncated else []
        elif intent == 'dwell':
            if not context.request.filters.zone_id:
                notices.append('zone_required')
                continue
            call_id, result = tools.invoke('get_zone_dwell', base_arguments(context))
            paths = dwell_paths(result) if usable(result) else []
        elif intent == 'interactions':
            call_id, result = tools.invoke('get_interactions', base_arguments(context))
            paths = [('confirmed_count',), ('unverified_count',), ('mean_confirmed_duration',),
                     ('mean_approach',), ('approach_sample_count',)] if usable(result) else []
        else:
            call_id, result = tools.invoke('get_unattended', base_arguments(context, limit=1000))
            paths = unattended_paths(result) if usable(result) else []
        claims += claims_for(call_id, result, paths)
    return SpecialistDraft(claims=tuple(claims)[:30], notices=tuple(dict.fromkeys(notices)))


def customer_behavior_registration():
    return SpecialistRegistration(customer_behavior_agent, ALLOWED_TOOLS['customer_behavior'], development_stub=False)
