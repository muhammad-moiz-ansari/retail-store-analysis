# Data Contracts

## Current decision — 11 November 2026

The [combined team plan](RetailPulse_FYP2_Implementation_Plan.md) governs current work and ownership. Implement camera/CV first, then register the supplied map, then render live role occupancy and confirmed-interaction layers. Exactly four dynamic occupancy categories are allowed: **Customer, Employee, Customer–employee both, No one**. They are not fixed permitted-role polygons. Invalid/missing/unknown observation is separate quality metadata, never a fifth category or a false No one. Historical z1–z6, staff zones, queue/counter geometries and hot/gray terminology below are legacy technical references, not additional category requirements. No existing runtime/schema/fixture has been migrated by this documentation update.

## Dashboard presentation provider — M-UI-P1 (Moiz)

Implemented in `frontend/src/lib/analytics-provider/{contracts,provider,fixture}.ts`. This is a frontend-facing adapter boundary, not a replacement event schema, HTTP API, auth policy or business agent. M-UI-P2 now consumes it through `frontend/src/components/dashboard/DashboardAnalytics.tsx` on `/dashboard`; comparison-derived legacy analytics are no longer imported by that page.

`AnalyticsProvider` declares `mode: fixture | backend` and async `load(request, signal?) -> unknown`. `loadDashboard` validates the response before returning a typed state. Request fields are `storeId`, `window: {start,end}` and `filters: {runId?,cameraId?,zoneId?}`. Times use UTC ISO strings ending in Z; the half-open observation window is positive and at most 31 days. Requests describe desired scope, not authority. The future server adapter must derive permissions from authenticated records and preserve backend tool limits and trusted observation context. Never accept browser store IDs as authorization.

Snapshot v1 echoes the exact store/window/filter selection, provenance (`mode`, explicit `synthetic`, visible `label`), retrieval/cache timestamps (`generatedAt`, `validUntil`), limitations and all eight metric keys. Cache freshness is separate from the historical observation window; an old observation window is not automatically stale. `snapshotState` can re-evaluate expiry without re-fetching. The consumer owns initial `loading`, refresh lifecycle and cancellation. After expiry a usable snapshot is `stale`; all-unavailable data remains `unavailable`; otherwise missing/partial metrics make the snapshot `partial`, with fully supported/observed-empty snapshots `ready`. Individual metric statuses remain visible even when the overall status is stale.

| Presentation key | Unit | Existing tool source |
|---|---|---|
| entries / exits | count | get_footfall bucket entries/exits; later adapter must handle bucket truncation, not sum partial buckets as complete totals |
| confirmedInteractions / unverifiedInteractions | count | get_interactions confirmed_count / unverified_count, kept separate |
| meanConfirmedDuration | seconds | get_interactions mean_confirmed_duration, not a fabricated response/approach time |
| customerDwellP50 | seconds | get_zone_dwell customer p50; explicit zone required by backend |
| unattendedEpisodes | count | get_unattended episode_count; preserve stored_derivation_verdict_unfiltered limitation |
| staffedOpenRatio | ratio | get_coverage selected zone staffed_open_ratio; null without trusted operating denominator |

Each metric has nullable numeric `value`, `unit`, `status: ok | empty | partial | unavailable`, nullable `reason`, `estimated`, `limitations` and evidence entries (`query`, `source`, `ids`, `matchedCount`, `truncated`). The adapter must retain metric-specific unavailable reasons/estimates and source-result limitations, not upgrade partial tool outputs. Positive values require evidence; observed zero may have no row IDs, but needs the backend's actual observation/health justification. Undefined averages/ratios remain null even in an observed-empty window. Unavailable metrics cannot contain numbers. Non-finite/negative values, fractional counts, ratios outside 0–1, missing explanations and invalid evidence are rejected. No occupancy/net-inside claim is derived by subtracting crossings; initial occupancy is not established.

Evidence tool/table pairs mirror existing sources (footfall; interactions/tracks; zone_dwell; unattended_episodes; zone_dwell/pipeline_health). Sampled evidence must retain matched count and truncation; evidence IDs alone are not a complete population. Shape checks cannot establish row authenticity, healthy observation or authorization. Those remain server responsibilities. Unsupported/malformed/cross-scope responses or provider exceptions return sanitized all-null unavailable results, never fixture fallback or backend exception text. Cancellation rejects for the UI to discard, rather than becoming an outage notice.

`createFixtureProvider(scenario, now?)` supports ready, empty, partial, unavailable and stale scenarios. These are **hand-authored synthetic presentation scenarios**, separate from Saqib's canonical SQLite generator and not derived from CV data. They accept only `fixtureRequest` (demo-store, demo-region, 3 Nov 2026 09:00–10:00 UTC, no camera/run filters); unsupported valid selections return unavailable rather than relabel fixed numbers. Fixture IDs and numbers are illustrative, not real evidence. This fixture provider performs no database/network access. M-UI-P3 adds a separate backend provider below. No interaction rows, map registration, occupancy category assignment or heatmap data are invented by this boundary.

Provider example (local fixture preview only):

```ts
import { createFixtureProvider, fixtureRequest } from "@/lib/analytics-provider/fixture";
import { loadDashboard } from "@/lib/analytics-provider/provider";
const controller = new AbortController();
const state = await loadDashboard(createFixtureProvider("partial"), fixtureRequest, {
  signal: controller.signal,
});
// Render state.snapshot.provenance.label, metric units/reasons/limitations and status.
// Re-evaluate cache expiry with snapshotState; abort/discard obsolete requests.
```

Offline verification: `npm run test:dashboard-provider` compiles these TypeScript modules/tests with installed TypeScript, then runs Node's test runner; generated JS stays under ignored `data/outputs/dashboard-provider-tests/`. No new dependency or model/provider call is required.

### Dashboard component binding — M-UI-P2 (Moiz)

`DashboardPreview` explicitly selects the fixture provider and fixed `fixtureRequest`; the labelled scenario selector offers Ready, Observed empty, Partial data, Unavailable and Stale data. It is a preview control, not live store configuration or a dataset selector. Backend failures never activate this preview automatically. At the Phase 2 checkpoint the dashboard defaulted to this preview; M-UI-P3 now defaults to Configured backend and keeps preview as an explicit choice.

`DashboardAnalytics({provider, request})` is the reusable binding seam for the later authenticated backend provider. `AnalyticsView({state})` displays all eight aggregate metrics with units, individual status, missing reasons, estimates, expandable evidence/limitations, matched-count/truncation details, source window and retrieval/cache timestamps. Observed empty counts show 0; undefined averages/ratios and unavailable metrics display Unavailable. Stale snapshots retain their per-metric quality and warn that cached values expired. No Net inside, employee/account identities, fake response times, peak/density claims or decorative heatmap blobs are derived from comparison JSON.

`DashboardController` in the provider package owns loading/refresh, abort signals and a revision guard that discards superseded results even when a provider ignores cancellation. Stop cancels pending loads and expiry timers on selection changes/unmount. It schedules a single cache-expiry transition using validUntil and re-checks the clock; no polling, silent fixture fallback or live backend calls are introduced. React consumes the controller using useSyncExternalStore, with a stable server loading snapshot and effect cleanup compatible with development effect replay. Controllers change when provider/request identity changes; parent code should keep these objects stable unless the selection changes.

