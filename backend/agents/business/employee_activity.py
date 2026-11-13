"""Employee Activity Agent (Ruhab): staffed coverage, engagement and missed customers.

Policy, in plain terms:
- Coverage is the observed staffed-time union per zone, never roster availability or
  per-employee time. Zones are ordered least-covered first by staffed/open ratio, so the
  biggest gaps lead; zones without operating windows follow, with staffed seconds only.
- Unknown observation time is published whenever it is non-zero, because a zone with
  blind time cannot be called unstaffed or fully staffed.
- Engagement uses confirmed interactions only, with unverified ones disclosed separately.
- Missed customers reuse the stored unattended episodes and keep their provenance caveat.
- No individual employee is ranked or named; the router already refuses such questions.
"""
from ..graph_contracts import SpecialistDraft
from ..specialists import ALLOWED_TOOLS, SpecialistRegistration
from .common import base_arguments, claims_for, mentions, repaired, usable
from .customer_behavior import unattended_paths

MAX_CLAIMS = 30
INTENT_WORDS = {
    'coverage': ('coverage', 'covered', 'staffed', 'understaffed', 'availability', 'available', 'gap', 'gaps', 'presence'),
    'interactions': ('interaction', 'interactions', 'engage', 'engagement', 'engaged', 'help', 'helped', 'assist',
                     'assisted', 'assistance', 'served'),
    'unattended': ('unattended', 'miss', 'missed', 'waiting', 'waited', 'ignored', 'unserved'),
}


def intents(question):
    found = tuple(name for name, words in INTENT_WORDS.items() if mentions(question, *words))
    return found or ('coverage',)


def coverage_paths(result, budget):
    ranked = sorted(enumerate(result.zones), key=lambda item: (
        item[1].staffed_open_ratio.value is None,
        item[1].staffed_open_ratio.value if item[1].staffed_open_ratio.value is not None else 0,
        item[1].zone_id))
    paths = []
    for index, zone in ranked:
        own = []
        if zone.staffed_open_ratio.value is not None:
            own.append(('zones', index, 'staffed_open_ratio'))
        own.append(('zones', index, 'observed_staffed'))
        if zone.unknown_observation.value:
            own.append(('zones', index, 'unknown_observation'))
        if len(paths) + len(own) > budget:
            break
        paths += own
    return paths


def employee_activity_agent(context, tools, prior=None, issues=()):
    if prior is not None:
        return repaired(prior, issues)
    found = intents(context.request.question)
    claims = []
    for intent in found:
        budget = MAX_CLAIMS - len(claims) - 4 * (len(found) - found.index(intent) - 1)
        if intent == 'coverage':
            call_id, result = tools.invoke('get_coverage', base_arguments(context, limit=1000))
            paths = coverage_paths(result, budget) if usable(result) else []
        elif intent == 'interactions':
            call_id, result = tools.invoke('get_interactions', base_arguments(context))
            paths = [('confirmed_count',), ('mean_confirmed_duration',), ('unverified_count',)] if usable(result) else []
        else:
            call_id, result = tools.invoke('get_unattended', base_arguments(context, limit=1000))
            paths = unattended_paths(result) if usable(result) else []
        claims += claims_for(call_id, result, paths)
    return SpecialistDraft(claims=tuple(claims)[:MAX_CLAIMS])


def employee_activity_registration():
    return SpecialistRegistration(employee_activity_agent, ALLOWED_TOOLS['employee_activity'], development_stub=False)


def business_specialists():
    """Both of Ruhab's registrations, for `AnalyticsService(..., specialists=business_specialists())`."""
    from .customer_behavior import customer_behavior_registration
    return {'customer_behavior': customer_behavior_registration(),
            'employee_activity': employee_activity_registration()}
