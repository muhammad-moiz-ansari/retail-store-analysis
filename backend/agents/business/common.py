"""Shared helpers for Ruhab's specialists: argument building, safe claims and repair."""
import re

from ..contracts import MAX_RESULTS, DataStatus
from ..graph_contracts import SpecialistDraft
from ..specialists import claim_for


def base_arguments(context, **extra):
    """Tool arguments always echo the validated window/filters; specialists never broaden them."""
    return {'window': context.request.window.model_dump(mode='json'),
            'filters': context.request.filters.model_dump(exclude_none=True)} | extra


def mentions(question, *words):
    return bool(re.search(r'\b(' + '|'.join(words) + r')\b', question, re.I))


def usable(result):
    """Unavailable results never contribute claims; partial results keep their limitations."""
    return result.status != DataStatus.UNAVAILABLE


def claims_for(call_id, result, paths):
    """Only metrics with a value become claims; null metrics stay unpublished, never zero."""
    return tuple(claim for path in paths if (claim := claim_for(call_id, result, path)) is not None)


def repaired(prior, issues):
    """Drop exactly the claims grounding rejected; never invent replacement numbers."""
    rejected = {issue.claim_index for issue in issues}
    return SpecialistDraft(claims=tuple(c for i, c in enumerate(prior.claims) if i not in rejected),
                           notices=prior.notices)


def bounded_limit(count):
    return max(1, min(MAX_RESULTS, count))
