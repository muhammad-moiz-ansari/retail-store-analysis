"""Golden-question regression on the SYNTHETIC FIXTURE day, through the real router and graph."""
from ..graph_contracts import SpecialistDraft
from ..specialists import ALLOWED_TOOLS, SpecialistRegistration, claim_for
from .common import base_arguments
from .golden import GoldenQuestion, evaluate, load_golden
from .test_customer_behavior import offline  # noqa: F401

# Known gaps in Moiz's OfflineRouter (routing.py), kept visible instead of hidden. Empty since 14 Nov 2026:
# EA1 ("staffing gaps") was refused because \bstaff\b missed "staffing"; the router now routes staffing/gaps.
KNOWN_ROUTER_GAPS: set[str] = set()


def test_golden_set_has_five_or_more_questions_per_agent():
    counts = {}
    for q in load_golden():
        counts[q.agent] = counts.get(q.agent, 0) + 1
    assert counts['customer_behavior'] >= 5 and counts['employee_activity'] >= 5 and counts['unsupported'] >= 3


def test_golden_answers_and_refusals():
    report = evaluate()
    assert report.synthetic and report.questions == len(load_golden())
    failing = {r.id for r in report.results if not r.answer_ok}
    assert failing == KNOWN_ROUTER_GAPS, [r for r in report.results if not r.answer_ok]
    for gap in KNOWN_ROUTER_GAPS:
        result = next(r for r in report.results if r.id == gap)
        assert not result.routed_ok, 'Router gap fixed: remove it from KNOWN_ROUTER_GAPS'
    assert report.refusal_accuracy == 1.0 and report.grounded_run_rate == 1.0


def test_wrong_claims_are_counted_against_grounding():
    def bad_handler(context, tools, prior=None, issues=()):
        call_id, result = tools.invoke('get_interactions', base_arguments(context))
        claim = claim_for(call_id, result, ('confirmed_count',))
        if prior is None:
            claim = claim.model_copy(update={'value': claim.value + 5})  # invented number
            return SpecialistDraft(claims=(claim,))
        return SpecialistDraft()
    question = GoldenQuestion(id='X1', agent='customer_behavior', question='How many interactions were confirmed?',
                              expect_status=('ok',), expect_claims=({'path': ('confirmed_count',), 'value': 13},))
    report = evaluate([question], specialists={'customer_behavior': SpecialistRegistration(
        bad_handler, ALLOWED_TOOLS['customer_behavior'], development_stub=False)})
    assert report.answer_accuracy == 0 and report.grounded_run_rate == 0