The existing backend system-status request remains separate from the preview. The camera section marks the local sample as a recorded clip and other feeds as not connected, without REC/live labels. Recent interaction rows and map/heatmap layers show explicit unavailable notices because the provider contract contains neither. Ask is disabled with an explanation until authenticated service integration. Existing global auth/role guards are unchanged; frontend payload validation does not establish backend authorization. The old dashboard-data.js and comparison-page functionality are retained outside the dashboard; legacy tests are not evidence of correct live analytics.

At the Phase 2 checkpoint the command ran 27 checks: 16 provider tests, five controller lifecycle/race/expiry tests and six React rendering tests. Phase 3 extends the same command to 34 checks below. Rendering checks are server/static component tests; browser interaction results and limitations are recorded separately in PROGRESS.md. No new test dependency is installed.

### Configured backend provider — M-UI-P3 (Moiz)

`backend/agents/dashboard.py` adapts the existing fixed tools to snapshot v1. `dashboard_api.py` supplies config-gated GET `/analytics/dashboard/context` and POST `/analytics/dashboard`, included by backend/app.py. It checks an explicit non-default shared service secret, active Manager ID/email in a read-only application DB connection and server-owned run/camera/region/store membership before reading events. No browser-controlled scope, source path, observation context or arbitrary tool name is accepted. Existing user/event schemas and business/operational writers are unchanged. Configuration and exact enablement steps are in [DASHBOARD_BACKEND_SETUP.md](DASHBOARD_BACKEND_SETUP.md).

`createBackendProvider` uses the same-origin session proxy and passes the result through the existing snapshot validator. `loadBackendSelection` obtains the server's default selection. DashboardDataSource defaults to backend; unavailable selection/auth/source errors do not select fixtures. Operator-configured synthetic backend events retain backend mode and a synthetic-source banner. The reusable view displays run/camera selection as well as store/region/window. Missing/incomplete source data stays null/partial. Retrieval TTL does not assert camera freshness, and the fixed observation window does not roll automatically.

The proxy strips all incoming x-retailpulse identity/service headers and overwrites from the verified session, including removal of injected user IDs for legacy sessions. Analytics requires an explicit session secret and a session Manager user ID; Python independently rechecks the account and membership. Signed sessions now reject missing/invalid/expired exp, malformed identity fields and extra token parts. These changes are bounded integration hardening, not a new authentication system. The internal credential remains the trusted server-to-server boundary and must stay server-side.

Evidence sources now accept pipeline_health for observed-zero counts from all five existing tools; the Phase 1 validator had omitted these legitimate source pairs. Footfall aggregates only complete unsampled buckets and otherwise returns unavailable totals; no truncated sum is promoted to a complete count. Tool result limitations/partialness and independent evidence truncation remain visible. Five tools use independent read snapshots, so concurrent ingestion can change between them. Query graph HTTP routes, durable traces, agent policy, live map and dispatch are not included.

Current frontend test command runs 34 provider/transport/header/session/lifecycle/render checks; backend adapter/HTTP tests join the existing regression suite. See PROGRESS.md for actual results and synthetic browser-login integration evidence, distinct from real-feed/deployment acceptance.

## What the pipeline writes today

`python -m backend.interaction.cli <video> --output backend/output/<run>/interaction.mp4`
writes these files next to the video:

| File | Shape |
|---|---|
| `interaction.detections.json` | `[{frame, timestamp, interaction_active, people: [{track_id, bbox:[x1,y1,x2,y2], center:[x,y], confidence, role, role_confidence, role_evidence}]}]` |
| `interaction.interactions.json` | confirmed events: `[{employee_track_id, customer_track_id, started_at, last_seen_at, start_time, verdict, ...}]` |
| `interaction.rejected_interactions.json` | same shape, events the pose judge rejected (only written with `--judge pose`) |
| `interaction.people.json` | `{weights, threshold, people: [{track_id, first_seen, last_seen, frames_observed, role, employee_score, factors, contributions, role_segments}]}` |

All coordinates are pixels of the source frame; times are seconds from the clip start.

## New: `interaction.summary.json` (Step 1)

Written by the CLI after the files above, computed by `backend/interaction/analytics.py`
from those same files only.

```json
{
  "run": "ShopAssistant1cor",
  "duration_s": 120.0,
  "footfall": {"in": 14, "out": 11},
  "people": {"customers": 17, "employees": 3},
  "interactions": {"count": 6, "mean_duration_s": 18.4, "mean_approach_s": 9.2},
  "unattended": [{"customer_track_id": 7, "from": 31.0, "to": 95.0, "waited_s": 64.0}],
  "employee_idle": [{"employee_track_id": 2, "idle_s": 40.5, "share": 0.34}],
  "zone_dwell": [{"zone": "staff_zone_0", "customer_s": 120.0, "employee_s": 310.0}],
  "heatmap": {"cols": 32, "rows": 18, "frame": [1280, 720], "counts": [[0, 1, 0]]}
}
```

Definitions:

- **footfall**: a track's `center` crossing the configured entrance line; direction from the sign change.
- **approach time**: customer `first_seen` → `started_at` of that customer's first confirmed interaction.
- **unattended**: a customer present longer than `unattended_after_s` with no confirmed interaction in that window.
- **employee idle**: employee time with no confirmed interaction and centre movement below `idle_move_px` over `idle_window_s`.
- **zone dwell**: seconds the track centres spend inside each zone rectangle (same frame-coordinate
  rectangles as `InteractionConfig.staff_zones`; store zones in SQLite have no geometry).
- **heatmap**: 2D histogram of all `center` points (`numpy.histogram2d`).

New config fields on `InteractionConfig` (defaults in brackets): `entrance_line` [None, footfall skipped],
`unattended_after_s` [60], `idle_window_s` [30], `idle_move_px` [40], `heatmap_grid` [(32, 18)].

## New API (Step 2)

`GET /analytics/runs` (manager): `[{"run": "<name>", "duration_s": ..., "created_at": ...}]`
from every `*.summary.json` under `backend/output/` (recorded runs go to `--output`, live runs to
`backend/output/live-<time>.*`). `run` is the path relative to `backend/output/` without `.summary.json`.

`GET /analytics/summary?run=<name>` (manager): that run's summary JSON; latest run when `run` is omitted.
404 when no summary exists. `run` must match an entry from `/analytics/runs` exactly (no path traversal).

Both are reached from the frontend through the existing `/api/backend/[...path]` proxy.

## New alerts (Step 3)

One row in the existing `alerts` table per unattended event:

| column | value |
|---|---|
| `category` | `unattended_customer` |
| `severity` | `high` if `waited_s` ≥ 2 × `unattended_after_s`, else `medium` |
| `title` | `Customer waited 64 s without assistance` |
| `context` | run name + time window |
| `source` | `vision` |
| `evidence_json` | the unattended entry plus the run name |
| `id` | `vision:<run>:<customer_track_id>:<from>` so re-importing a run does not duplicate alerts |

## Event schema v1 (shared contract 1)

