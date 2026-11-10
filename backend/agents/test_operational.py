"""Fake handler checks only. No app/task writer or voice/provider is imported."""
from datetime import timedelta
import socket

import pytest
from pydantic import ValidationError

from .contracts import Evidence
from .operational import (DispatchOutcome, DispatchReceipt, OperationalDispatchAdapter,
                          OperationalEvent, TrustedOperationalScope)
from .test_read_tools import WINDOW, scope as manager_scope


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('Operational tests must run offline')
    monkeypatch.setattr(socket.socket, 'connect', denied)


def operational_scope(**kwargs):
    return TrustedOperationalScope(service_id='synthetic-producer', store_id='store-1', allowed_zone_ids=('z1',), **kwargs)


def payload():
    context = dict(storeId='store-1', zoneId='z1', window=WINDOW.model_dump(mode='json'), status='partial', synthetic=True)
    demand = Evidence(source='unattended_episodes', ids=('synthetic:wait:1',), query='get_unattended', matched_count=1)
    coverage = Evidence(source='pipeline_health', ids=('synthetic:health:1',), query='get_coverage', matched_count=1)
    return dict(eventId='synthetic-event-1', idempotencyKey='synthetic-idempotency-1', storeId='store-1', zoneId='z1',
        eventType='unattended_customer', source='customer_behavior', sourceTimestamp=WINDOW.end.isoformat(),
        window=WINDOW.model_dump(mode='json'), evidence=dict(demand=context | {'evidence':[demand.model_dump(mode='json')]},
        coverage=context | {'evidence':[coverage.model_dump(mode='json')]}))


def event():
    return OperationalEvent.model_validate(payload())


def outcome(event, decision='no_eligible_employee', **kwargs):
    return DispatchOutcome(event_id=event.event_id, idempotency_key=event.idempotency_key,
                           store_id=event.store_id, zone_id=event.zone_id, decision=decision, **kwargs)


def test_no_handler_does_not_dispatch_or_claim_a_task():
    result = OperationalDispatchAdapter().handle(event(), scope=operational_scope())
    assert result.decision == 'unavailable' and result.reason_code == 'handler_not_registered'
    assert not result.handler_invoked and result.task_id is None and result.synthetic


@pytest.mark.parametrize('decision', ['dispatched', 'no_eligible_employee', 'duplicate', 'unavailable', 'error'])
def test_fake_handler_outcomes_and_same_event_identity(decision):
    calls = []
    def fake(*, event, scope):
        calls.append((event, scope))
        assignment = dict(task_id='fake-task', selected_employee_id='fake-employee') if decision in ('dispatched','duplicate') else {}
        return outcome(event, decision, **assignment)
    result = OperationalDispatchAdapter(fake).handle(event(), scope=operational_scope())
    assert result.decision == decision and result.handler_invoked and len(calls) == 1
    assert result.event_id == 'synthetic-event-1' and result.idempotency_key == 'synthetic-idempotency-1'
    assert result.elapsed_ms >= 0 and result.reason_code == 'handler_reported'
    assert DispatchReceipt.model_validate_json(result.model_dump_json(by_alias=True)) == result


def test_repeated_events_forward_same_key_and_deduplication_belongs_to_handler():
    seen, keys = set(), []
    def fake(*, event, scope):
        keys.append((event.event_id, event.idempotency_key))
        decision = 'duplicate' if event.idempotency_key in seen else 'dispatched'
        seen.add(event.idempotency_key)
        return outcome(event, decision, task_id='fake-task', selected_employee_id='fake-employee')
    adapter = OperationalDispatchAdapter(fake)
    first = adapter.handle(event(), scope=operational_scope())
    second = adapter.handle(event(), scope=operational_scope())
    assert [first.decision, second.decision] == ['dispatched','duplicate']
    assert keys == [('synthetic-event-1','synthetic-idempotency-1')]*2
    assert len(keys) == 2  # Adapter adds no pretend durable idempotency cache.


def test_handler_error_is_sanitized_and_never_automatically_retried():
    calls = []
    def broken(**kwargs):
        calls.append(kwargs)
        raise RuntimeError('private-token-or-provider-error')
    result = OperationalDispatchAdapter(broken).handle(event(), scope=operational_scope())
    assert len(calls) == 1 and result.decision == 'error' and result.reason_code == 'handler_error'
    assert 'private-token' not in result.model_dump_json() and result.task_id is None
    assert any('uncertain' in note for note in result.limitations)


