"""Structured analytics requests and claims; no model-generated answer prose."""
from typing import Annotated, Literal

from pydantic import Field

from .contracts import (Contract, CoverageResult, EventFilters, Evidence, FootfallResult, Identifier,
                        InteractionsResult, TimeWindow, TrustedAccessScope, UnattendedResult, ZoneDwellResult)

Target = Literal['customer_behavior', 'employee_activity', 'unsupported']
ToolResult = Annotated[FootfallResult | ZoneDwellResult | InteractionsResult | UnattendedResult | CoverageResult,
                       Field(discriminator='tool')]


class AskRequest(Contract):
    question: str = Field(min_length=3, max_length=2000, pattern=r'\S')
    window: TimeWindow
    filters: EventFilters = Field(default_factory=EventFilters)
    request_id: Identifier | None = None


class RouteDecision(Contract):
    target: Target


class Claim(Contract):
    """Meaning is rendered from a concrete metric path, never a free-form label."""
    call_id: Identifier
    path: tuple[Annotated[str, Field(min_length=1, max_length=100)] | Annotated[int, Field(strict=True, ge=0)], ...] = Field(min_length=1, max_length=8)
    value: float = Field(strict=True)
    unit: Literal['count', 'seconds', 'ratio', 'percent']
    store_id: Identifier
    window: TimeWindow
    filters: EventFilters
    evidence: tuple[Evidence, ...] = Field(min_length=1, max_length=20)


class SpecialistDraft(Contract):
    claims: tuple[Claim, ...] = Field(default=(), max_length=30)


class GroundingIssue(Contract):
    claim_index: int = Field(ge=0)
    code: Literal['missing_metric', 'wrong_context', 'wrong_value', 'wrong_evidence']


class NodeTrace(Contract):
    node: str
    elapsed_ms: float = Field(ge=0)


class ToolTrace(Contract):
    call_id: Identifier
    tool: str
    elapsed_ms: float = Field(ge=0)
    status: str
    node: str


class GraphLimits(Contract):
    max_steps: int = Field(default=8, strict=True, ge=1, le=12)
    max_tool_calls: int = Field(default=8, strict=True, ge=1, le=20)
    max_result_bytes: int = Field(default=524288, strict=True, ge=1024, le=1048576)


class SpecialistContext(Contract):
    run_id: Identifier
    scope: TrustedAccessScope
    request: AskRequest


class GraphRun(Contract):
    run_id: Identifier
    request_id: Identifier
    scope: TrustedAccessScope
    request: AskRequest
    selected_node: Target
    development_stub: bool
    status: Literal['ok', 'partial', 'insufficient_evidence', 'refused', 'unavailable']
    claims: tuple[Claim, ...] = ()
    citations: tuple[Evidence, ...] = ()
    tool_results: dict[str, ToolResult] = Field(default_factory=dict, max_length=20)
    nodes: tuple[NodeTrace, ...] = Field(default=(), max_length=12)
    tool_calls: tuple[ToolTrace, ...] = Field(default=(), max_length=20)
    errors: tuple[str, ...] = Field(default=(), max_length=30)
    limitations: tuple[str, ...] = Field(default=(), max_length=50)
    repair_attempts: int = Field(default=0, ge=0, le=1)
    steps: int = Field(ge=0, le=12)
    latency_ms: float = Field(ge=0)
    response: str