`backend/events/schema.sql`: eight tables (`tracks`, `role_decisions`, `interactions`, `zone_dwell`, `footfall`,
`queue_samples`, `unattended_episodes`, `pipeline_health`). Every row has `event_id` (stable, `<run>:<kind>:<camera>:<key>`),
`run_id`, `store_id`, `camera_id`, `zone_id`, `ts_start`, `ts_end` (UTC ISO 8601; instants have `ts_end = ts_start`).
Zone and camera ids are the ones seeded in `store_core.py` (`z1`–`z6`, `c1`–`c3`). Indexed on `(store_id, zone_id, ts_start)`.

- **Ingest a CV run** (idempotent on `run_id`):
  `python -m backend.events.ingest backend/output/run1/interaction --run-id run1 --camera c2 --zone z2 --start 2026-11-03T09:00:00+00:00`
  (default DB `backend/events.sqlite3`, or `EVENTS_DB_PATH`).
- **Straight from the CLI**: add `--camera c2` (zone from the camera settings, or `--zone`), optionally `--start <UTC ISO>`
  (default: when processing starts, which is right for live runs) and `--run-id`. `POST /interaction/runs` and
  `POST /interaction/live` take an optional `"camera": "c2"` and pass it on.
- **unattended_episodes** is derived, not detected: a customer whose wait from first sighting to their first confirmed
  interaction (or exit) is ≥ N s, N = settings `thresholds.unattendedWaitMinutes` × 60. `helped` says which ended it.
- **Fixture day** for tools/agents/UI: `python -m backend.events.fixtures` → `backend/events/fixture.sqlite3`
  (seeded, identical every run; not committed since `*.sqlite3` is ignored). 09:00–21:00 UTC, planted patterns:
  17:00–19:00 rush, understaffed `z3`, camera `c2` blocked 14:00–14:40 (`pipeline_health.frozen_or_dark = 1`).
- **Zones and dwell (B4.2)**: the camera's `--config` JSON may hold `floor_zones` (normalised polygons keyed by store
  `zone_id`), `zone_hold_seconds` (1.0) and `heatmap_grid` ([32, 18]). A track's foot point picks its zone (outside every
  polygon = the camera's zone); `zone_dwell` has one row per visit, ordered visits of a track are its zone transitions,
  `tracks.zone_id` is the zone it spent longest in and `interactions.zone_id` is the customer's zone at the start.
- **heatmaps** (additive to v1): one row per camera per wall-clock hour, `cells` = JSON `rows` x `cols` foot-point counts.
- **footfall (B4.3)**: entrance camera config sets `entrance_line` (normalised x of a vertical line) and
  `entrance_in_direction` ("right"/"left"). A track that ends on the other side from where it started is one row at
  its last crossing time (net, so jitter on the line counts once; walking in and back out within one track counts 0).
- **queue_samples (B4.4)**: counter camera config sets `queue_zone` (normalised polygon) and `queue_sample_seconds` (5).
  Every sample counts customers (not staff, not unknown) whose feet are in the polygon; `est_wait_s` = length x the
  run's mean interaction duration (NULL when the run has no interactions).
- **pipeline_health.frozen_or_dark (B4.5)**: the CLI flags each processed frame (`frozen_or_dark` in detections.json):
  mean grey < `dark_brightness` (20), or the picture unchanged (< `frozen_change`) for `frozen_seconds` (2 s). The minute
  is 1 when most of its frames are flagged; NULL for runs recorded before the check existed.
- **Contract test**: `backend/events/test_events.py` checks the fixture and every local CV run under `backend/output/`
  with `ingest.validate`.

## Agent read-tool contracts — Moiz Phase 1 (2026-11-10)

**Implemented:** typed inputs/results in `backend/agents/contracts.py` and the five-method `AnalyticsTools` Protocol in `backend/agents/tools/__init__.py`. **Not implemented in Phase 1:** SQL readers, tool registry, graph execution, HTTP routes or authentication adapters. The older summary/API sections above remain design records; their presence is not implementation evidence. Saqib's `backend/events/schema.sql` is the canonical store contract and is unchanged.

### Callable boundary for Ruhab and the next implementation phase

All methods are keyword-only on an injected `AnalyticsTools` implementation:

| Method | Request | Result | Event sources / availability |
|---|---|---|---|
| `get_footfall(*, scope, request)` | `FootfallRequest(window, filters={}, limit=100, granularity="hour")` | `FootfallResult`: buckets with entries/exits; nullable occupancy | `footfall`, supporting `pipeline_health`; stored net crossings, not all entrance crossings. Initial occupancy/entrance coverage currently absent. |
| `get_zone_dwell(*, scope, request)` | `ZoneDwellRequest(window, filters={"zone_id":"z3"}, limit=100)` | `ZoneDwellResult`: by-role sample count, total, p50, p90 | `zone_dwell`; customer/employee/unknown kept separate; usable zone geometry remains camera-specific. |
| `get_interactions(*, scope, request)` | `InteractionsRequest(window, filters={}, limit=100)` | `InteractionsResult`: confirmed/unverified counts, confirmed mean duration, mean approach and approach sample count | `interactions` plus `tracks`; confirmed means `verdict=interaction`. Approach reference is explicitly `camera_first_seen`, not entrance/zone entry. |
| `get_unattended(*, scope, request)` | `UnattendedRequest(window, filters={}, limit=100, min_seconds=180)` | `UnattendedResult`: episode count and clipped episodes with helped/provenance | `unattended_episodes`; current writer's first-help derivation does **not** filter interaction verdict. These are stored derived waits, not verified absence of assistance. Saqib owns correction/validation. |
| `get_coverage(*, scope, request)` | `CoverageRequest(window, filters={}, limit=100, shift=None)` | `CoverageResult`: per-zone observed staffed/unknown seconds, nullable open seconds and staffed/open ratio | Employee `zone_dwell` plus `pipeline_health`; a trusted operating/shift context is not yet supplied. No open-hours or roster-availability ratio can be inferred from the fixture's 12-hour span. |

`scope: TrustedAccessScope` is supplied separately by the trusted server, never included in the model/tool argument payload. It carries actor ID, store ID, role, and optional run/camera/zone allowlists. `None` means no additional restriction **within that store**; a supplied allowlist must be nonempty. Request filters can only narrow access. When omitted, they do not remove scope restrictions. `scope.validate_filters(request.filters)` rejects explicit disallowed filters, but does not implement authentication or database isolation. Phase 2 readers must apply store and allowlists to every query; Phase 3 must bind them to real authenticated identity before any public endpoint. Existing role/internal-secret headers alone are not a proven multi-store policy.

Example typed input construction (the concrete Phase 2 reader is shown below):

```python
from backend.agents.contracts import FootfallRequest, TrustedAccessScope
from backend.agents.tools import AnalyticsTools

scope = TrustedAccessScope(actor_id="manager-1", store_id="store-1", role="manager",
                           allowed_camera_ids=("c1",))  # trusted server creates this
request = FootfallRequest(window={"start": "2026-11-03T14:00:00+05:00",
                                  "end": "2026-11-03T16:00:00+05:00"},
                          filters={"camera_id": "c1"}, granularity="hour")
scope.validate_filters(request.filters)
# tools: AnalyticsTools = <server-injected SQLiteAnalyticsTools reader, shown below>
# result = tools.get_footfall(scope=scope, request=request)
```