@pytest.mark.parametrize('field,value', [('storeId','store-2'),('zoneId','z2'),('source','employee_activity')])
def test_event_outside_trusted_scope_never_reaches_handler(field, value):
    body = payload(); body[field] = value
    if field in ('storeId','zoneId'):
        for signal in body['evidence'].values():
            signal[field] = value
    calls = []
    adapter = OperationalDispatchAdapter(lambda **kwargs:calls.append(kwargs))
    with pytest.raises(PermissionError):
        adapter.handle(OperationalEvent.model_validate(body), scope=operational_scope(allowed_sources=('customer_behavior',)))
    assert not calls


def test_manager_scope_is_not_an_operational_capability():
    with pytest.raises(PermissionError):
        OperationalDispatchAdapter().handle(event(), scope=manager_scope())


def test_updated_model_instances_cannot_bypass_evidence_scope_checks():
    original = event()
    wrong = original.evidence.demand.model_copy(update={'store_id':'store-2'})
    changed = original.model_copy(update={'evidence':original.evidence.model_copy(update={'demand':wrong})})
    with pytest.raises(ValidationError):
        OperationalDispatchAdapter().handle(changed, scope=operational_scope())


@pytest.mark.parametrize('mutation', ['missing_evidence','cross_store','cross_zone','different_window','mixed_synthetic','naive_time','early_time','bad_coverage','approval','auto_mode','schedule'])
def test_invalid_or_approval_payloads_fail_validation(mutation):
    body = payload()
    if mutation == 'missing_evidence': body['evidence']['coverage']['evidence'] = []
    elif mutation == 'cross_store': body['evidence']['demand']['storeId'] = 'store-2'
    elif mutation == 'cross_zone': body['evidence']['coverage']['zoneId'] = 'z2'
    elif mutation == 'different_window': body['evidence']['coverage']['window']['start'] = (WINDOW.start+timedelta(seconds=1)).isoformat()
    elif mutation == 'mixed_synthetic': body['evidence']['coverage']['synthetic'] = False
    elif mutation == 'naive_time': body['sourceTimestamp'] = '2026-11-03T10:00:00'
    elif mutation == 'early_time': body['sourceTimestamp'] = WINDOW.start.isoformat()
    elif mutation == 'bad_coverage': body['evidence']['coverage']['evidence'][0]['query'] = 'get_footfall'
    elif mutation == 'approval': body['managerApproved'] = True
    elif mutation == 'auto_mode': body['autoModeEnabled'] = True
    elif mutation == 'schedule': body['eventType'] = 'next_day_roster'
    with pytest.raises(ValidationError):
        OperationalEvent.model_validate(body)


@pytest.mark.parametrize('bad', ['missing_assignment','extra_fields','different_store','different_event','different_key'])
def test_invalid_callback_result_does_not_claim_assignment(bad):
    def fake(*, event, scope):
        result = outcome(event).model_dump()
        if bad == 'missing_assignment': result['decision'] = 'dispatched'
        elif bad == 'extra_fields': result['managerApproved'] = True
        elif bad == 'different_store': result['store_id'] = 'store-2'
        elif bad == 'different_event': result['event_id'] = 'other-event'
        elif bad == 'different_key': result['idempotency_key'] = 'other-key'
        return result
    result = OperationalDispatchAdapter(fake).handle(event(), scope=operational_scope())
    assert result.decision == 'error' and result.task_id is None
    assert result.event_id == 'synthetic-event-1' and result.idempotency_key == 'synthetic-idempotency-1'
    assert result.reason_code in ('invalid_handler_result','mismatched_handler_result')


def test_timestamp_aliases_utc_and_outcome_pairs():
    body = payload()
    body['sourceTimestamp'] = (WINDOW.end+timedelta(hours=5)).replace(tzinfo=None).isoformat()+'+05:00'
    parsed = OperationalEvent.model_validate(body)
    assert parsed.source_timestamp == WINDOW.end
    assert parsed.model_dump(mode='json',by_alias=True)['eventId'] == 'synthetic-event-1'
    with pytest.raises(ValidationError):
        outcome(parsed, 'no_eligible_employee', task_id='not-a-task')
