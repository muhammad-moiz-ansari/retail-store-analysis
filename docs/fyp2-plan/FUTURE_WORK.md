# RetailPulse — Complete Future-Work Implementation Plan

## Context

`FYP Report-main.pdf` lists unfinished work in three places: the out-of-scope list (§1.6), current limitations (§8.11) and the Remaining FYP Plan (Ch. 9). Requirements are tracked in the FR/TC tables (§4.7–4.8, App. C).
`docs/fyp2-plan/` already covers part of this (Steps 0–4: model consolidation, analytics, dashboard binding, alerts, evaluation). It explicitly **leaves out** the out-of-scope items, the narration/query agents, report export and the employee-linkage work. A0 model consolidation is implemented: COCO tracks and `best.pt` labels roles; see `MODELS.md` and `interaction/pipeline.py`/`role_classifier.py`. The remaining summary/dashboard steps are separate from the existing event-store feeds. Saqib's B0/B4 event code and Moiz's typed contracts, five read-only tools/registry and callable LangGraph/trace foundation and fake-verified internal operational adapter now exist; this does not complete the planned summary module, real business agents, public/internal producer auth, real assignment/idempotency/voice delivery, live-provider evaluation or frontend binding.

This plan covers **every** item. Phase A reuses the existing fyp2-plan steps and adds the details they leave open. Phases B–D cover everything else.

Current owner-specific implementation, verification and blockers are maintained in [PROGRESS.md](PROGRESS.md) and [PENDING.md](PENDING.md), with responsibilities in [PLAN.md](PLAN.md). For Moiz's tool tasks, generated fixture/check outputs use ignored `data/outputs/moiz-phase1/`, `data/outputs/moiz-phase2/` `data/outputs/moiz-phase3/` or `data/outputs/moiz-phase4/`; no `Report/` edits or report-evidence generation are authorized. The user separately authorized committing pre-existing report contents without editing them. The broader guides below retain future work rather than expanding this phase.