### Time, aggregation and bounds

- Aware ISO timestamps/datetimes normalize to UTC. Naive dates/times and numeric epochs are rejected. Require `start < end`, at most 31 days. DST ambiguity must be resolved by an explicit input offset.
- Instant events belong to `[start,end)`: include an instant at start and exclude one at end. Intervals overlap when `ts_start < end` and `ts_end > start`; clip to `[max(ts_start,start), min(ts_end,end)]`. Ignore zero-length clipped intervals. These are the agreed reader conventions, not claims that Phase 1 executes queries.
- Buckets align to UTC minute/hour/day boundaries and clip at the requested edges. At most 1000 buckets; choose a coarser granularity rather than silently returning an enormous series. Row `limit` is a strict integer 1–1000 (default 100). Phase 2 must use deterministic time/event-ID ordering and set result `truncated` when rows are omitted.
- Footfall counts stored instant events. Dwell samples are positive clipped visits, not deduplicated people: report sample count and role; p50/p90 use sorted linear interpolation at `(n-1)*p`, singleton returns itself, no samples means null. Durations use clipped intervals rather than an entire stored duration extending outside the window. Interaction counts include each overlapping event once; aggregate durations use confirmed rows only. Unverified rows remain separate. Approach uses a valid scoped customer-track match and its first confirmed interaction; require nonnegative supported elapsed time and disclose the sample count. A supplied time window bounds interaction selection, while first-seen reference may precede it.
- Track joins require `(store_id, run_id, camera_id, track_id)`, never `track_id` alone. A CV employee track is not an employee account or proof of roster availability.
- `get_unattended` selects stored episodes by overlap and `stored waited_s >= min_seconds`; it does not rederive waits. Returned episode `window` and `waited` describe the clipped wait within the request, which may be shorter than the selection threshold. Retain stored-event evidence and the unfiltered-verdict provenance; the UI must not infer a newly confirmed event from the clipped duration.
- Coverage is the clipped **union** of employee presence per zone, not employee-seconds. Merge overlapping staff intervals. Blocked/missing/unhealthy observation is unknown, not zero staff. Apply trusted operating windows before computing any open-hours denominator; shift is only a lookup key, not caller-supplied authorization or a denominator.

### Result status, units and evidence

All five results carry tool name, echoed trusted scope/window/filters, `status`, mandatory `synthetic`, limitations and result-row `truncated`. `ok` means the requested supported metrics are observed; `empty` means no matching event rows, **not proven zero activity**; `unavailable` means unsupported/missing sources or context; `partial` means incomplete observation/data. Partial/unavailable require limitations. Unavailable results cannot contain numeric metrics. A missing table is unavailable, never silently empty.

Each numeric field is a typed metric `{value, unit, evidence, unavailable_reason, estimated}`. Counts are integral/nonnegative; seconds nonnegative; ratios in [0,1]. Count/seconds/ratio fields reject the wrong unit. Missing values are `null` with a reason, not zero. A numeric zero also requires supporting observation evidence. Grounding of a number against actual rows is a later-phase responsibility; these models enforce shape, ranges and association only.

Evidence extends the shared shape `{source: table, ids: [...], query: name}` with `matched_count` and `truncated`. Source tables and the five query names are fixed Literals. IDs must be unique, nonempty, at most 200 per citation. `matched_count` records the full supporting row count; evidence `truncated=true` iff not all IDs are returned. Metrics cite their own supporting rows, including health rows for a defensible observed zero; a global bag of unrelated IDs is insufficient. A result rejects evidence citing another tool name. Aggregates are computed before result/evidence caps in Phase 2; sampled evidence must not change the answer. Result-row and evidence truncation are separate.

Schema-only synthetic example result, validated in the contract tests; **not output from an implemented reader**:

```json
{
  "scope": {"actor_id": "manager-1", "store_id": "store-1", "role": "manager"},
  "window": {"start": "2026-11-03T09:00:00Z", "end": "2026-11-03T10:00:00Z"},
  "status": "partial",
  "synthetic": true,
  "limitations": ["Illustrative stored crossing; complete observation and initial occupancy are unknown"],
  "buckets": [{
    "window": {"start": "2026-11-03T09:00:00Z", "end": "2026-11-03T10:00:00Z"},
    "entries": {"value": 1, "unit": "count", "evidence": [{"source": "footfall", "ids": ["synthetic:in:1"], "query": "get_footfall", "matched_count": 1, "truncated": false}]},
    "exits": {"value": null, "unit": "count", "unavailable_reason": "No supported observation evidence"}
  }],
  "occupancy": {"value": null, "unit": "count", "unavailable_reason": "Initial occupancy unknown"}
}
```

Fixture replay from the repository root, explicitly targeting an ignored disposable location:

```powershell
New-Item -ItemType Directory -Force data/outputs/moiz-phase1 | Out-Null
.venv/Scripts/python.exe -m backend.events.fixtures --db data/outputs/moiz-phase1/fixture.sqlite3
```

This reuses Saqib's seeded `fixture-2026-11-03` / `store-1`, 09:00–21:00 UTC (rush 17:00–19:00, under-covered z3, blocked c2 14:00–14:40). Every consumer result must set `synthetic=true` for this store file; the schema itself has no synthetic column. A second-store collision case exists only in the new tests and does not replace his generator. Heatmaps remain image-grid counts; queue waits remain heuristics (length × mean interaction duration). No metric floor calibration, new CV models, account linkage, operating-hours policy or dispatch capability is introduced here.

Follow-on interfaces (`get_queue`, `get_alerts`, `get_pipeline_health`, legacy `get_pos_sales`) are not part of this five-tool Phase 1 publication; their signatures/readers remain pending scope/data decisions. POS is outside the agreed project scope; the legacy name is not a commitment to build POS analytics. Arbitrary `run_readonly_sql` is deferred. No production migrations or writing connection are introduced; Phase 2 must use SQLite `mode=ro`, parameterized queries, fixed source names, and must not call `backend.events.ingest.connect`, which executes DDL.

## Executable event readers (Moiz Phase 2)

`backend.agents.tools.analytics.EventAnalytics(path, synthetic=..., contexts=...)` now implements `get_footfall`, `get_zone_dwell` and `get_interactions` against the existing SQLite event schema. Inputs/results reuse the Phase 1 types above. The SQLiteAnalyticsTools subclass adds unattended/coverage readers, and ScopedToolRegistry integrates all five below. Phase 1's SQL-free description is historical.

`backend.agents.tools.common.ObservationContext` is a trusted server-injected declaration of expected cameras per store/zone, with a context ID and optional shift/operating-window metadata. No request argument may redefine that declaration. Without expected-camera configuration and healthy observation over the full relevant interval, missing event counts return null instead of a proven zero. Health is camera-wide; its stored home-zone ID need not equal a mapped aisle zone, so only this validated camera mapping permits camera-wide health evidence. Camera/run allowlists and the store boundary still apply.

