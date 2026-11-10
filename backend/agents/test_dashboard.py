"""Offline HTTP identity/configuration and real-reader integration, no production data."""
import hashlib
import json
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from .dashboard import footfall_total
from .dashboard_api import router
from .test_read_tools import WINDOW, database, event, put
from .contracts import CountMetric, Evidence, FootfallBucket, FootfallResult


@pytest.fixture
def setup(database, tmp_path, monkeypatch):
    users = tmp_path/'users.sqlite3'
    conn = sqlite3.connect(users)
    conn.execute('CREATE TABLE users(id TEXT, role TEXT, email TEXT, active INTEGER)')
    conn.executemany('INSERT INTO users VALUES(?,?,?,?)', [
        ('manager-1', 'Manager', 'manager@test.invalid', 1), ('employee-1', 'Employee', 'employee@test.invalid', 1),
        ('inactive', 'Manager', 'inactive@test.invalid', 0), ('no-membership', 'Manager', 'unbound@test.invalid', 1)])
    conn.commit()
    conn.close()
    request = dict(storeId='store-1', window=WINDOW.model_dump(mode='json'), filters=dict(zoneId='z1'))
    config = dict(version=1, event_db=database.name, synthetic=True, memberships=[dict(
        user_id='manager-1', store_id='store-1', run_ids=['r1'], camera_ids=['c1'], zone_ids=['z1'], default_request=request)],
        contexts=[dict(context_id='test-observation', store_id='store-1', zone_id='z1', camera_ids=['c1'],
                       available_sources=['footfall', 'zone_dwell', 'interactions', 'unattended_episodes'],
                       operating_windows=[WINDOW.model_dump(mode='json')])])
    config_path = tmp_path/'analytics.json'
    config_path.write_text(json.dumps(config), encoding='utf-8')
    monkeypatch.setenv('RETAILPULSE_DB_PATH', str(users))
    monkeypatch.setenv('RETAILPULSE_ANALYTICS_CONFIG', str(config_path))
    monkeypatch.setenv('RETAILPULSE_INTERNAL_SECRET', 'isolated-test-secret')
    app = FastAPI()
    app.include_router(router)
    headers = {'x-retailpulse-internal-secret': 'isolated-test-secret', 'x-retailpulse-user-id': 'manager-1',
               'x-retailpulse-email': 'manager@test.invalid', 'x-retailpulse-role': 'Manager'}
    return TestClient(app), headers, request, database, users, config_path, config


def test_identity_cannot_be_overridden_by_browser_role_or_unknown_account(setup):
    client, headers, request, *_ = setup
    for changed, status in [({'x-retailpulse-internal-secret': 'wrong'}, 401),
        ({'x-retailpulse-user-id': ''}, 403), ({'x-retailpulse-role': 'Employee'}, 403),
        ({'x-retailpulse-user-id': 'employee-1', 'x-retailpulse-email': 'employee@test.invalid'}, 403),
        ({'x-retailpulse-user-id': 'inactive', 'x-retailpulse-email': 'inactive@test.invalid'}, 403),
        ({'x-retailpulse-user-id': 'missing'}, 403), ({'x-retailpulse-email': 'other@test.invalid'}, 403),
        ({'x-retailpulse-user-id': 'no-membership', 'x-retailpulse-email': 'unbound@test.invalid'}, 403)]:
        assert client.get('/analytics/dashboard/context', headers=headers | changed).status_code == status
        assert client.post('/analytics/dashboard', headers=headers | changed, json=request).status_code == status
    assert client.get('/analytics/dashboard/context').status_code == 401


def test_missing_config_identity_db_or_explicit_secret_is_unavailable_without_writes(setup, monkeypatch, tmp_path):
    client, headers, request, database, users, config_path, _ = setup
    before = users.read_bytes(), database.read_bytes()
    monkeypatch.delenv('RETAILPULSE_ANALYTICS_CONFIG')
    assert client.post('/analytics/dashboard', headers=headers, json=request).status_code == 503
    monkeypatch.setenv('RETAILPULSE_ANALYTICS_CONFIG', str(config_path))
    missing = tmp_path/'absent.sqlite3'
    monkeypatch.setenv('RETAILPULSE_DB_PATH', str(missing))
    assert client.get('/analytics/dashboard/context', headers=headers).status_code == 503
    assert not missing.exists()
    monkeypatch.delenv('RETAILPULSE_INTERNAL_SECRET')
    assert client.get('/analytics/dashboard/context', headers=headers).status_code == 503
    assert (users.read_bytes(), database.read_bytes()) == before


def test_authorized_context_exposes_selection_without_paths_or_other_memberships(setup):
    client, headers, request, *rest = setup
    response = client.get('/analytics/dashboard/context', headers=headers)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    data = response.json()
    assert data['request']['storeId'] == request['storeId'] and data['synthetic'] is True
    assert 'event_db' not in response.text and 'user_id' not in response.text


