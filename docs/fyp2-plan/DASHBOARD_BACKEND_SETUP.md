# Configured dashboard backend

M-UI-P3 connects the dashboard provider to existing SQLite analytics tools. It does not generate CV data, implement Ruhab's business agents, register a map or expose the query graph/dispatch capability. The browser now starts in Configured backend mode. Synthetic fixture preview remains an explicit selection; a backend failure never selects it automatically.

## Server identity and configuration

The Next.js session proxy forwards the verified user ID, email and role after removing browser-supplied service/identity headers. The analytics backend independently requires the shared service credential, an existing active Manager row with matching ID/email, and server-owned membership. A role header or browser store ID alone grants no access. Legacy sessions without a user ID must sign in again. Membership is currently one configured store per manager; this is an adapter configuration, not a user/schema migration.

Set these variables in the appropriate server environments, then restart both services:

| Variable | Where | Meaning |
|---|---|---|
| POS_SESSION_SECRET (or NEXTAUTH_SECRET) | Next.js only | Explicit signed-cookie secret; the built-in local fallback is not accepted for analytics |
| RETAILPULSE_INTERNAL_SECRET | Both servers | Same explicit service credential; the built-in local fallback is not accepted for analytics |
| RETAILPULSE_SERVICE_URL | Next.js | Reachable Python backend URL; localhost only works when the backend runs on the same host |
| RETAILPULSE_DB_PATH | Python | Existing application users/settings SQLite DB, used for active-account checks |
| RETAILPULSE_ANALYTICS_CONFIG | Python | Path to the operator-owned JSON configuration below |

Use the actual session variable name above; POS_AUTH_SECRET is not read by the current session implementation. Next.js reads its normal environment configuration; the standalone Python backend needs exported variables too. No NEXT_PUBLIC secret or database path is needed. Existing application login/bootstrap behavior is unchanged. Dashboard reads never initialize either database. Keep machine-specific runtime configuration out of Git (local demo files can live under ignored data/outputs/).

Example **template**, requiring real identifiers/window/context from Saqib and the actual manager account ID. It is not installed or enabled automatically:

```json
{
  "version": 1,
  "event_db": "events.sqlite3",
  "synthetic": true,
  "memberships": [{
    "user_id": "replace-existing-manager-id",
    "store_id": "replace-store-id",
    "run_ids": ["replace-run-id"],
    "camera_ids": ["replace-camera-id"],
    "zone_ids": ["replace-region-id"],
    "default_request": {
      "storeId": "replace-store-id",
      "window": {"start": "2026-11-03T09:00:00Z", "end": "2026-11-03T10:00:00Z"},
      "filters": {"runId": "replace-run-id", "zoneId": "replace-region-id"}
    }
  }],
  "contexts": [{
    "context_id": "replace-verified-observation-context",
    "store_id": "replace-store-id",
    "zone_id": "replace-region-id",
    "camera_ids": ["replace-camera-id"],
    "available_sources": ["footfall", "zone_dwell", "interactions", "unattended_episodes"],
    "operating_windows": [{"start": "2026-11-03T09:00:00Z", "end": "2026-11-03T10:00:00Z"}]
  }]
}
```

event_db is absolute or relative to the JSON file's directory. Explicit nonempty run/camera/region allowlists are required; the default request must be inside them. A region ID is a stable location/scope identifier, not one of the four changing occupancy categories. No fixed-category/map schema is introduced. Duplicate manager memberships or duplicate store/region/shift contexts are rejected. Unknown configuration keys are rejected; file size is capped at 256 KiB.

`synthetic` must explicitly attest the provenance of **every allowed run**. Keep true for the canonical generated fixtures. Only set false for verified real event data; the database schema has no intrinsic synthetic marker, so the adapter cannot discover that claim. Do not mix synthetic and real runs under one provenance setting. Backend synthetic results retain mode=backend and synthetic=true, visibly distinct from hand-authored frontend preview scenarios.

Only declare feeds/cameras/windows actually verified by their owners. Missing context can be represented with `contexts: []`; missing operating windows should stay absent. The tools then retain unknown/partial values and unavailable denominators. A configuration declaration alone cannot prove healthy observation: pipeline_health rows and event sources still determine support. None of these settings claims a real store has been validated.

## API and data semantics

- GET `/analytics/dashboard/context`: authenticated manager's default request and synthetic marker only; no DB paths or other memberships.
- POST `/analytics/dashboard`: `{storeId, window: {start,end}, filters: {zoneId, runId?, cameraId?}}` and snapshot v1 from CONTRACTS.md. The frontend uses the same paths under `/api/backend/` with same-origin session cookies.
- Missing service credential returns 401; invalid/inactive/non-manager/unbound identity or unauthorized store/run/camera/region returns 403; invalid request shape/window returns 422; missing server authentication/configuration/identity store returns 503. Successful context/snapshot responses carry Cache-Control: no-store. Source DB failures return an all-null/partial snapshot rather than creating a database or fabricating zero.

The backend calls the five existing fixed read tools with the authorized scope. Footfall uses day buckets (at most 32 for a 31-day window), rejects incomplete/truncated bucket sums and defers totals when per-bucket evidence samples cannot be combined truthfully. Positive and observed-zero evidence, source limitations, estimate flags, status and matched/truncated counts are retained. Health evidence is allowed for observed-zero count results. Confirmed/unverified interactions remain separate; unattended derivation is still verdict-unfiltered and described as such. Coverage ratio stays unavailable without a healthy configured operating denominator.

The tools use separate read transactions; cross-tool atomicity is not promised while ingestion updates the file. Scope is identical across calls. Retrieval/cache timestamps are not camera freshness claims. The selected window is fixed by default_request, not a rolling live period; re-open backend mode after an operator changes the default. Refresh re-queries that selection and cache expiry is one minute. Stale historical observations must still be judged against the displayed window and source limitations. The proxy bounds analytics upstream requests to 30 seconds and forwards cancellation; existing non-analytics streams retain their prior timeout behavior.

## Continue and verify

Moiz's provider/API integration is implemented and tested with disposable accounts and existing synthetic event fixtures. Saqib supplies/adopts verified real user/store/run/camera/region/source context and reachable deployment; Ruhab supplies actual business outputs and acceptance/refinement. No real configuration, deployment or database migration was installed by this work. Ask, interaction detail rows, map layers, real dispatch and durable graph traces remain separate work.

Start the existing backend with the variables above and `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8011`, then the frontend with `npm run dev:frontend` from the repository root. Sign in with an existing Manager account and open `/dashboard`. Configured backend should display that manager's configured store/region/run/window and evidence. With no configuration, verify the unavailable message; choose Synthetic fixture preview only when intentionally demonstrating fixture states. Verify denied employee/unbound/cross-store requests and confirm real outputs against known event rows before claiming live acceptance.

Reproducible automated commands and measured outcomes are in PROGRESS.md. The canonical generator remains `python -m backend.events.fixtures --db <ignored-output-path>`; do not replace it or present its generated events as a real video run.
