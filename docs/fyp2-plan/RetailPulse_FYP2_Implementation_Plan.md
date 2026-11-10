# RetailPulse FYP-2 — combined implementation plan

Updated 11 November 2026. This is the current team plan, reconciling Saqib's 10 November status snapshot, the agreed member allocation, the current checkout and the user's four live-category decision. Its tracked copy lives in docs/fyp2-plan/; local extra-docs copies are ignored and must not be the only teammate reference.

## Priority and source reconciliation

1. Current direct user decisions govern workflow and the four live occupancy categories.
2. The existing Moiz/Ruhab/Saqib allocation and seven-agent architecture below remain authoritative. Member 2/Member 3 in Saqib's snapshot are historical labels, not new owners.
3. Saqib's status is evidence of work on his branch, not proof it is integrated here. His statements that backend/agents does not exist and that tools/graph have not started are outdated for fyp2-moiz. Moiz's four foundation phases are implemented and offline tested (139 passed, 1 missing-real-output skip in the last recorded run).
4. Preserve report/evaluation evidence without overstating it: no benchmarks, model adoption, merges or report edits are performed by this documentation reconciliation.

## Unchanged ownership and architecture


The original 16-week work and schedules are retained below, with ownership updated to match the team table. Where the table does not reassign a task, the source plan’s Member 2 is mapped to Moiz Ansari and Member 3 to Ruhab Ahmad based on their roles.

| Milestone | Moiz Ansari | Saqib Atif | Ruhab Ahmad |
| --- | --- | --- | --- |
| Mid-1 | Manager frontend; Footfall Agent | Backend and CV pipeline: detection, tracking and depth estimation | Employee frontend; documentation; presentation |
| Final-1 | Customer–Employee Interaction Agent | Backend pipeline integration and agent data feeds | Employee Activity Agent; model fine-tuning; documentation |
| Mid-2 | Dashboard analytics, data visualization and LangGraph orchestration | Staffing & Task Assignment Agent integration | Manager dashboard and employee interface refinement; Customer Behavior Agent; documentation |
| Final-2 | Full frontend integration; agent-output-to-UI integration testing | Full backend/AI integration and deployment | QA, documentation, client acceptance testing and agent output validation |

The table records responsibilities across milestones, including past work. The Interaction Agent is complete as reported by the team; its data integration, evaluation and UI binding remain in the plan. The Mid-1 depth-estimation entry records ownership and does not reopen the descoped metric floor-calibration prototype.

### Finalized architecture and ownership

| Component | Owner | Role |
| --- | --- | --- |
| Customer Behavior Agent | Ruhab | Footfall summaries, paths, dwell and hot/gray zones; consumes Moiz’s footfall implementation and Saqib’s CV feeds |
| Employee Activity Agent | Ruhab | Staff activity, availability and coverage; corresponds to Employee/Coverage below |
| Interaction Agent | Moiz | Completed customer–employee interaction detection; Saqib owns the backend data feed |
| Employee Task Assignment Agent | Saqib | Staffing integration, direct aisle assignments and dispatch voice integration |
| Insight Narration Agent | Ruhab | Evidence-based summaries and digest |
| Query Agent | Moiz | Authorized analytics questions and evidence |
| Orchestrator | Moiz | LangGraph routing, shared state, grounding and traces |

Classification, tracking and zone identification are shared tools. Anomaly Investigation, next-day Staffing Planner and Clip Review remain supporting capabilities with their original owners. All original reasoning and operational workstreams are retained.

**Direct aisle assignments do not require manager approval or a manager-enabled auto mode.** The existing approval node and inbox remain planned for separate actions such as next-day schedule changes. Next-day planning and direct aisle dispatch are distinct.


## Agreed workflow and the ONLY four live categories

**Camera connection/recorded-video input → CV detection, tracking, customer/employee classification and interaction events → supply/register the store map → project usable observations onto that map → customer/employee occupancy and confirmed-interaction heatmaps → agents/dashboard → separately authorized real operational integration.** Fixtures allow parallel tool/UI work; they do not prove this real-data flow is complete.

The four labels describe changing occupancy in observed map locations, NOT fixed permissions, staff-only areas or permanently assigned customer polygons:

| Category | Proposed storage label (not implemented yet) | Meaning in the chosen observation window |
|---|---|---|
| Customer | customer | Customer presence observed; no employee presence observed with sufficient coverage |
| Employee | employee | Employee presence observed; no customer presence observed with sufficient coverage |
| Customer–employee both | customer_employee | Both roles present; this alone does NOT prove an interaction |
| No one | no_one | Observed empty with sufficient healthy coverage; never inferred from missing data |