@pytest.mark.parametrize('mutation', [dict(storeId='store-2'), dict(filters={'zoneId':'z2'}),
    dict(filters={'zoneId':'z1', 'runId':'r2'}), dict(filters={'zoneId':'z1', 'cameraId':'c2'})])
def test_cross_store_run_camera_zone_queries_denied(setup, mutation):
    client, headers, request, *_ = setup
    assert client.post('/analytics/dashboard', headers=headers, json=request | mutation).status_code == 403


@pytest.mark.parametrize('mutation', [dict(path='private.db'), dict(scope={'role':'manager'}), dict(contexts=[]),
    dict(filters={}), dict(window={'start':'2026-11-03T09:00:00', 'end':'2026-11-03T10:00:00Z'})])
def test_injected_server_fields_or_invalid_selection_rejected(setup, mutation):
    client, headers, request, *_ = setup
    assert client.post('/analytics/dashboard', headers=headers, json=request | mutation).status_code == 422


def test_real_readers_map_hand_calculated_values_and_preserve_provenance_read_only(setup):
    client, headers, request, database, users, *_ = setup
    put(database, 'footfall', [event('f1', direction='in', track_id=1), event('outside', store_id='store-2', direction='in', track_id=2)])
    put(database, 'interactions', [event('i1', 10, 30, employee_track_id=1, customer_track_id=2, duration_s=20, verdict='interaction'),
                                 event('i2', 40, 60, employee_track_id=1, customer_track_id=3, duration_s=20, verdict='unverified')])
    put(database, 'zone_dwell', [event('d1', 0, 300, role='employee', track_id=1, dwell_s=300),
                               event('d2', 0, 200, role='customer', track_id=2, dwell_s=200)])
    put(database, 'unattended_episodes', [event('u1', 0, 400, customer_track_id=2, waited_s=400, helped=0)])
    before = tuple(hashlib.sha256(p.read_bytes()).hexdigest() for p in (database, users))
    response = client.post('/analytics/dashboard', headers=headers, json=request)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    data = response.json()
    assert data['provenance'] == dict(mode='backend', synthetic=True, label='Backend event analytics — synthetic source')
    assert {k: v['value'] for k, v in data['metrics'].items()} == dict(entries=1, exits=0,
        confirmedInteractions=1, unverifiedInteractions=1, meanConfirmedDuration=20,
        customerDwellP50=200, unattendedEpisodes=1, staffedOpenRatio=.5)
    assert 'outside' not in response.text
    assert data['metrics']['exits']['evidence'][0]['source'] == 'pipeline_health'
    assert data['metrics']['unattendedEpisodes']['status'] == 'partial'
    assert 'does not filter' in json.dumps(data['metrics']['unattendedEpisodes']['limitations']).lower()
    assert tuple(hashlib.sha256(p.read_bytes()).hexdigest() for p in (database, users)) == before


def test_missing_health_and_database_do_not_become_empty(setup):
    client, headers, request, database, _, config_path, config = setup
    with sqlite3.connect(database) as conn:
        conn.execute('DELETE FROM pipeline_health')
    response = client.post('/analytics/dashboard', headers=headers, json=request).json()
    assert response['metrics']['entries']['value'] is None
    assert response['metrics']['staffedOpenRatio']['value'] is None
    config['event_db'] = 'absent-events.sqlite3'
    config_path.write_text(json.dumps(config), encoding='utf-8')
    response = client.post('/analytics/dashboard', headers=headers, json=request).json()
    assert all(metric['value'] is None for metric in response['metrics'].values())
    assert not (config_path.parent/'absent-events.sqlite3').exists()


def test_invalid_or_ambiguous_config_fails_closed(setup):
    client, headers, _, _, _, config_path, config = setup
    config['memberships'] *= 2
    config_path.write_text(json.dumps(config), encoding='utf-8')
    assert client.get('/analytics/dashboard/context', headers=headers).status_code == 503
    config_path.write_text('{not-json', encoding='utf-8')
    assert client.get('/analytics/dashboard/context', headers=headers).status_code == 503


def test_footfall_never_presents_a_truncated_sum_as_complete():
    from .test_read_tools import scope
    observed = CountMetric(value=0, evidence=(Evidence(query='get_footfall', source='pipeline_health', ids=('h1',), matched_count=1),))
    result = FootfallResult(scope=scope(), window=WINDOW, status='partial', synthetic=True, truncated=True,
        limitations=('truncated',), buckets=(FootfallBucket(window=WINDOW,
            entries=observed, exits=observed),), occupancy=CountMetric(value=None, unavailable_reason='unknown'))
    assert footfall_total(result, 'entries').value is None