### Ground rules (apply to every step)
- Plain logic over the existing tracks first. A new model is allowed only in Phase D, and only where the report itself says a model is needed (depth, optional re-ID upgrade). Each new model needs a benchmark showing it beats the logic-only baseline.
- Reuse what exists: `run_script`/`start_job`/`interaction_result` (`backend/app.py:129-198`), `ingest_orchestration_event` (`app.py:570`), `select_dispatch_employee`/`create_task_for_employee` (`app.py:69-111`), `IdentityRegistry` (`backend/interaction/identity.py`), `handoff_core` (pure, tested), `voice_agent.py` HF-router client, `benchmark.py`, the `/api/backend/[...path]` proxy, `runBackendJob` (`frontend/src/lib/backend-job.ts`) and the Retro UI components.
- Every new route uses `require_manager` or `require_employee_or_manager`. Every user-supplied path is matched against a server-side listing and never joined into a path.
- Unknown stays unknown: no view or coverage means "n/a", never 0 (the report's FR-07 and FR-35 wording).
- Each step ends with a pytest or a scripted check and a "Done when" line. Results go to `backend/interaction/benchmarks/` or `Report/evidence/`.

### Coverage map (report item → step)
| Report item | Step |
|---|---|
| Dashboard vision metrics are demo data; interactions are CLI-only | A1, A2 |
| Footfall, approach, unattended, idle, dwell, heatmap, paths, crowd density | A1 |
| Alerts on real events; Orchestrator coordination | A3, B4 |
| Interaction accuracy rests on one clip; ten clips await labels; threshold tuning | A4 |
| Model consolidation | A0 |
| Employee Activity Agent (FR-35, TC-28) | B1 |
| Task Assignment linkage of tracks to accounts, source-zone safety (FR-36, TC-29–33) | B2 |
| Insight Narration Agent + report/PDF export (FR-17, TC-13) | B3 |
| Query Agent (FR-37, TC-34–36) | B5 |
| System Status with real telemetry (FR-19, TC-41) | B4 |
| Employee pages, profile, settings consumers, monitoring (FR-11/12/13/20/29) | B6 |
| All Planned/Pending TCs (09, 10, 26–48) | C1 |
| Role-navigation checks on every route, security, privacy (NFR-07–10) | C2 |
| CPU throughput and page timings (NFR-05/06, TC-46) | C3 |
| Report and documentation update | C4 |
| Cross-camera identity association / camera handoff | D1 |
| Metric floor-plane distance | D2 |
| Foot/keypoint locator | D3 |
| 3D reconstruction / per-pixel depth | D4 |
| Shelf-level product interaction | D5 |
| Store layout and promotion effectiveness | D6 |
| Real-time processing | D7 |
| Multi-store scaling | D8 |
| Real retail-partner pilot | D9 |

---

## Phase A — Finish the FYP-2 core (report weeks 1–12)

### A0. Model consolidation (done 2026-10-24)
`best.pt` missed ~60% of people on non-store footage, so it did not replace COCO. COCO tracks, `best.pt` labels each new track and rechecks it every 2 s. Details and numbers in `MODELS.md`.

### A1. Analytics module (3–4 days)
New file `backend/interaction/analytics.py`, made of pure functions. `summarise(detections, interactions, people, config) -> dict` returns the shape in `docs/fyp2-plan/CONTRACTS.md` plus two keys that contract lacks: `paths` and `crowding`.

Guide:
1. **Config** (`interaction/config.py`): add `entrance_line: tuple[float,float,float,float] | None = None` (normalised x1,y1,x2,y2), `unattended_after_s=60`, `idle_window_s=30`, `idle_move_px=40`, `heatmap_grid=(32,18)`, `min_track_frames=5`, `analytics_zones: tuple[tuple[str,float,float,float,float],...] = ()` (named, normalised rectangles) and `crowd_capacity: dict[str,int]`.
2. **Filter noise first:** drop tracks with `frames_observed < min_track_frames` (ID-switch mitigation in the PLAN risks table).
3. **footfall:** per track, find the sign change of the cross product of consecutive centres against `entrance_line`; the direction comes from the sign. If the line is None, return `None`, not `{in:0,out:0}`. Occupancy is unknown at clip start, so report `in`/`out` only and never an absolute "inside" count (FR-02).
4. **approach_times:** for each customer, `first_seen` → `started_at` of their first confirmed interaction. Customers with no interaction are excluded from the mean and counted separately.
5. **unattended:** a customer present longer than `unattended_after_s` with no confirmed interaction covering that window. Return `{customer_track_id, from, to, waited_s}`.
6. **employee_idle:** slide `idle_window_s` windows over the employee's centres. Idle means centre displacement below `idle_move_px` **and** no confirmed interaction overlapping the window (FR-35: stationary while assisting is not idle). Also return `observed_s`, so `share = idle_s / observed_s` and unobserved time stays unknown.
7. **zone_dwell:** seconds of centres inside each `analytics_zones` rectangle, split by role. A zone outside the frame or never covered is `null`.
8. **heatmap:** one `numpy.histogram2d` over all centres; `range` = frame size, taken from the first detection's frame.
9. **paths:** per customer, the ordered list of zones visited (collapse repeats). The top N paths come from `collections.Counter`. This replaces the demo `TOP_PATHS`.
10. **crowding:** per zone, the maximum and mean concurrent people per frame, plus seconds above `crowd_capacity[zone]`.
11. **CLI hook** (`interaction/cli.py`, after the `people.json` write at line ~255): `args.output.with_suffix(".summary.json").write_text(json.dumps(analytics.summarise(...)))`. Add a `--config <json>` option that loads per-store overrides into `InteractionConfig`, so thresholds are store-specific (the answer to the "Gucci" generalisability critique).
12. **Tests** (`backend/interaction/test_analytics.py`) with hand-built detections: one inbound and one outbound crossing; one unattended customer; one stationary employee who is assisting (not idle) and one stationary employee who is not (idle); one zone dwell; heatmap cell sums equal the number of centres; one two-zone path; a crowding threshold breach; `entrance_line=None` returns `None`.

**Done when:** a CLI run on `backend/videos/ShopAssistant1cor.mp4` writes `.summary.json` and `pytest backend/interaction/test_analytics.py` passes.

### A2. Analytics API and dashboard binding (3 days)
1. **Backend** (`app.py`): `GET /analytics/runs` globs `OUTPUT_DIR/**/*.summary.json` and returns `{run, duration_s, created_at}` (mtime). `GET /analytics/summary?run=` serves the latest run when `run` is omitted, returns 404 for an unknown name, and looks `run` up in the glob listing — it never builds a path from it.
2. Extend `interaction_result()` (`app.py:191`) to include `summary`, so the Interactions page shows it right after a run.
3. **Frontend:** add one small hook `useAnalyticsSummary(run?)` in `frontend/src/lib/` (fetch `/api/backend/analytics/summary`), then bind:
   - `dashboard/page.tsx` KPI tiles → footfall, interactions.count, mean_approach_s, unattended.length
   - `customer-info/page.tsx` `ATTENDANCE_DATA`, `INTERACTION_SPARKLINE`, `UNATTENDED_EVENTS`, `ZONE_DWELL`, `HOURLY_TRAFFIC` → summary keys; `TOP_PATHS` → `paths`
   - `employee-info/page.tsx` idle/engagement figures → `employee_idle`, interactions per employee track
   - `spatial-analytics/page.tsx` heatmap → `heatmap`, density → `crowding`
4. Add a run picker: a `<select>` fed by `/analytics/runs` (FR-12 interval filter = run selection plus a time-window slider over `duration_s`).
5. Every value still fake gets the existing `Badge` with "demo data". With no runs, pages show an empty state, never fake numbers.

**Done when:** after one CLI run the four pages show that run's numbers; deleting the summary shows empty states; an anonymous call to `/api/backend/analytics/summary` returns 401 and an Employee call returns 403.

### A3. Real events → alerts → dispatch (1–2 days)
Better than the existing PLAN.md Step 3: route vision events through the orchestrator, so dispatch and voice work too.
1. Split the body of `ingest_orchestration_event` (`app.py:570`) into `record_event(conn, body, event_id=None)`. The route calls it with a random id.
2. New `import_run_events(run)`, called the first time `/analytics/summary` reads a run and from `interaction_result()`. For each `unattended` entry it calls `record_event` with `eventType="unattended_customer"`, `source="vision"`, severity `high` if `waited_s ≥ 2×unattended_after_s`, and deterministic `event_id = sha1(f"vision:{run}:{track}:{from}")`. Make the alert and event inserts `INSERT OR IGNORE` on that id, so a repeat read does nothing. Do the same for `crowding` breaches (`eventType="crowding"`).
3. Remove the `ALERTS` fallback array in `alerts/page.tsx`.
4. Tests: a FastAPI `TestClient` test that imports one run twice creates exactly one alert, one dispatch decision and at most one task; resolving the alert records the actor and time (TC-40).

**Done when:** the TC-40 test passes and an unattended customer in a clip shows up on `/alerts` and as a task on `/employee-home`.

### A4. Evaluation and threshold tuning (ongoing from week 1; labelling needs no code)
1. Label all 10 waiting clips per `backend/interaction/ANNOTATION_GUIDE.md` into specs shaped like `evaluation_spec.example.json`. Add `footfall`, `unattended`, `zone_dwell`, `roles` and `handoffs` (for D1) fields to the spec.
2. Extend `benchmark.py` to score the summary against those labels: footfall absolute error, unattended precision/recall (interval IoU ≥ 0.3, the same matcher), role accuracy per track, and an ID-switch count from `role_segments`.
3. **Threshold sweep:** add `--set key=value` (repeatable) to `benchmark.py`, which overrides `InteractionConfig` fields. A shell loop sweeps `facing_angle_degrees ∈ {45,60,75}` × `min_facing_fraction ∈ {0.3,0.5,0.7}` × `unattended_after_s ∈ {30,60,90}`. Choose values on 6 clips and report on the held-out 5, so the reported numbers are not tuned on the clips they are tested on.
4. Write the pooled with/without-judge P/R/F1 table, per-failure error analysis (occlusion, ID switch, wrong role, pass-by) and the chosen thresholds to `backend/interaction/benchmarks/report.json` and `Report/evidence/`.

**Done when:** all 11 clips have specs, the held-out table exists, and TC-09/TC-10/TC-26 have results.

---

## Phase B — Agents and product features (report weeks 4–12)

### B1. Employee Activity Agent (FR-35, TC-28) — 1 day after A1
This is mostly A1's `employee_idle` plus coverage:
1. `coverage_gaps`: zones with customers present and no employee in the zone for more than `coverage_gap_s` (new config field, default 45). Unobserved zones → `null`.
2. `staff_availability`: per frame, employees not in an interaction; shown as a time series.
3. Feed `coverage_gaps` into A3 as `eventType="unstaffed_zone"`.
4. TC-28 test: an employee standing still beside a customer during a confirmed interaction gets `idle_s == 0`; the same employee standing still alone gets `idle_s > 0`.

### B2. Track → account linkage and safe dispatch (FR-36, TC-29–33) — 2–3 days
1. **Link:** add `user_id` to the `global_person` document. `IdentityRegistry.register_employee` (`identity.py:120`) gets a `user_id` parameter and stores it; the audit row already exists in `role_assignment`.
2. **UI:** on the Interactions page, list the employee tracks from the latest run with a crop thumbnail, rendered by the CLI from `detections.json` at the track's best-confidence frame and saved as `<output>.tracks/<id>.jpg`. Add a "This is <employee>" select that calls the camera service `PUT /people/{id}/role` (exists, `camera_service.py:166`) extended with `user_id`.
3. **Linkage is per run:** a track id means nothing in the next run, so linkage is valid for that run (or via D1 re-ID later). Never assume a detected employee track equals a task recipient (report §9.4).
4. **Source-zone safety:** in `select_dispatch_employee` (`app.py:69`), exclude an employee whose roster zone would drop below `zones.min_staff` if they leave (count other available rostered staff in that zone through a subquery). Add a `stale` rule: a task not acknowledged by `due_at` → state `expired`, and the next eligible employee is selected (lazy check run at `/tasks/me` and dispatch time; no background worker).
5. **Tests** (`backend/test_dispatch.py`, TestClient + temp SQLite via an env var for the DB path): TC-29 eligible employee receives a task; TC-30 all busy → 409 plus a "No eligible employee" alert; TC-31 existing task is not double-assigned; TC-32 an expired task is re-dispatched; TC-33 an employee sees only their own tasks and gets 403 on another's transition.

### B3. Insight Narration Agent and report export (FR-17, TC-13) — 2–3 days
1. **Backend:** `POST /reports` `{run}` builds `{metrics, narrative, generated_at, run}`. Metrics come from the summary. The narrative reuses the HF router client in `voice_agent.py` (move its private request helper to a shared `llm_chat(messages)` function in the same file; no new module). The prompt contains only the summary JSON and an instruction to cite each number it uses. If `HF_TOKEN` is unset or the call fails → `narrative=None, mode="metrics_only"` (TC-13 explicit fallback).
2. **Grounding check:** after generation, extract every number in the narrative with a regex and verify that each one appears in the summary (after rounding). If any does not, discard the narrative and fall back to metrics-only. Unit-test this with a fabricated number.
3. **Frontend:** new `frontend/src/app/reports/page.tsx` (add it to `MANAGER_ROUTES` in `RouteAccessGuard.tsx` and to the Navbar). It has a run picker, metric tables and the narrative. "Export PDF" calls `window.print()` with a `@media print` stylesheet in `globals.css` that hides navigation and keeps tables unbroken. Browser print-to-PDF; no PDF dependency.
4. **TC-13:** export a report, open the PDF, check that the selected run's figures appear. Record it in `Report/evidence/`.

### B4. Orchestrator and real system status (FR-19, TC-41) — 1–2 days
1. **Pipeline coordination in application code** (no LangGraph): in `interaction_result()` run, in order: summary present? → `import_run_events` (A3, B1) → optional auto-report (B3) when the setting `autoReport` is on. Record each stage's outcome in a new `agent_runs` table `(id, agent, run, status, started_at, finished_at, detail_json)` created in `store_core.py` next to the other tables.
2. **`/system-status`** (`app.py:740`): replace the hard-coded `workers` dict with, per component (the seven agents plus the detector/tracker/pose tools), the latest `agent_runs` row → `ok | failed | stale (older than 24 h) | never_run`. The CV throughput comes from the latest run's `processed Xs in Ys` line, parsed in `run_script` and saved on the job.
3. **Frontend:** the dashboard's System Status card shows these states; a component that never ran shows "no data" rather than a fake throughput.
4. **TC-41:** a test seeds `ok`, `failed`, stale and missing rows and asserts each status.

### B5. Query Agent (FR-37, TC-34–36) — 2–3 days
1. `POST /query` `{question, run?}` (manager only, read-only).
2. Tool-style dispatch: the LLM (shared `llm_chat`) gets the question plus a fixed JSON schema of supported intents: `metric ∈ {footfall, interactions, approach, unattended, idle, zone_dwell, crowding}`, `zone?`, `from_s?`, `to_s?`. It returns JSON only. Application code computes the answer from the summary (the LLM never computes numbers) and returns `{answer, figures, run, window}`.
3. Ambiguous or unsupported intent, or missing data → `{clarification: "..."}` (TC-35). Without `HF_TOKEN`, a keyword matcher over the same intent list is the fallback.
4. TC-36: anonymous → 401, Employee → 403; assert that no table row counts change after a query.
5. UI: a query box on the dashboard or reports page.

### B6. Remaining page bindings (FR-11/12/13/20/29) — 3 days
1. **Employee pages** (`employee-home`, `my-performance`; FR-13/TC-39): new `GET /me/performance` returns the interactions and idle time of the tracks linked to this `user_id` (B2), plus their own tasks. No linkage → empty state "no linked observations yet". An employee can only ever query their own `user_id` (taken from the actor header, never from the body).
2. **Profile** (FR-20/TC-42): `PATCH /accounts/me` for name and email; password change requires the current password, verified with the existing `authenticate` helper. Duplicate email → 409; a `role` field in the body → 400. Bind `profile/page.tsx`.
3. **Settings consumers** (FR-29/TC-27): the analytics thresholds (A1 config fields) are edited in `settings/page.tsx` and stored with the existing `set_setting("thresholds")`. `/interaction/runs` writes them to a temp JSON passed to `--config` (A1 step 11). Invalid values → 400 and the previous setting kept.
4. **Monitoring** (FR-11/TC-37): camera cards show `online`, `last_frame_at` (from the live preview mtime) and `stale` after 10 s. A camera with no source shows "not configured".

---

## Phase C — Testing, hardening, documentation (report weeks 13–16)

### C1. Execute every planned test case
Write `backend/tests/` TestClient tests where the case can be automated and a dated manual procedure in `Report/evidence/` otherwise:

| TC | How |
|---|---|
| 09, 10, 26 | A4 benchmark on labelled clips |
| 13 | B3 export |
| 27 | B6.3 settings API test |
| 28 | B1 test |
| 29–33 | B2 tests |
| 34–36 | B5 tests |
| 37–39 | B6 tests + manual screenshots |
| 40 | A3 test |
| 41 | B4 test |
| 42 | B6.2 test |
| 43 | run the CLI twice with a fixed config; `summary.json` numbers within 1e-6 (extends TC-25) |
| 44 | count clicks from each landing page to each analytics view (manual table) |
| 45 | screenshots at 375/768/1440 px |
| 46 | C3 |
| 47, 48 | C2 |

### C2. Security and privacy (NFR-07–10, TC-47/48)
1. **Route coverage test:** a pytest walks `app.routes` and asserts every route except `/health` and `/auth/*` has a `require_manager`/`require_employee_or_manager` dependency. A frontend test asserts that every `app/*/page.tsx` directory is listed in exactly one of the route lists in `RouteAccessGuard.tsx` (or in a small public allow-list).
2. The default `INTERNAL_SECRET` (`"local-dev-pos-secret"`) → refuse to start when `RETAILPULSE_ENV=production` and the secret is the default.
3. Path validation review: `resolve_video`, `/analytics/summary`, track crop images.
4. **Privacy:** add a retention setting (days) and a `DELETE` sweep of `backend/output/interaction-runs/*` older than it, run at startup. Store no face crops; track thumbnails (B2) are deleted along with their run. TC-48: inspect the SQLite documents and confirm there are no embeddings or face templates.
5. Run `/security-review` on the branch and fix the findings.

### C3. Performance (NFR-05/06, TC-46)
1. Record the CPU model, RAM and OS in `Report/evidence/env.json`.
2. For each clip, run with `--track-every 1` and `3` and `--judge pose/off`; save the CLI's ×realtime figure (A4 harness).
3. Page timings: `next build && next start`, then Lighthouse or `performance.now()` around the summary fetch on the four analytics pages.

### C4. Documentation and report
Update `README.md` (Future Work section → link to this plan), `docs/fyp2-plan/*`, and the report chapters `Report/chapters/chapter8_testing.tex`, `chapter9_development_evidence.tex`, `chapter10_fyp2_plan.tex`, `appendix_test_cases.tex` with dated evidence. Every TC status changes from Planned to Passed/Failed only with a file in `Report/evidence/`.

---

## Phase D — Out-of-scope future work (after FYP-2 core; ordered by value ÷ effort)

### D1. Cross-camera identity association / camera handoff
Parts that exist: `handoff_core.py` (pure matcher, tested in `test_handoff_core.py`), `camera_handoff.py` (its own detector loop + HSV histogram `appearance_descriptor`), `attach_global_identities`, `IdentityRegistry`, the `/camera/handoff` job and the camera-handoff page.
1. **Camera topology:** a new setting `camera_links: [{from_camera, from_boundary, from_direction, to_camera, to_boundary, to_direction, min_gap_s, max_gap_s}]`, edited in Settings. `HandoffConfig` is built from one link instead of the hard-coded `cam1`/`cam2`.
2. **One detector loop:** `camera_handoff.py` should consume each camera's interaction `detections.json` (same tracker, same `best.pt`, and roles come for free) instead of running its own YOLO loop. Boundary crossings are computed from `center` with the existing `crossing_direction`. Appearance is read from the video only at crossing frames (seek with `cv2.CAP_PROP_POS_FRAMES`).
3. **Better appearance at no new cost:** average the descriptor over the last 5 frames before the exit and the first 5 after the entry, with the upper/lower body halves as separate histograms (shirt vs trousers). Keep the `0.55 appearance + 0.45 time` score; tune the weights on labelled handoffs.
4. **Role constraint:** never match an employee to a customer track (use the `people.json` role); this rules out most false matches cheaply.
5. **Ambiguity stays unresolved:** keep the existing `uncertain` status; the UI shows candidates and a manager can confirm one, which calls `resolve_track(matched_global_person_id=...)`.
6. **Analytics:** for a confirmed global person, merge per-camera summaries so approach time and unattended time are counted store-wide (a customer helped on cam2 is not unattended on cam1).
7. **Upgrade path (new model, only if step 3 fails):** OSNet-x0.25 ReID (≈0.2 M params, runs on CPU through OpenVINO). Accept it only if confirmed-match precision on labelled handoffs improves by at least 10 points.
8. **Evaluation:** label handoff pairs in the A4 specs (`handoffs: [{cam1_track, cam2_track}]`); report confirmed precision, recall and the uncertain rate. Tests: role-constraint and topology cases added to `test_handoff_core.py`.

### D2. Metric floor-plane distance (revive for static cameras only)
It was descoped because the footage came from a moving camera; real store CCTV is static.
1. Recover the prototype: `git show 4a9023a --stat`, then restore the geometry, calibration and quality-gate modules from `4a9023a^..8c3a6fe^` into `backend/interaction/floor/`.
2. Add a camera property `static: bool` and per-camera homography calibration (4+ floor points clicked on a reference frame in Settings; store `H` in the cameras table as JSON).
3. When the camera is static and calibrated, `body_distance` also returns `distance_m` (homography of each person's floor point, D3) and the engagement threshold switches to metres (`interaction_threshold_m=1.5`). Otherwise keep the body-height logic. Mark it in output as `measured_by: "floor_m"`.
4. The quality gate from the prototype (camera-motion check against the reference frame) disables metres automatically when the camera moves.
5. Tests: known-geometry homography (the old TC-17); motion → fallback to body heights.

### D3. Foot/keypoint locator
1. `yolov8n-pose.pt` is already loaded by the pose judge (`pose.py`). When pose has run on a frame, use the mean of the ankle keypoints (15, 16; confidence ≥ 0.5) as the floor point and fall back to the bbox bottom-centre (report eq. 6.1).
2. In `engagement.py`, the feet band uses the ankle y when available. This removes the "fixed bands assume an upright person" shortcut noted in `engagement.py:13`.
3. Cost: pose currently runs only on judged pairs. Running it on every Nth frame is a config flag (`pose_every`), measured in C3.
4. Accept only if the A4 benchmark F1 does not drop and seated-person errors fall.

### D4. 3D reconstruction / per-pixel depth (research spike, new model)
1. Spike: Depth-Anything-V2-Small (ONNX, CPU) on a frame every 2 s of each clip, cached per frame.
2. Use only for relative depth ordering between two people (median depth inside each feet band). It replaces the "box reaches lower = nearer" occlusion heuristic in `_visible_band` and adds a depth-difference veto to `close`.
3. Measure on the A4 benchmark: keep it only if pass-by false positives drop, with the extra cost reported in ×realtime.
4. Full 3D reconstruction stays out: one camera, no calibration, and it gives no analytics benefit. Write this up in the report as a negative result.

### D5. Shelf-level product interaction
1. Config: named shelf polygons per camera (normalised), drawn in Settings like the analytics zones.
2. Detection: a customer's wrist keypoint (pose indices 9, 10) inside a shelf polygon for ≥ `reach_min_s` (1 s) = `reach` event `{track, shelf, from, to}`. A dwell of ≥ 5 s facing the shelf (reuse `pose.head_vector` against the polygon centre) = `browse`.
3. Output: `shelf_events` in `summary.json`; per-shelf reach and browse counts on Spatial Analytics.
4. No product recognition (would need a new model and SKU dataset); state that as the limit.
5. Label reaches on 3 clips; report precision and recall.

### D6. Store layout and promotion effectiveness
1. Persist daily aggregates: a new table `analytics_daily(store_id, date, camera_id, zone, footfall_in, dwell_s, interactions, unattended, reaches)`, filled by `import_run_events` from each run.
2. New tables `layout_changes(id, date, description)` and `promotions(id, zone, start_date, end_date, description)`, with CRUD in Settings.
3. Analysis endpoint `GET /analytics/effect?promotion=`: compares the zone's mean daily dwell, reaches and conversion during the promotion against the same weekdays in the previous 4 weeks. Bootstrap 95% CI with plain `numpy`. Conversion joins POS transactions (`dummydataset/transactions.csv` format) by date and zone.
4. UI: an "Effect" card per promotion with the before/after figures and the CI; "insufficient data" when there are fewer than 7 days on either side.
5. Needs weeks of real footage, so it is only meaningful in the D9 pilot.

### D7. Real-time processing
Parts that exist: live DroidCam path (`/interaction/live`, MJPEG preview), `LiveSource` for RTSP with reconnect (`live.py`), OpenVINO 320 px model, `--track-every`.
1. In `cli.py`'s live loop, every `summary_every_s` (10 s) write `.summary.json` from the detections so far (atomic write + rename, the same pattern as the preview). Cap the in-memory detection list to a rolling window (`deque`, 15 min).
2. `/analytics/summary` already serves the newest file; the dashboard polls every 5 s while a live run is active (or uses the existing `/tasks/events` SSE stub, extended to emit `summary_updated`).
3. A3 imports events incrementally; deterministic ids already make it idempotent.
4. Wire `LiveSource` (RTSP) as a second live input next to DroidCam, using the cameras table `source_url`.
5. Budget: report end-to-end latency (frame time → alert time) in C3 with the target of < 15 s for an unattended alert. Do not claim "real-time" beyond the measured fps.

### D8. Multi-store scaling
1. `validated_store_id` and the store-scoped identity documents already exist. Add `store_id TEXT NOT NULL DEFAULT 'default'` to `zones`, `cameras`, `rosters`, `alerts`, `tasks`, `orchestration_events`, `analytics_daily` with a migration in `store_core.py` (bump `meta.schema_version` to 2; `ALTER TABLE ... ADD COLUMN` guarded by a `PRAGMA table_info` check).
2. Users get a `store_id`; the session cookie carries it; `actor()` adds it; every query adds `WHERE store_id = ?`. One test per table asserts that store A cannot read store B's data.
3. Output under `backend/output/<store_id>/`; per-store settings (thresholds) already sit behind `set_setting`, so key them by store.
4. Deployment shape: one edge box per store runs CV and pushes only `summary.json` and daily aggregates to a central backend (`POST /ingest/summary` with a per-store API key). No video leaves the store. An owner role gets a cross-store dashboard.
5. SQLite is fine per edge box; the central backend moves to Postgres when there are more than ~10 stores.

### D9. Pilot with a real retail partner (non-code, with deliverables)
1. Partner agreement and data-protection pack: purpose, camera signage text, retention (C2.4), no faces or biometrics, access list.
2. Install guide: edge box spec (C3 env), `npm run build && npm start`, the uvicorn service, RTSP setup, calibration checklist (zones, entrance line, `camera_links`, store thresholds).
3. Two weeks of shadow mode (alerts on, dispatch paused through the existing `dispatchPaused` setting), then two weeks live.
4. Success metrics agreed up front: unattended alert precision ≥ 0.8 on spot-checked samples, manager usefulness survey, and the change in mean approach time.
5. Weekly feedback log; threshold changes recorded as settings history.

---

## Timeline
| Weeks | Work |
|---|---|
| 1–3 | A0, A1, start A4 labelling |
| 4–6 | A2, A3, B1, B2 |
| 7–9 | B3, B4, B5, B6 |
| 10–12 | A4 evaluation and tuning, D3 (cheap and improves A4) |
| 13–14 | C1, C2, C3 |
| 15–16 | C4, final demonstration |
| Post-FYP | D1 → D7 → D2 → D5 → D8 → D6 → D9; D4 as a spike when time allows |

## Verification (end to end)
1. `python -m pytest backend -q` (all existing 44 tests plus the new ones) and `npm run lint && npm run build`.
2. `npm run dev:all` → log in as Manager → Interactions: run `ShopAssistant1cor.mp4` → Dashboard, Customer Info, Employee Info and Spatial Analytics show that run's numbers; Alerts shows its unattended events; Employee Home (as an employee) shows the dispatched task; Reports exports a PDF; the query box answers "how many customers waited unattended?" with a cited figure.
3. `python -m backend.interaction.benchmark` on all 11 specs gives the held-out with/without-judge table.
4. Route-coverage and store-isolation tests pass; `/security-review` is clean.
5. For each Phase D item, its own "accept only if" benchmark criterion is recorded in `backend/interaction/benchmarks/`.