Only assert an exclusive/empty category when role and coverage evidence are sufficient; otherwise mask classification rather than force a category. Unknown remains a CV role/quality label, not a spatial category. There is no fifth zone type. Missing/stale/blocked views, unknown roles and unmapped observations use separate validity/quality metadata and an unavailable overlay/mask, not a new zone category and not No one. Historic z1–z6 IDs, floor polygons, entrance lines and counter/queue geometry are implementation/fixture references, not additional approved product categories. Do not silently recategorize those fixtures or migrate schemas without a separately authorized implementation.

Keep stable map-location/region identifiers separate from the changing category attribute; do not turn existing zone_id authorization keys into role labels or change access as people move. The four categories are the only classification vocabulary, not a reason to silently rewrite camera/run/fixture identities. Representation and migrations remain planned, not implemented.

The supplied map is a spatial reference, not evidence that metre/feet distances are calibrated. Agree camera-to-map registration, visible area, coordinate transforms, overlap handling, aggregation window, smoothing/hysteresis and role-confidence handling before implementation. Registration must be configuration/version driven; metric homography/depth remains separate deferred work. A cell/region can change category as people move. Customer/employee counts or occupancy-time and confirmed interaction count/duration are separate heatmap layers, not zone types. Show which quantity/unit/window a heatmap represents; image-grid counts are not metric floor density or deduplicated people. Co-presence is not confirmed assistance; default interaction statistics use verdict=interaction and disclose unverified separately.

## Current evidence and branch availability

| Work | Current status / evidence | Next action |
|---|---|---|
| B0 event store, B4 signal producers (Saqib) | Present in integrated 44b0c00 baseline; schema/fixture/ingestion/zone/health/queue code reused; focused event regressions passed previously | Verify camera configuration and actual ingestion; adapt real map integration, not a second event schema |
| B1 interaction labels | This checkout: 11 tuning clips / 13 interactions, 14 set-B clips / 17 interactions. Saqib reports 25 reviewed role clips and 109/113 matched tracks elsewhere | Reconcile role branch/artifacts and second-review provenance. Local set-B pass_bys list totals 9; Saqib reports 10. Audit that discrepancy before quoting totals |
| B2 interaction evaluation | Local merged reports: tuned F1 0.867 (13/4/0); set-B F1 0.462, P 0.409, R 0.529 (9/13/8); proximity F1 0.429 | Retain set-B once-seen-during-tuning caveat, blind checks, pause convention, tracking error analysis and clean idle CPU/GPU timing |
| B3 role refit | Saqib reports completed code/results at d6783b2 and uncommitted fitted/random-6 artifacts. That commit and role_labels.py are absent here | Saqib publishes exact branch/artifacts for normal review; Ruhab retains fine-tuning/validation ownership. Do not mark local adoption complete or change defaults without user/team decision |
| B4 map readiness | Producers exist; no verified real camera polygons/map registration supplied. Generic heatmaps currently aggregate foot points, not the new role-separated live-category map | Camera-first validation, then supplied-map registration/configuration and live role/interaction layers |
| B5 handoff | Evaluator present; labelled crossings/evaluation absent | Saqib stretch task, not a prerequisite for the core single-camera map demo |
| B6 CV chapter | Skeleton with TODOs | Ruhab documents Saqib's exact reproducible results later; do not edit Report in this task |
| Moiz M-P1–M-P4 | Typed five-tool layer, scoped registry, grounded callable LangGraph, dev traces, isolated fake-only operational adapter implemented; latest foundation suite 139 passed / 1 skipped | Real auth/store/config binding, wider tools, Query/evaluation and frontend integration remain |
| Frontend deployment | Root Vercel configuration and local Next 15.5.25 production build verified; user subsequently confirmed deployment works | Record user-confirmed cloud success; independently verify backend/login/live data connectivity before claiming full deployment |
| Real business agents / dispatch / UI flow | Interfaces and fake demonstrations exist, not real agent/operational acceptance | Ruhab business agents and policy; Saqib actual assignment/idempotency/voice; Moiz binding and graph integration |

Saqib's refit/random-6/100% role figures are reported branch results, not newly verified local measurements. Absent reference/staff-zone factors mean not observed, not useless. Do not introduce those fixed-area labels into the new live category model. Contended 0.07–0.23× speed figures are invalid; 0.87× is reported clean speed, not rerun here. Random-six label provenance still needs confirmation.

## Next developer queue (owners retained)

