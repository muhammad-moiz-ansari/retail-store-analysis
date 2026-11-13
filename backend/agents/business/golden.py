"""Golden-question evaluation for Ruhab's two agents (A3: 5+ questions per agent).

Each golden question names the route it should take and the exact metric claims a correct
answer must contain. `evaluate` runs every question through the real AnalyticsService and
reports routing accuracy, answer accuracy, refusal accuracy, grounded-claim rate and latency.

The bundled set (`golden_questions.json`) runs against the labelled SYNTHETIC fixture day in
`fixture_day()`. Its scores measure agent logic and routing, not real-store accuracy.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Literal

from pydantic import Field

from ..contracts import Contract, EventFilters, TimeWindow, TrustedAccessScope
from ..graph_contracts import AskRequest
from ..service import AnalyticsService
from .employee_activity import business_specialists
from .fixture_tools import FixtureAnalyticsTools

GOLDEN_PATH = Path(__file__).with_name('golden_questions.json')
DAY_START = datetime(2026, 11, 3, 9, tzinfo=timezone.utc)
DAY = TimeWindow(start=DAY_START, end=DAY_START + timedelta(hours=8))
HOURLY = (3, 9, 14, 6, 2, 11, 5, 4)


def fixture_day():
    """SYNTHETIC FIXTURE: one hand-authored 8-hour store day used by the golden set."""
    def footfall(window):
        index = int((window.start - DAY_START).total_seconds() // 3600)
        return HOURLY[index], max(0, HOURLY[index] - 1)
    return FixtureAnalyticsTools(
        footfall=footfall,
        dwell={'z1': {'customer': (12, 1800, 95, 410), 'employee': (3, 5400, 1800, 1900), 'unknown': (2, 60, 30, 40)},
               'z2': {'customer': (6, 900, 120, 300)}},
        interactions=dict(confirmed=13, unverified=4, mean_duration=21.5, mean_approach=48, approach_samples=9),
        unattended=[dict(event_id='u1', zone_id='z2', waited_s=240), dict(event_id='u2', zone_id='z1', waited_s=600, helped=True),
                    dict(event_id='u3', zone_id='z3', waited_s=320)],
        coverage={'z1': dict(staffed=20000, unknown=0, open=28800, ratio=0.69),
                  'z2': dict(staffed=4000, unknown=1200, open=28800, ratio=0.14),
                  'z3': dict(staffed=900, unknown=300)})


class ExpectedClaim(Contract):
    path: tuple[str | int, ...]
    value: float


class GoldenQuestion(Contract):
    id: str
    agent: Literal['customer_behavior', 'employee_activity', 'unsupported']
    question: str = Field(min_length=3)
    zone_id: str | None = None
    expect_status: tuple[Literal['ok', 'partial', 'insufficient_evidence', 'refused', 'unavailable'], ...]
    expect_claims: tuple[ExpectedClaim, ...] = ()
    forbid_paths: tuple[tuple[str | int, ...], ...] = ()


class QuestionResult(Contract):
    id: str
    routed_ok: bool
    status_ok: bool
    answer_ok: bool
    selected: str
    status: str
    missing: tuple[str, ...] = ()
    claims: int
    latency_ms: float


class GoldenReport(Contract):
    synthetic: bool
    questions: int
    per_agent: dict[str, int]
    routing_accuracy: float
    answer_accuracy: float
    refusal_accuracy: float | None
    # Share of answering runs whose first draft passed grounding with no repair or removal. GraphRun
    # records that a rejection happened, not how many claims, so this is a per-run rate.
    # None if no run drafted any claim.
    grounded_run_rate: float | None
    median_latency_ms: float
    results: tuple[QuestionResult, ...]


def load_golden(path=GOLDEN_PATH):
    return tuple(GoldenQuestion.model_validate(item) for item in json.loads(Path(path).read_text(encoding='utf-8')))


def _scope():
    return TrustedAccessScope(actor_id='golden-manager', store_id='store-1', role='manager')


def evaluate(questions=None, *, tools=None, specialists=None, window=DAY):
    questions = load_golden() if questions is None else tuple(questions)
    service = AnalyticsService(tools if tools is not None else fixture_day(),
                               specialists=business_specialists() if specialists is None else specialists)
    results, answering, clean, synthetic = [], 0, 0, set()
    for q in questions:
        run = service.ask(AskRequest(question=q.question, window=window, filters=EventFilters(zone_id=q.zone_id)), scope=_scope())
        got = {tuple(c.path): c.value for c in run.claims}
        missing = tuple(str(list(e.path)) for e in q.expect_claims
                        if e.path not in got or abs(got[e.path] - e.value) > 1e-9)
        forbidden = [p for p in q.forbid_paths if tuple(p) in got]
        # A repair pass means grounding rejected part of the first draft, even if the repaired
        # draft then passes and the run's final issue list is empty.
        dirty = run.repair_attempts > 0 or 'unsupported_claims_removed' in run.errors
        if run.claims or dirty:
            answering += 1
            clean += not dirty
        synthetic |= {r.synthetic for r in run.tool_results.values()}
        results.append(QuestionResult(id=q.id, routed_ok=run.selected_node == q.agent, status_ok=run.status in q.expect_status,
            answer_ok=not missing and not forbidden and run.status in q.expect_status, selected=run.selected_node,
            status=run.status, missing=missing + tuple(f'forbidden {list(p)}' for p in forbidden),
            claims=len(run.claims), latency_ms=run.latency_ms))
    per_agent = {}
    for q in questions:
        per_agent[q.agent] = per_agent.get(q.agent, 0) + 1
    refusals = [r for q, r in zip(questions, results) if q.agent == 'unsupported']
    n = len(results) or 1
    return GoldenReport(synthetic=synthetic != {False}, questions=len(results), per_agent=per_agent,
        routing_accuracy=sum(r.routed_ok for r in results) / n, answer_accuracy=sum(r.answer_ok for r in results) / n,
        refusal_accuracy=sum(r.answer_ok for r in refusals) / len(refusals) if refusals else None,
        grounded_run_rate=clean / answering if answering else None,
        median_latency_ms=median(r.latency_ms for r in results) if results else 0.0, results=tuple(results))


def main():
    report = evaluate()
    print(report.model_dump_json(indent=2))
    for r in report.results:
        if not r.answer_ok:
            print(f'FAIL {r.id}: routed={r.selected} status={r.status} missing={list(r.missing)}')


if __name__ == '__main__':
    main()
