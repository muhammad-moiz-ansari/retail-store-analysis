# Data Contracts

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