| Key / order | Owner | Work and handoff / acceptance |
|---|---|---|
| MAP-1: camera/CV first | Saqib | Connect/configure real video or camera; stable timestamps, camera/store/run IDs, roles, confirmed/unverified interactions and health into existing event store; supply reproducible run/weights/config. No new model required |
| MAP-2: map registration | Saqib CV/backend; Moiz data/UI binding; Ruhab refinement/QA | Accept supplied map, version camera-to-map alignment/coverage and map-cell conventions; handle unmapped/overlapping views. Demonstrate one static camera before multi-camera expansion; no implied metric accuracy |
| MAP-3: dynamic categories/layers | Ruhab business semantics; Saqib spatial/event feeds; Moiz typed readers and rendering | Implement exactly the four live categories plus separate validity metadata. Customer/employee occupancy-time or counts and confirmed-interaction layers need units/window/evidence. Test transitions, co-presence without interaction, occlusion, unknown role, blocked feed and empty observed space |
| M-REAL-BINDING | Moiz with Saqib backend/auth | Bind authoritative actor/store/configuration; expose graph routes only after auth. Wire dashboard, Ask panel, citations/traces and stale/partial states; keep fixture mode labelled and replaceable |
| M-WIDER-EVAL | Moiz | Queue/health/alerts tools, complete Query/supporting Anomaly/next-day planning, 50+ golden questions and grounding ablation, routing/refusals/latency/cost. POS and arbitrary SQL remain excluded/deferred |
| R-AGENTS | Ruhab | Actual Customer Behavior / Employee Activity logic and event emission policy using four-category map layers; no new zone classes. Insight Narration/Digest/Clip Review and interface refinement retain ownership |
| S-OPERATIONS | Saqib; Moiz adapter support | Plug real handler into operational.py; stable event/store/key, atomic dedup/key conflicts, employee/account/roster/source-zone safety, persistence, voice/acknowledgement. Direct aisle dispatch has no manager approval/auto-mode requirement |
| CV-REVIEW | Saqib evidence; Ruhab tuning/validation/docs | Publish missing role artifacts; decide fitted adoption with user/team; blind recheck IMG_8838 p2 and IMG_8830; define 4–6s gap convention; second annotator for tuning set; fix ID switches without tuning set B again; collect clean speed and provenance |
| TEAM-CI | Ruhab coordination; Saqib Python; Moiz frontend | Agree integrated branch and review plan; CI fast/slow test separation, Python checks/build/lint and actual branch protection. Do not assume main protection exists; no merge/push in this docs task |
| TEAM-ACCEPTANCE | Ruhab lead; both supply evidence | Real footage → map/live categories/layers → business event → eligible employee update → manager result, plus no-eligible and duplicate cases. Fake receipts and static frontend deployment are not end-to-end acceptance |

## Evaluation/checkpoint reconciliation

The original week-1 date is 3 November 2026. Retain the team's 16-week schedule as a plan, not proof of delivery. Week 2: schema and signatures exist on the inspected foundation branch; integrated CI still needs verification. Week 6: label/benchmark artifacts exist and fixture tools run, but real map pages remain pending. Week 10: gate is real CV/map/agent flow and direct eligible assignment, NOT an approval inbox for aisle dispatch. Week 13: measured CV/golden-agent/dispatch-scenario results and real-data pages. Week 15: rehearsed demo, version freeze and no open P1 defects.

Zone-dwell annotations were deferred/dropped in Saqib's old snapshot because geometry was absent; do not pretend they are complete. With map analytics now central, the team must collect appropriate map/category/dwell/interaction ground truth for the configured camera and selected time windows. Loss prevention and POS analytics remain out of scope. Broader research/stretch tasks remain in FUTURE_WORK.md; they cannot silently add product zone categories or agents.

## Resume instructions

### Parallel dashboard provider/binding queue (Moiz)