The reader opens SQLite with URI `mode=ro`, `query_only=ON`, and a per-call snapshot; it never invokes the schema-initializing writer. Each source has a 100000-row safety budget; exceeding it returns unavailable rather than an inaccurate capped aggregate. Event selection uses an inclusive broad SQL time prefilter and exact timezone-aware Python boundaries, preserving sub-millisecond events. Result/evidence caps apply after aggregation. Aggregate-only interaction results are unaffected by the request row limit.

### Contextual readers and trusted operating context

`backend.agents.tools.contextual.SQLiteAnalyticsTools` extends `EventAnalytics` with `get_unattended` and `get_coverage`, completing the five callable implementations. It does not dispatch tasks or implement Ruhab's business agents.

`ObservationContext.available_sources` must explicitly list enabled feeds among `footfall`, `zone_dwell`, `interactions`, `unattended_episodes`; its default is empty. Health alone does not prove a missing writer was enabled. The expected cameras and source declaration must cover the selected query scope, otherwise counts without rows remain null. This is trusted server/configuration input, not a manager/LLM-supplied declaration.

Unattended rows use stored `waited_s >= min_seconds` and overlap selection. The returned episode window/waited metric is clipped; the count and its evidence include all matching rows before the result limit. `helped` and `stored_derivation_verdict_unfiltered` expose the current writer limitation. Results are partial even with healthy feeds because these derived waits are not verified absence of assistance.

Coverage merges employee-presence intervals and intersects them with the union of healthy intervals for **every expected camera**. A blocked/unknown-health record overrides an overlapping healthy record for that camera; run/camera allowlists remain enforced. The conservative policy does not treat one surviving camera as proof that a zone is fully observed. Without context or supporting health records, observation metrics stay null; with partial supported health, unknown time is the uncovered evaluated interval. Zero observed staffed seconds alongside a fully unknown interval is not a claim of zero employees.

Optional server-injected `operating_windows` are merged and clipped to the request. When supplied, coverage metrics evaluate those windows; otherwise they evaluate the whole request and open-hours/ratio stay null. A requested shift must match a configured store/zone context; there is no fallback to the request window. Each `CoverageSummary` echoes `operating_context_id`, `operating_windows` and `evaluated_windows`. Health/dwell event citations ground observations; the separate echoed trusted configuration supplies the denominator, rather than a fictional configuration table. Ratios require a positive trusted denominator and no unknown observation in the evaluated windows. A closed/zero denominator yields a null ratio. This is observation coverage, not roster/break/account availability.

### Runnable scoped registry and synthetic replay

`backend.agents.tools.registry.ScopedToolRegistry(tools, scope)` binds all five methods to an injected trusted manager scope. `invoke(name, arguments)` validates the corresponding request model; arguments cannot supply store/actor scope, database paths, observation policy, SQL, or dispatch. `input_schemas()` publishes exactly the five request JSON Schemas. Employee scopes and unregistered names are rejected. This callable layer does not expose a new HTTP endpoint or turn role headers into authentication; Phase 3 still needs an authenticated server-side store binding.

Approach metrics are unavailable under a zone-restricted trusted scope: unseen earlier assistance in another zone prevents proof of the first confirmed interaction. Counts/durations still use the permitted rows. A request zone filter alone may narrow interaction selection while history/track joins retain the full authorized camera/run scope.

Runnable local example for **synthetic data only**, from the repository root (create the ignored parent folder first):

```powershell
New-Item -ItemType Directory -Force data/outputs/moiz-phase2 | Out-Null
.venv/Scripts/python.exe -m backend.events.fixtures --db data/outputs/moiz-phase2/fixture.sqlite3
```

```python
from backend.agents.contracts import TrustedAccessScope
from backend.agents.tools.common import ObservationContext
from backend.agents.tools.contextual import SQLiteAnalyticsTools
from backend.agents.tools.registry import ScopedToolRegistry

# A trusted server adapter must supply these in the actual application.
# This local synthetic example is not a production login/store policy.
context = ObservationContext(context_id="synthetic-entrance-config", store_id="store-1",
    zone_id="z1", camera_ids=("c1",), available_sources=("footfall",))
tools = SQLiteAnalyticsTools("data/outputs/moiz-phase2/fixture.sqlite3", synthetic=True,
                            contexts=(context,))
registry = ScopedToolRegistry(tools, TrustedAccessScope(actor_id="local-synthetic-manager",
    store_id="store-1", role="manager", allowed_camera_ids=("c1",), allowed_zone_ids=("z1",)))
result = registry.invoke("get_footfall", {
    "window": {"start": "2026-11-03T09:00:00Z", "end": "2026-11-03T21:00:00Z"},
    "filters": {"zone_id": "z1"}, "granularity": "hour"
})
assert result.synthetic and len(result.buckets) == 12
print(result.model_dump_json(indent=2))
```

To configure a real reader, set `synthetic=False` only for a real event database, and obtain expected cameras, available feeds and operating windows from verified server-side camera/store configuration. Never infer them from the mere presence of event rows. Without that configuration, positive stored observations are still returned with partial-data limitations; absent counts and unsupported coverage/ratios remain null. Result `truncated` concerns returned buckets/roles/episodes/zones; evidence `truncated` concerns the supporting ID sample. Neither truncates the underlying aggregate.

### Deferred follow-on interfaces (not registered or implemented here)

| Proposed interface | Source and proposed result | Required limitations/dependencies |
|---|---|---|
| `get_queue(*, scope, window, counter=None, limit=100)` | `queue_samples`; length samples and nullable estimated wait seconds with per-metric event evidence | Confirm counter→camera/zone mapping. Label wait as heuristic (`estimated=true`), not measured waiting time; retain scoped UTC/health/truncation rules. |
| `get_pipeline_health(*, scope, window, limit=100)` | `pipeline_health`; FPS, confidence, unknown-role share, churn and frozen/dark sample metrics/evidence | Null confidence/check fields remain unknown; camera-wide health uses authorized camera mapping. This is a proposed reporting interface, separate from the implemented internal observation helper. |
| `get_alerts(*, scope, window, status=None, limit=100)` | Existing application alert records through a separately authorized read adapter; event evidence references when present | App alert tables are not in `events/schema.sql`. Store/actor ownership and evidence mapping must be agreed before implementing. No invented event-store alerts table. |
| Legacy `get_pos_sales(*, scope, window, category=None)` | Unavailable: POS analytics is outside the agreed project scope | Retained only to resolve the older handoff name; no POS implementation, metric claim or registered callable is added. |

These follow-on requests would use the same bounded/timezone-aware request, scoped access, status/null and evidence conventions after their source contracts are agreed. Arbitrary `run_readonly_sql` remains deferred. No graph, provider, business-agent policy, roster selection or operational task delivery is part of these readers.

Observation configuration is also checked against cameras present in the selected event rows: an unexpected camera makes observation completeness unknown, even when a configured camera is healthy. Cross-run/camera event counts are stored-event counts, not deduplicated physical-person counts; apply a run filter when evaluating a specific CV run.

## Analytics graph boundary (Moiz Phase 3)

`backend.agents.graph.run_analytics(request, registry, *, router=None, specialists=None, limits=None) -> GraphRun` is the callable graph boundary. It reuses the Phase 2 `ScopedToolRegistry`; its scope must be constructed in trusted server code. No public graph HTTP route is added: `backend/app.py` accepts internal-secret/role/user headers and the current frontend proxy forwards session identity, but neither path supplies an authoritative actor-to-store binding. This remains a production integration dependency.

