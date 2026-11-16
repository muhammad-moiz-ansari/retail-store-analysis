"""Anomaly evidence for an alert and the next-day staffing proposal, through the same manager access as the dashboard."""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.database import connect

from .advisory_api import router
from .test_dashboard import setup  # noqa: F401  (fixture)
from .test_read_tools import database, event, fingerprint, put  # noqa: F401  (fixtures and helpers)

STAMP = '2026-11-03T09:00:00+00:00'


@pytest.fixture
def advisory(setup):  # noqa: F811
    _, headers, _, dsn, *_ = setup
    with connect(dsn) as conn:
        conn.cursor().executemany("INSERT INTO zones(id, name, type, capacity, min_staff, created_at, updated_at) VALUES (%s, %s, 'floor', 10, %s, '', '')",
                                  [('z1', 'Floor', 1), ('z9', 'Elsewhere', 0)])
        conn.cursor().executemany("INSERT INTO orchestration_events(id, event_type, source, zone_id, title, created_at) VALUES (%s, 'unattended_customer', 'cv', %s, 't', %s)",
                                  [('e1', 'z1', STAMP), ('e9', 'z9', STAMP)])
        conn.cursor().executemany("INSERT INTO alerts(id, category, severity, title, context, evidence_json, created_at) VALUES (%s, 'Service', 'high', 't', 'c', %s, %s)",
                                  [('a1', json.dumps({'eventId': 'e1'}), STAMP), ('other-zone', json.dumps({'eventId': 'e9'}), STAMP),
                                   ('no-event', '{}', STAMP), ('broken', 'not json', STAMP)])
        conn.execute("INSERT INTO rosters(id, user_id, zone_id, shift, available, created_at, updated_at) VALUES ('r1', 'employee-1', 'z1', '9-5', 1, '', '')")
    app = FastAPI()
    app.include_router(router)
    return TestClient(app), headers, dsn


def test_alert_investigation_cites_scoped_evidence_and_hides_alerts_outside_the_membership(advisory, monkeypatch):
    client, headers, dsn = advisory
    put(dsn, 'queue_samples', [event('q-long', 30, queue_length=5, est_wait_s=None), event('q-short', 90, queue_length=1, est_wait_s=None)])
    put(dsn, 'zone_dwell', [event('d1', 0, 60, role='employee', track_id=1, dwell_s=60)])  # staffed 60 of 600 s: below 0.25
    before = fingerprint(dsn, ('alerts', 'pipeline_health', 'queue_samples', 'zone_dwell'))
    response = client.post('/agents/alerts/a1/investigate', headers=headers)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    data = response.json()
    found = {c['signal']: [i for e in c['evidence'] for i in e['ids']] for c in data['candidates']}
    assert set(found) == {'long_queue', 'low_staffed_coverage'} and found['long_queue'] == ['q-long']
    assert (data['zone_id'], data['synthetic'], data['unavailable_sources']) == ('z1', True, [])
    assert data['thresholds'] == dict(min_fps=.5, max_queue_length=3, min_staffed_ratio=.25)
    assert fingerprint(dsn, ('alerts', 'pipeline_health', 'queue_samples', 'zone_dwell')) == before

    # A covered lens is itself a candidate, and coverage for that window is then unknown rather than low.
    put(dsn, 'pipeline_health', [event('dark', 60, 120, fps=10, id_churn=0, frozen_or_dark=1)])
    blind = client.post('/agents/alerts/a1/investigate', headers=headers).json()
    assert {c['signal'] for c in blind['candidates']} == {'pipeline_issue', 'long_queue'} and blind['unavailable_sources'] == ['coverage']

    for hidden in ('other-zone', 'no-event', 'broken', 'missing'):
        assert client.post(f'/agents/alerts/{hidden}/investigate', headers=headers).status_code == 404
    assert client.post('/agents/alerts/a1/investigate', headers=headers | {'x-retailpulse-role': 'Employee'}).status_code == 403
    monkeypatch.setenv('RETAILPULSE_STORE_ID', 'store-2')
    assert client.post('/agents/alerts/a1/investigate', headers=headers).status_code == 403


def test_next_day_staffing_is_advisory_and_names_missing_inputs(advisory):
    client, headers, dsn = advisory
    quiet = client.get('/agents/staffing/next-day', headers=headers).json()
    zone, = quiet['zones']
    # An observed window with no entries is a forecast of zero, so only the zone's minimum staff is suggested.
    assert quiet['approval_required'] is True and (zone['suggested_staff'], zone['additional_staff'], zone['missing_inputs']) == (1, 0, [])

    put(dsn, 'footfall', [event(f'f{i}', i, direction='in', track_id=i) for i in range(25)])
    put(dsn, 'zone_dwell', [event('d1', 0, 300, role='employee', track_id=1, dwell_s=300)])
    before = fingerprint(dsn, ('rosters', 'tasks', 'footfall'))
    data = client.get('/agents/staffing/next-day', headers=headers).json()
    zone, = data['zones']
    # 25 entries at 10 customers per employee -> 3 staff; one is rostered available, so 2 more.
    assert (zone['zone_id'], zone['suggested_staff'], zone['additional_staff'], zone['missing_inputs']) == ('z1', 3, 2, [])
    assert zone['historical_staffed_ratio'] == .5 and {e['source'] for e in zone['evidence']} >= {'footfall'}
    assert data['customers_per_employee'] == 10 and data['store_id'] == 'store-1' and data['synthetic'] is True
    assert fingerprint(dsn, ('rosters', 'tasks', 'footfall')) == before

    put(dsn, 'pipeline_health', [event('dark', 60, 120, fps=10, id_churn=0, frozen_or_dark=1)])
    zone, = client.get('/agents/staffing/next-day', headers=headers).json()['zones']
    assert zone['suggested_staff'] is None and zone['missing_inputs']  # a blind minute: no number is invented
