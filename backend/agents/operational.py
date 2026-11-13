"""Internal operational handoff only; no query graph, HTTP, DB writes or delivery.

Saqib supplies the future trusted dispatch callback and durable idempotency.
No callback is registered by default. This module never imports backend.app.
"""
from datetime import datetime
from time import perf_counter
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .contracts import Contract, DataStatus, Evidence, Identifier, TimeWindow

SourceAgent = Literal['customer_behavior', 'employee_activity']
EventType = Literal['unattended_customer', 'unstaffed_zone', 'crowding']
Decision = Literal['dispatched', 'no_eligible_employee', 'duplicate', 'unavailable', 'error']


class OperationalModel(Contract):
    model_config = ConfigDict(populate_by_name=True)


class SignalEvidence(OperationalModel):
    """Scoped source references, not a new demand/eligibility policy or row verifier."""
    store_id: Identifier = Field(alias='storeId')
    zone_id: Identifier = Field(alias='zoneId')
    window: TimeWindow
    status: DataStatus
    synthetic: bool = Field(strict=True)
    evidence: tuple[Evidence, ...] = Field(min_length=1, max_length=10)
    limitations: tuple[Annotated[str, Field(min_length=1, max_length=1000)], ...] = Field(default=(), max_length=20)


class OperationalEvidence(OperationalModel):
    demand: SignalEvidence
    coverage: SignalEvidence


class OperationalEvent(OperationalModel):
    event_id: Identifier = Field(alias='eventId')
    idempotency_key: Identifier = Field(alias='idempotencyKey')
    store_id: Identifier = Field(alias='storeId')
    zone_id: Identifier = Field(alias='zoneId')
    event_type: EventType = Field(alias='eventType')
    source: SourceAgent
    source_timestamp: datetime = Field(alias='sourceTimestamp')
    window: TimeWindow
    evidence: OperationalEvidence
    severity: Literal['low', 'medium', 'high'] = 'medium'

    @field_validator('source_timestamp', mode='before')
    @classmethod
    def utc_timestamp(cls, value):
        return TimeWindow.aware_iso_input(value)

    @model_validator(mode='after')
    def consistent_evidence_context(self):
        if self.source_timestamp < self.window.end:
            raise ValueError('sourceTimestamp must not precede the completed evidence window')
        for signal in (self.evidence.demand, self.evidence.coverage):
            if (signal.store_id, signal.zone_id, signal.window) != (self.store_id, self.zone_id, self.window):
                raise ValueError('Demand and coverage must match the event store, zone and window')
        if self.evidence.demand.synthetic != self.evidence.coverage.synthetic:
            raise ValueError('Synthetic and real evidence cannot be combined')
        if any(ref.query != 'get_coverage' or ref.source not in ('zone_dwell', 'pipeline_health')
               for ref in self.evidence.coverage.evidence):
            raise ValueError('Coverage references must come from scoped coverage metrics')
        return self


class TrustedOperationalScope(OperationalModel):
    """Constructed by the internal producer/consumer integration, never a query body.

    This model validates an asserted capability; it does not authenticate a caller.
    """
    service_id: Identifier
    store_id: Identifier
    allowed_zone_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=1000)
    allowed_sources: tuple[SourceAgent, ...] = Field(default=('customer_behavior', 'employee_activity'), min_length=1, max_length=2)

    def validate_event(self, event):
        if (event.store_id != self.store_id or event.zone_id not in self.allowed_zone_ids
                or event.source not in self.allowed_sources):
            raise PermissionError('Operational event is outside the trusted producer scope')


class DispatchOutcome(OperationalModel):
    """Callback-reported outcome, not proof that a task/voice message was delivered."""
    event_id: Identifier = Field(alias='eventId')
    idempotency_key: Identifier = Field(alias='idempotencyKey')
    store_id: Identifier = Field(alias='storeId')
    zone_id: Identifier = Field(alias='zoneId')
    decision: Decision
    task_id: Identifier | None = Field(default=None, alias='taskId')
    selected_employee_id: Identifier | None = Field(default=None, alias='selectedEmployeeId')
    alert_id: Identifier | None = Field(default=None, alias='alertId')

    @model_validator(mode='after')
    def consistent_assignment(self):
        if self.decision == 'dispatched' and (self.task_id is None or self.selected_employee_id is None):
            raise ValueError('Dispatched outcomes require taskId and selectedEmployeeId')
        if (self.task_id is None) != (self.selected_employee_id is None):
            raise ValueError('Task and employee references must be present together')
        if self.decision not in ('dispatched', 'duplicate') and self.task_id is not None:
            raise ValueError('Non-assignment outcomes cannot claim a task')
        return self


class DispatchReceipt(DispatchOutcome):
    handler_invoked: bool
    synthetic: bool
    elapsed_ms: float = Field(ge=0)
    reason_code: Literal['handler_reported', 'handler_not_registered', 'handler_error',
                         'invalid_handler_result', 'mismatched_handler_result']
    limitations: tuple[str, ...]


class DispatchHandler(Protocol):
    def __call__(self, *, event: OperationalEvent, scope: TrustedOperationalScope) -> DispatchOutcome: ...


class OperationalDispatchAdapter:
    def __init__(self, handler: DispatchHandler | None = None):
        if handler is not None and not callable(handler):
            raise TypeError('Dispatch handler must be callable')
        self._handler = handler

    def handle(self, event: OperationalEvent, *, scope: TrustedOperationalScope) -> DispatchReceipt:
        if not isinstance(scope, TrustedOperationalScope):
            raise PermissionError('Internal operational scope is required, not a manager query scope')
        # Revalidate even model instances: producer model_copy updates can bypass validators.
        event = OperationalEvent.model_validate(event.model_dump() if isinstance(event, BaseModel) else event)
        scope.validate_event(event)
        started = perf_counter()
        identity = dict(event_id=event.event_id, idempotency_key=event.idempotency_key,
                        store_id=event.store_id, zone_id=event.zone_id)
        limits = ('Handler-reported outcome only; selection, source-zone safety, durable idempotency and delivery belong to Saqib',)

        def receipt(outcome, invoked, code, extra=()):
            return DispatchReceipt(**outcome.model_dump(), handler_invoked=invoked,
                synthetic=event.evidence.demand.synthetic, elapsed_ms=(perf_counter()-started)*1000,
                reason_code=code, limitations=limits+extra)

        if self._handler is None:
            return receipt(DispatchOutcome(**identity, decision='unavailable'), False, 'handler_not_registered',
                           ('No handler is registered; no dispatch was attempted',))
        try:
            raw = self._handler(event=event.model_copy(deep=True), scope=scope)
        except Exception:
            return receipt(DispatchOutcome(**identity, decision='error'), True, 'handler_error',
                           ('Outcome is uncertain after handler failure; reconcile the idempotency key before retrying',))
        try:
            outcome = DispatchOutcome.model_validate(raw.model_dump() if isinstance(raw, BaseModel) else raw)
        except (ValueError, TypeError):
            return receipt(DispatchOutcome(**identity, decision='error'), True, 'invalid_handler_result',
                           ('Invalid handler result; side effects are uncertain and no automatic retry is performed',))
        if any(getattr(outcome, key) != value for key, value in identity.items()):
            return receipt(DispatchOutcome(**identity, decision='error'), True, 'mismatched_handler_result',
                           ('Handler identity does not match the event; reconcile before retrying',))
        return receipt(outcome, True, 'handler_reported')
