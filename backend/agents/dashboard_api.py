"""Opt-in, server-configured dashboard routes behind the existing trusted proxy."""
import hmac
import os
from pathlib import Path
from psycopg import Error

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import ValidationError

from .dashboard import DashboardConfig, DashboardRequest, dashboard_snapshot, public_request
from ..database import DatabaseNotConfigured, read_only

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
        with read_only() as conn:
            row = conn.execute(
                'SELECT role, email, active FROM users WHERE id = %s', (x_retailpulse_user_id,)
            ).fetchone()
    except (Error, DatabaseNotConfigured):
        raise HTTPException(503, 'Dashboard identity store unavailable') from None
    if not row or row['role'] != 'Manager' or row['active'] != 1 or row['email'].casefold() != x_retailpulse_email.casefold():
        raise HTTPException(403, 'Active manager identity required')
    config_path = os.getenv('RETAILPULSE_ANALYTICS_CONFIG')
    try:
        if not config_path:
            raise ValueError('Not configured')
        path = Path(config_path)
        if path.stat().st_size > 262144:
            raise ValueError('Configuration too large')
        config = DashboardConfig.model_validate_json(path.read_text(encoding='utf-8'))
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
