#!/bin/sh
# Starts the RetailPulse API. One worker only: login lockout and the Ask request limit are kept in process memory.
set -eu
# Hosts without secret files can pass the operator analytics config (docs/fyp2-plan/DASHBOARD_BACKEND_SETUP.md) as JSON.
if [ -n "${RETAILPULSE_ANALYTICS_CONFIG_JSON:-}" ]; then
  umask 077
  printf '%s' "$RETAILPULSE_ANALYTICS_CONFIG_JSON" > /tmp/retailpulse-analytics.json
  export RETAILPULSE_ANALYTICS_CONFIG=/tmp/retailpulse-analytics.json
fi
# The registered store map (backend/events/spatial.py) can be passed the same way.
if [ -n "${RETAILPULSE_MAP_CONFIG_JSON:-}" ]; then
  umask 077
  printf '%s' "$RETAILPULSE_MAP_CONFIG_JSON" > /tmp/retailpulse-map.json
  export RETAILPULSE_MAP_CONFIG=/tmp/retailpulse-map.json
fi
exec python -m uvicorn backend.app:app --host 0.0.0.0 --port "${PORT:-8011}" --workers 1
