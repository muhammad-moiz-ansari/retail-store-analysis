"""Opt-in, server-configured dashboard routes behind the existing trusted proxy."""
import hmac
import os
from pathlib import Path
import sqlite3

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import ValidationError

from .dashboard import DashboardConfig, DashboardRequest, dashboard_snapshot, public_request
from ..store_core import DEFAULT_DB_PATH

router = APIRouter(prefix='/analytics/dashboard', tags=['dashboard analytics'])


def access(x_retailpulse_internal_secret: str | None = Header(default=None),
           x_retailpulse_user_id: str | None = Header(default=None),
           x_retailpulse_email: str | None = Header(default=None),
           x_retailpulse_role: str | None = Header(default=None)):
    secret = os.getenv('RETAILPULSE_INTERNAL_SECRET', '')
    if not secret or secret == 'local-dev-pos-secret':
        raise HTTPException(503, 'Dashboard service authentication is not configured')
    if not hmac.compare_digest(x_retailpulse_internal_secret or '', secret):
        raise HTTPException(401, 'Unauthorized service request')
    if not x_retailpulse_user_id or not x_retailpulse_email or x_retailpulse_role != 'Manager':
        raise HTTPException(403, 'Active manager identity required')
    try:
        # Never call store_core.connect: dashboard reads must not initialize/seed app data.
        path = Path(os.getenv('RETAILPULSE_DB_PATH', str(DEFAULT_DB_PATH)))
        conn = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=3)
        try:
            conn.execute('PRAGMA query_only = ON')
            row = conn.execute('SELECT role, email, active FROM users WHERE id = ?', (x_retailpulse_user_id,)).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        raise HTTPException(503, 'Dashboard identity store unavailable') from None
    if not row or row[0] != 'Manager' or row[2] != 1 or row[1].casefold() != x_retailpulse_email.casefold():
        raise HTTPException(403, 'Active manager identity required')
    config_path = os.getenv('RETAILPULSE_ANALYTICS_CONFIG')
    try:
        if not config_path:
            raise ValueError('Not configured')
        path = Path(config_path)
        if path.stat().st_size > 262144:
            raise ValueError('Configuration too large')
        config = DashboardConfig.model_validate_json(path.read_text(encoding='utf-8'))
        if not config.event_db.is_absolute():
            config = config.model_copy(update={'event_db': (path.resolve().parent/config.event_db).resolve()})
    except (OSError, ValueError, ValidationError):
        raise HTTPException(503, 'Dashboard source configuration unavailable') from None
    membership = next((m for m in config.memberships if m.user_id == x_retailpulse_user_id), None)
    if membership is None:
        raise HTTPException(403, 'Dashboard membership required')
    return config, membership


@router.get('/context')
def context(response: Response, authorized=Depends(access)):
    config, membership = authorized
    response.headers['Cache-Control'] = 'no-store'
    return dict(request=public_request(membership.default_request), synthetic=config.synthetic)


@router.post('')
def snapshot(request: DashboardRequest, response: Response, authorized=Depends(access)):
    config, membership = authorized
    try:
        result = dashboard_snapshot(config, membership, request)
    except PermissionError:
        raise HTTPException(403, 'Selection outside dashboard membership') from None
    response.headers['Cache-Control'] = 'no-store'
    return result