`AskRequest` contains question (3–2000 characters), mandatory validated time window, optional run/camera/zone filters and request ID. It rejects caller-supplied scope, node names and operational envelopes. The run ID is always server-generated. Actual LangGraph nodes are `route`, `customer_behavior` or `employee_activity`, `ground`, optional `repair`, and `finish`. The normal path has four steps; a repair path has six. `GraphLimits` bounds steps (default 8, max 12), total tool attempts (default 8, max 20) and each captured tool result (default 512 KiB). No arbitrary SQL or dispatch tool is registered.

The offline router is deliberately narrow and is not a complete Query Agent. `JsonRouter(complete)` is the optional structured-provider extension: inject an existing completion function such as `voice_agent.call_hugging_face` only when real provider use is authorized. No provider is selected/called by default, no new model name is hardcoded, and LangSmith tracing is disabled for graph invocation. The injected provider owns network timeout/model configuration. Graph step/tool budgets do not preempt a blocking Python specialist/provider; registration is trusted server code, not a sandbox for arbitrary user programs.

`SpecialistDraft` permits only structured claims. Each `Claim` binds a captured call ID and exact Pydantic metric path to value, unit, store, window, filters and the metric's complete returned evidence sample, including truncation metadata. Grounding uses a 1e-9 absolute/relative numeric tolerance. A matching number elsewhere in a result is insufficient. Null/unsupported values, wrong fields, units, scope or citations cannot be published. One specialist repair is allowed; any still-invalid claim is removed. Final numeric answer sentences use server-owned field labels/context, not model-written prose. This validates support against reader output, not CV accuracy or subjective business interpretations.

Customer Behavior registration permits footfall, zone dwell, interactions and unattended tools. Employee Activity permits coverage, interactions and unattended tools. Inject `SpecialistRegistration(handler, allowed_tools, development_stub=False)` under either fixed target to register Ruhab's implementation. Her callable signature is `handler(context: SpecialistContext, tools: ReadToolFacade, prior: SpecialistDraft | None, issues: tuple[GroundingIssue, ...]) -> SpecialistDraft`. `tools.invoke(name, arguments)` returns `(call_id, typed_result)`; it cannot broaden the user's validated window/explicit filters or its trusted scope. `claim_for(call_id, result, path)` helps construct a correctly linked claim. The default adapters demonstrate these calls only: they do not implement segmentation, hot/gray-zone policy, availability, rankings or narration.

Graph construction follows the [official LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api). Current verification uses injected offline doubles and the existing synthetic event data; live provider and business-agent acceptance remain pending.

### Callable service, development traces and route contracts

`AnalyticsService(tools, *, router=None, specialists=None, traces=None, limits=None)` in `backend/agents/service.py` exposes `ask(request: AskRequest, *, scope: TrustedAccessScope) -> GraphRun` and `get_run(run_id, *, scope) -> GraphRun`. Scope is server-injected separately, never parsed from the question/body. Each run carries request/run IDs, trusted scope/window/filters, selected node, captured typed tool results, verified claims and their citations, node/tool timings, validated per-call arguments, errors, repair count, response and `trace_retained`.

The default `MemoryTraceStore` is **development-only**: FIFO retention up to 20 runs, 30-minute TTL, maximum 2 MiB per serialized run, with process-restart loss. Its configurable bounds are at most 100 runs, one-day TTL and 4 MiB per record. IDs are append-only and retrieval requires exact full trusted-scope equality, including actor, store, role and allowlists. Missing, expired and unauthorized runs all return the same not-found exception. Serialized snapshots prevent callers from mutating saved traces. The service also verifies scope/run ID returned by an injected store. Implement `RunTraceStore.put(run)` / `get(run_id, scope)` for future durable persistence with equivalent authorization/retention behavior; no new app/event schema or migration is added here.

Retention failure does not fabricate a saved run: `trace_retained=false`, error `trace_not_retained` and a limitation accompany any still-grounded answer. A successful trace is not a durable audit log. No public listing/search endpoint is exposed. Provider token usage/cost is unavailable, not recorded as zero. Callbacks/providers remain trusted server code: step/tool/result bounds do not forcibly cancel a blocking callback. External provider deadlines and durable operational tracing remain integration work.

| Proposed HTTP contract (not exposed yet) | Validated input / result | Required server integration |
|---|---|---|
| `POST /agents/ask` | Body `AskRequest`, response `GraphRun`; malformed inputs become validation errors | Resolve current authenticated actor and authorized store/filters from authoritative server records before `service.ask`. Never accept scope/node/dispatch in the body or treat arbitrary role headers as store authorization. |
| `GET /agents/runs/{id}` | Server-generated run ID, response the retained `GraphRun`; not-found for unknown/expired/unauthorized | Resolve the same current trusted actor/store/permission scope and call `get_run`. Do not expose another actor's or a broader historical trace. |

These routes are deliberately absent from `backend/app.py` pending the real account/store binding. The existing internal-secret dependency and session-to-header proxy are integration building blocks, not a completed multi-store identity policy.

### Runnable offline fixture service example

Generate a disposable synthetic store, leaving live/event databases untouched:

```powershell
New-Item -ItemType Directory -Force data/outputs/moiz-phase3 | Out-Null
.venv/Scripts/python.exe -m backend.events.fixtures --db data/outputs/moiz-phase3/fixture.sqlite3
```

```python
from backend.agents.contracts import EventFilters, TrustedAccessScope
from backend.agents.graph_contracts import AskRequest
from backend.agents.service import AnalyticsService
from backend.agents.tools.common import ObservationContext
from backend.agents.tools.contextual import SQLiteAnalyticsTools

# Explicit local synthetic context; production scope/configuration requires real binding.
scope = TrustedAccessScope(actor_id="synthetic-manager", store_id="store-1", role="manager",
                           allowed_camera_ids=("c1",), allowed_zone_ids=("z1",))
observation = ObservationContext(context_id="synthetic-entrance", store_id="store-1",
    zone_id="z1", camera_ids=("c1",), available_sources=("footfall", "zone_dwell"))
service = AnalyticsService(SQLiteAnalyticsTools("data/outputs/moiz-phase3/fixture.sqlite3",
                           synthetic=True, contexts=(observation,)))
request = AskRequest(question="Show customer footfall", filters=EventFilters(zone_id="z1"),
    window={"start":"2026-11-03T09:00:00Z", "end":"2026-11-03T10:00:00Z"})
run = service.ask(request, scope=scope)
assert run.development_stub and run.trace_retained and run.claims
assert [n.node for n in run.nodes] == ["route", "customer_behavior", "ground", "finish"]
assert service.get_run(run.run_id, scope=scope) == run
print(run.response)
```

This runs locally without a provider. The employee path uses a coverage question and a trusted zone observation declaration; missing operating windows leave staffed/open ratios unavailable. The development adapters select existing tools for footfall, dwell, interaction or unattended questions; a dwell question without a zone returns an explicit zone-required notice rather than guessing. Their small result limits remain visible as partial/truncated source data. They do not implement Ruhab's business policies or a complete manager Query Agent.