- **M-UI-P1 implemented:** `frontend/src/lib/analytics-provider/` contains a typed provider/snapshot boundary with runtime validation, freshness and null-aware metrics plus five hand-authored synthetic presentation scenarios. Strict compilation/16 offline tests, full frontend typecheck, targeted lint and the legacy data regression passed. Existing backend tool/evidence semantics retained; no page or event-schema changes.
- **M-UI-P2 implemented:** dashboard now binds the provider with labelled synthetic scenarios, eight supported aggregate metrics, evidence/limitations, loading/observed-empty/partial/unavailable/stale presentation and safe refresh/cancel/cache expiry. Fabricated comparison-derived metrics, interaction rows and decorative map claims removed from the dashboard; recorded clip is labelled, Ask disabled and unsupported detail/map data explicitly unavailable. 27 tests, frontend lint/typecheck/build and isolated Chrome scenario/refresh/route/mobile checks passed. Ruhab retains refinement/QA; this does not complete real-data integration.
- **M-UI-P3 connection implemented / real acceptance pending:** backend provider and scoped dashboard routes reuse existing five tools; active Manager ID/email and explicit server-owned store/run/camera/region membership/config gate reads. Default source is Configured backend; fixtures remain an explicit choice. 155 backend tests/1 existing skip, 34 frontend checks, lint/typecheck/build and synthetic actual-login browser flow passed. Saqib must supply/adopt verified real bindings/context/feed/deployment; Ruhab retains actual business outputs/refinement/QA. Backend failures remain unavailable. No real source config, PostgreSQL migration, Query graph HTTP/durable traces, map layers or dispatch is installed by this task.

These UI phase numbers are separate from completed tool/graph M-P1–M-P4. M-UI-P1/P2/P3 connection code is implemented; current work stops after Phase 3. Camera/map order, four live categories and seven agents remain unchanged. Shared setup/contract and runnable checks are in DASHBOARD_BACKEND_SETUP.md/CONTRACTS.md/PROGRESS.md; ignored assistant notes are not required on teammate clones. Synthetic end-to-end UI evidence does not close live CV/agent/deployed acceptance.

Read this tracked plan, PROGRESS.md, PENDING.md, CONTRACTS.md and CHECKLIST.md first; inspect the actual current branch/code before changing checkboxes. Use Saqib's source note as historical reported evidence, not instructions to push/merge/train or reassign members. No file in ignored extra-docs is guaranteed on a teammate clone. Current next implementation starts at MAP-1 and proceeds through MAP-2/MAP-3, while Moiz's fixture-backed UI/Query evaluation can continue in parallel. Production auth/dispatch and real agent acceptance are explicitly still pending.

## Additional Saqib evidence and follow-up retained

These are the Nov-10 source snapshot's measurements/claims, not a new benchmark run:

| Evidence | Value / caveat |
|---|---|
| Setup | COCO tracking plus best.pt role labels; torso-colour relink and per-store role calibration already reported/implemented, not new models requested |
| Detector | Reported best_320 OpenVINO on 455 images: mAP50 0.969, mAP50–95 0.896, P 0.963, R 0.953, 88 ms/image; role-report artifact cited by Saqib is not present here |
| Set-B timing | Local merged report start error about 1.16 s, end error 2.93 s; temporal one-to-one matching IoU >= 0.5 |
| Refitting | Reported hand-set leave-one-clip-out 0.960 tuning / 0.915 B; fitted 1.000 both; fit on tuning and score B 59/59. Candidate weights 0.61 YOLO / 0.36 bib / 0.03 stationary, reference/staff-zone 0, threshold 0.094. Unobserved factors and small two-camera sample prevent a general accuracy claim; adoption remains open |
| Random-six | Reported F1 0.737, 7/5/0 with hand/fitted roles; role-flip rate 1.34 vs 1.17/min; role accuracy 0.963 on 27 tracks. Reports and label provenance need publication/verification |
| Tracking | Reported ID switches 1.8/min B, 2.3/min random-six; role report B 1.000 on 59 tracks is branch evidence, not local model adoption |
| Error taxonomy | Saqib reports 13 FPs: 4 overlong, 4 ID-switch duplicates, 5 without nearby labels (2 suspected missed annotations). Six of eight misses arise from long spans covering multiple short labels. Blind checks and gap convention precede any correction; estimated improved F1 is not an accepted result |

Carry forward clean CPU speed at track-every 1/3, optional available GPU throughput, confidence intervals, more independently reviewed/staged data, slow-test marking, version/model freeze by week 14 and agent freeze by week 15. The source's 20-minute/76-test interaction-suite timing is reported historical runtime, not a promise about this checkout or the fast 139-test scoped suite. Keep report chapter TODOs linked to exact commands/artifacts; Ruhab owns documentation and Saqib supplies CV evidence.

Checkpoint dates from the original Nov-3 week-1 plan remain tentative: week 2 Nov 10–16, week 6 Dec 8–14, week 10 Jan 5–11, week 13 Jan 26–Feb 1 and week 15 Feb 9–15. They are not newly confirmed supervisor deadlines. Source references to Claude Memory/CVAT private notes are not teammate-accessible evidence until published in the shared docs. No push, PR, merge or fitted-default change is performed just because the source snapshot recommends one.