### Ruhab's registration example (development illustration)

The same handler signature applies to Customer Behavior and Employee Activity. Example using an allowed interaction metric:

```python
from backend.agents.graph_contracts import SpecialistDraft
from backend.agents.specialists import SpecialistRegistration, claim_for

# Illustrative hook only: Ruhab replaces this with her actual business-agent implementation.
def customer_hook(context, tools, prior=None, issues=()):
    call_id, result = tools.invoke("get_interactions", {
        "window": context.request.window.model_dump(mode="json"),
        "filters": context.request.filters.model_dump(exclude_none=True)
    })
    claim = claim_for(call_id, result, ("confirmed_count",))
    return SpecialistDraft(claims=() if claim is None else (claim,))

bindings = {"customer_behavior": SpecialistRegistration(customer_hook,
    frozenset(("get_interactions",)), development_stub=True)}
# Pass specialists=bindings to AnalyticsService to exercise this hook.
# Keep development_stub=True for illustrations; registration alone is not acceptance evidence.
```

For repair, `prior` is the rejected structured draft and `issues` contains indexed codes (`missing_metric`, `wrong_context`, `wrong_value`, `wrong_evidence`). The handler may return a corrected `SpecialistDraft` once. It may also return the fixed `zone_required` notice; arbitrary answer/label/prose fields are rejected. Numeric claims are direct metric references, not unsupported arithmetic invented by the model. Values accepted within grounding tolerance are normalized to the exact captured metric before publication, and estimated metrics are labelled estimated by the renderer. Real qualitative business reasoning/narration remains separate work.

For an optional existing-HF router, construct `JsonRouter(complete=backend.voice_agent.call_hugging_face)` in authorized server wiring; this uses existing provider configuration without introducing another hardcoded model. No live-provider example is executed as part of this deliverable. Failure/invalid routing output is sanitized to unavailable, not leaked as raw provider error text. Direct operational requests are refused conservatively; dispatch is absent from the tool capability set regardless of prompt wording.

Each tool call captures its own read-only snapshot. A multi-call graph run does not establish one global database transaction; use a stable filtered CV run when reproducible comparisons are required. Grounding proves association with captured tool metrics and evidence, not detector accuracy or real-world causal truth. Saqib's unattended-verdict limitation remains present in source limitations; Ruhab's production-agent validation and Saqib's feed/auth/configuration integration remain pending.

## Internal operational dispatch contract (Moiz Phase 4)

`backend.agents.operational.OperationalDispatchAdapter(handler=None).handle(event, *, scope) -> DispatchReceipt` is a separate internal operational-event path. It is **not** an analytics tool, specialist target or manager-question route. It registers no live callback/HTTP route and imports no production task/voice writer. Without a handler it returns `decision=unavailable`, `reason_code=handler_not_registered`, `handler_invoked=false`, with no task ID or dispatch attempt.

Inputs are `OperationalEvent` and separately server-created `TrustedOperationalScope(service_id, store_id, allowed_zone_ids, allowed_sources=...)`. A manager `TrustedAccessScope` is not accepted as an operational capability. These models assert/validate internal context; they are not authentication or a public authorization token. Event store/zone/source must be permitted by the scope before the handler is called.

| Operational JSON field | Contract / relationship to existing Saqib code |
|---|---|
| `eventType` | Existing aisle event names: `unattended_customer`, `unstaffed_zone`, `crowding`; schedule/roster actions are excluded. |
| `source`, `zoneId`, `sourceTimestamp`, `evidence`, `severity` | Reuse existing endpoint field names. Sources are limited to `customer_behavior` / `employee_activity`. Severity is low/medium/high. Timestamp is aware and normalized to UTC. |
| `eventId` | Required upstream stable ID, preserved by the adapter. Existing endpoint currently generates a fresh UUID instead; it is not a drop-in consumer for this contract. |
| `storeId`, `idempotencyKey` | Required trusted-scope/store and stable retry identity extensions; the existing endpoint does not currently preserve/enforce them. Saqib must supply durable per-store idempotency in his callback. |
| `window` | Completed validated analysis interval (same UTC/max-31-day conventions as the tools). `sourceTimestamp` must be at or after its end; no freshness threshold is invented here. |
| `evidence.demand`, `evidence.coverage` | `SignalEvidence`: storeId/zoneId/window/status/synthetic/evidence/limitations. Both must match the event context and synthetic flag. Coverage citations must be from `get_coverage` on `zone_dwell`/`pipeline_health`; shared evidence IDs/query/truncation conventions remain. |

Snake-case Python field names and camelCase JSON aliases are both accepted, with unknown/approval/auto-mode fields rejected. Use `model_dump(mode="json", by_alias=True)` for the JSON envelope. Existing endpoint compatibility is a field mapping, **not** permission to post this envelope to `/orchestrator/events`; that endpoint ignores stable/store/idempotency extensions and performs real writes. No such post is made here.

The injected signature is `handler(*, event: OperationalEvent, scope: TrustedOperationalScope) -> DispatchOutcome`. Outcomes echo eventId/idempotencyKey/storeId/zoneId and use `decision` equal to `dispatched`, `no_eligible_employee`, `duplicate`, `unavailable` or `error`. The assigned scenario uses Saqib's existing `dispatched` spelling. `taskId` and `selectedEmployeeId` are required together for dispatched, optional together for duplicate, absent for non-assignment results; `alertId` is optional. `selectedEmployeeId` corresponds to existing `dispatch_decisions.selected_employee_id`, although it is not currently returned by the legacy event endpoint. Saqib's callback must explicitly supply it.

Receipts echo outcome/context plus handler_invoked, synthetic, measured elapsed_ms, a controlled reason_code and limitations. They are handler reports, not proof of employee acknowledgement or voice delivery. Exceptions and invalid/mismatched callback outcomes return sanitized errors without task claims. Handler errors can occur after side effects: outcomes remain uncertain and the adapter never automatically retries. Real deduplication, transaction boundaries, source-zone/roster/active-task safety and delivery belong to Saqib. No manager approval or manager-enabled auto mode is introduced for direct aisle events.

Signal quality/limitations are forwarded, including partial/unknown observation and the existing unattended-verdict derivation limitation. This adapter verifies envelope consistency, not database-row authenticity or the policy that produced a demand event. Ruhab's approved policy must decide when to emit an event; Saqib's handler must verify eligibility/safety before any real assignment. No new hot-aisle threshold, staffing policy or production task is invented by Moiz's adapter.

### Saqib's exact plug-in location and remaining contract work

The integration point is the constructor argument to `backend.agents.operational.OperationalDispatchAdapter`: inject a callable implementing `DispatchHandler`, then invoke `.handle(event, scope=trusted_operational_scope)` from an **internal event consumer**. Do not add it to `REQUEST_TYPES`, `ALLOWED_TOOLS`, `SpecialistRegistration`, `RouteDecision`, `AskRequest` or the manager analytics service. `OperationalEvent.model_json_schema()` and `DispatchOutcome.model_json_schema()` expose the full typed input/result shapes; models are revalidated at the boundary, including programmatically updated model instances.

Saqib needs to supply:

1. Authoritative internal producer authentication, store/zone/source binding and event-row provenance checks. A Pydantic `TrustedOperationalScope` alone does not authenticate a producer. A manager's analytics scope/header cannot become this capability.
2. An internal `DispatchHandler` that reuses his employee/account, roster/availability, active-task and source-zone safety logic, with real account IDs (not CV track IDs). No manager approval or manager-enabled auto switch is a prerequisite for direct aisle events; separate next-day schedule planning stays outside this contract.
3. Durable, atomic idempotency scoped by `(storeId, idempotencyKey)`, preserving the stable upstream eventId and comparing event/zone/payload identity to detect key reuse conflicts. Return duplicate for a recognized equivalent event, not a second task. The adapter intentionally has no cache, ledger, cooldown or automatic retry. Concurrent/restart-safe task creation and failure reconciliation belong to this handler.
4. Task/alert/decision persistence, delivery/voice and acknowledgement evidence, plus outcome mapping to the typed echo fields. Existing `select_dispatch_employee` / `create_task_for_employee` are references to reuse or harden in Saqib's scope, **not** called by this adapter. Existing `/orchestrator/events` generates UUIDs and lacks the required store/key contract; it must not be used as a drop-in callback. Its `paused` / `alert_only` cases must map deliberately to unavailable/non-assignment when appropriate; the adapter adds no approval or auto-mode gate.
5. Real-feed and no-eligible/repeat-event acceptance evidence with the exact model/configuration/event versions. Handler-reported dispatched is not evidence that an employee heard or acknowledged a message. Persist the envelope and receipt in his operational audit path rather than inserting operational capabilities into manager-question traces.

Ruhab owns demand/coverage business policy and decides when its outputs become one of the supported event types. The producer then packages references from scoped tool/business results into `SignalEvidence`, retaining status, synthetic marker and limitations; both contexts must match the chosen store/zone/window. Moiz's adapter validates this envelope and passes it directly to Saqib's handler. It does not infer hot/gray thresholds, choose staff, change rosters or silently promote unknown coverage/derived unattended waits into confirmed facts. Sampled/truncated evidence is not a complete source population; the handler must resolve the data it needs before any real eligibility decision.

### Fake-only fixture replay

The regression replay generates Saqib's unchanged fixture in pytest's ignored temporary directory, uses the actual read-only unattended/coverage readers, deliberately stages a synthetic event, and invokes a fake callback twice (dispatched then duplicate). It checks source limitations and an unchanged event-database hash. It is **not** a test of a real demand policy or real assignment/voice delivery.

```powershell
.venv/Scripts/python.exe -m pytest backend/agents/test_operational_integration.py::test_seeded_operational_replay -q --basetemp data/outputs/moiz-phase4/replay-fresh
```

Use a fresh ignored base directory for another run. For the executable example below, generate a disposable file first:

```powershell
New-Item -ItemType Directory -Force data/outputs/moiz-phase4 | Out-Null
.venv/Scripts/python.exe -m backend.events.fixtures --db data/outputs/moiz-phase4/fixture.sqlite3
```

```python
from backend.agents.contracts import (CoverageRequest, EventFilters, TimeWindow,
                                     TrustedAccessScope, UnattendedRequest)
from backend.agents.operational import (DispatchOutcome, OperationalDispatchAdapter,
    OperationalEvent, OperationalEvidence, SignalEvidence, TrustedOperationalScope)
from backend.agents.tools.common import ObservationContext
from backend.agents.tools.contextual import SQLiteAnalyticsTools

# Synthetic read-only source selection, not real producer authentication or business policy.
window = TimeWindow(start="2026-11-03T09:00:00Z", end="2026-11-03T21:00:00Z")
reader_scope = TrustedAccessScope(actor_id="synthetic-reader", store_id="store-1", role="manager",
    allowed_run_ids=("fixture-2026-11-03",), allowed_camera_ids=("c2",), allowed_zone_ids=("z3",))
layout = ObservationContext(context_id="synthetic-z3", store_id="store-1", zone_id="z3",
    camera_ids=("c2",), available_sources=("unattended_episodes", "zone_dwell"))
reader = SQLiteAnalyticsTools("data/outputs/moiz-phase4/fixture.sqlite3", synthetic=True, contexts=(layout,))
filters = EventFilters(run_id="fixture-2026-11-03", camera_id="c2", zone_id="z3")
demand = reader.get_unattended(scope=reader_scope,
    request=UnattendedRequest(window=window, filters=filters, limit=1))
coverage = reader.get_coverage(scope=reader_scope,
    request=CoverageRequest(window=window, filters=filters))
context = dict(store_id="store-1", zone_id="z3", window=window, synthetic=True)

# This event/type is manually staged for the replay; no policy trigger is being implemented here.
event = OperationalEvent(event_id="synthetic:replay:z3", idempotency_key="synthetic:store-1:z3:fixture",
    store_id="store-1", zone_id="z3", event_type="unattended_customer", source="customer_behavior",
    source_timestamp=window.end, window=window, evidence=OperationalEvidence(
        demand=SignalEvidence(**context, status=demand.status, evidence=demand.episode_count.evidence,
                              limitations=demand.limitations),
        coverage=SignalEvidence(**context, status=coverage.status,
            evidence=coverage.zones[0].unknown_observation.evidence, limitations=coverage.limitations)))

# A fake in-memory ledger for demonstration ONLY; no task, employee or voice message is created.
seen = set()
def fake_dispatch(*, event, scope):
    key = (event.store_id, event.idempotency_key)
    decision = "duplicate" if key in seen else "dispatched"
    seen.add(key)
    return DispatchOutcome(event_id=event.event_id, idempotency_key=event.idempotency_key,
        store_id=event.store_id, zone_id=event.zone_id, decision=decision,
        task_id="fake-task", selected_employee_id="fake-employee")

producer_scope = TrustedOperationalScope(service_id="synthetic-producer", store_id="store-1",
                                        allowed_zone_ids=("z3",))
adapter = OperationalDispatchAdapter(handler=fake_dispatch)
first = adapter.handle(event, scope=producer_scope)
second = adapter.handle(event, scope=producer_scope)
assert first.decision == "dispatched" and second.decision == "duplicate"
assert first.synthetic and second.synthetic
assert OperationalDispatchAdapter().handle(event, scope=producer_scope).decision == "unavailable"
print(first.model_dump_json(by_alias=True, indent=2))
print(second.model_dump_json(by_alias=True, indent=2))
```

Only the fake callback above is invoked in this example. Production callback injection, source-zone safety, restart/concurrent deduplication and delivery are not verified by a simulated outcome. No new operational HTTP route or manager-question tool is introduced.

## Planned map/category representation boundary

Stable map-location IDs and existing zone_id scope keys must remain distinct from the live category attribute. Proposed category labels are customer / employee / customer_employee / no_one only; this is not yet a runtime schema/API. Each map layer must declare its observation window, value/unit, role filter, confirmed-interaction semantics, coordinate/map/config version and separate validity metadata. Do not recast unknown CV role or missing camera coverage as a fifth category or no_one, and do not change authorization scopes as occupancy changes. Exact camera-to-map transform, aggregation cadence and ambiguity handling remain MAP-2/MAP-3 decisions with owners in the combined plan.
