# Legacy workstream detail — reference only

Superseded where it conflicts with [the combined plan](RetailPulse_FYP2_Implementation_Plan.md). This retains technical detail from the prior local team plan; old fixed zones, POS, model names, scheduling and stale checkboxes are not current authorization or requirements. Current ownership, seven agents and four dynamic categories govern.

# RetailPulse FYP-2 Implementation Plans

Nov 3, 2026 · @Saqib

## Overview

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

## Member work and added pending tasks

### Moiz Ansari

**Original work:** A1 tools; A2 orchestration; A3 Query, Anomaly Investigation and next-day Staffing Planner; A4 agent evaluation; A5 agent integration; B4 Footfall Agent logic; C1 frontend integration; C2 dashboard analytics, visualization, data binding and Ask RetailPulse; C6 final frontend integration. The milestone table also assigns the manager interface and completed Interaction Agent.

**Added pending work:**

- [ ] Validate entry/exit direction and deduplicate repeated crossings. Provide hourly/daily footfall; show current occupancy only when an initial count and sufficient entrance coverage are available.
- [ ] Finish binding real agent outputs to the frontend, including completed interaction results and the employee task-status outcome on the manager side. Distinguish unavailable or stale data from zero.
- [ ] Run frontend integration testing on the full workflow: footage creates a hot-aisle signal, the employee receives and updates one task, and the manager sees the result. Coordinate the backend negative case with Saqib and acceptance evidence with Ruhab.

### Saqib Atif

**Original work:** B0 event store and ingestion; B1 labelling and split audit; B2 CV evaluation; B4 CV signal production and data feeds, including wiring Moiz’s footfall output; B5 camera handoff; B6 model freeze and benchmark evidence; C1 backend/AI integration; C3 task assignment and voice; C6 inference performance and deployment. Supply labelled factors and validation results to Ruhab for fine-tuning and documentation.

**Added pending work:**

- [ ] Verify real zone demand reaches the existing dispatch endpoint automatically. Reuse task and alert records, enforce roster/availability and coverage rules, prevent duplicate tasks on repeated events, and verify no task is sent if no employee is eligible. No manager approval for direct aisle assignments.
- [ ] Validate all three cameras on stable footage: camera-to-zone mappings, timestamps and duplicate observations where views overlap. Reuse the existing handoff experiment as needed, without making full multi-camera Re-ID a release requirement.
- [ ] Document the exact dataset/split, model weights, configuration, event schema and run commands that reproduce the demo. Supply them to Ruhab for the report. Automate retraining only if already committed in scope.

### Ruhab Ahmad

**Original work:** A3 Customer Behavior and Employee Activity; B1/B3 model fine-tuning; C1 CI coordination; C2 manager and employee interface refinement; C4 Insight Narration and Digest; C5 Clip Review; C6 security review, demo script and report. Own documentation, presentation, QA, client acceptance and agent output validation. Moiz and Saqib supply their technical results.

**Added pending work:**

- [ ] Complete real customer behavior outputs, including hot/gray zones from occupancy and dwell. Distinguish poor observation coverage from low activity. Complete staff availability/coverage using roster, active tasks and confirmed interactions, leaving ambiguous activity unknown.
- [ ] Validate Query and Narration outputs against stored metrics and cited evidence, including missing or partial data. Check the digest/PDF against the same run.
- [ ] Run and capture client acceptance for both the real footage → direct assignment → employee update → manager result flow and the no-eligible-employee case. Record evidence and limitations against the exact configuration and model versions.

## Detailed implementation work

### Shared contracts (agree in week 1, all three)

1. **Event schema v1.** Tables: `tracks`, `role_decisions`, `interactions`, `zone_dwell`, `footfall`, `queue_samples`, `unattended_episodes`, `pipeline_health`. Every row carries `store_id`, `camera_id`, `zone_id`, `ts_start`, `ts_end`, `run_id` and a stable `event_id`.
2. **Evidence format.** Every agent claim cites `{source: table, ids: [...], query: name}`. The UI renders these as links to the event trail.
3. **Tool signatures.** Moiz publishes the tool list (name, params, return shape) by end of week 2. Moiz builds UI calls against it; Ruhab refines the interfaces; Saqib makes sure the CV writer fills every field the tools read.
4. **Fixtures.** A seeded SQLite file with a synthetic day of events. Agents and UI develop against it until real CV output arrives.
5. **Branch policy.** `main` is protected. Work goes in short-lived feature branches merged by PR with tests passing. The five `interaction-*` branches are retired after the merge.

### Dependency order

CV stages write events into the event store (Saqib) → tools expose them (Moiz) → agents reason over tools (Moiz, Ruhab, Saqib) → the dashboard shows results and applicable approvals (Moiz binds the data; Ruhab refines the UI). Fixtures break this chain during weeks 1 to 6, so nobody waits on anybody.

## Plan A: Tools, orchestration and reasoning

Moiz owns the tool layer and LangGraph orchestration. Moiz and Ruhab split the five original reasoning workstreams as marked below. This is the part the panel will probe hardest, because it carries the "agentic" claim in the title.

### Dependency on Plan B

The event store, ingestion and synthetic fixtures are built in Plan B (section B0). Until the store is ready in week 3, build the tools against the fixture file Saqib ships at the end of week 2.

### A1. Tool layer (weeks 2–4)

**Owner:** Moiz.

Agents never write SQL against production tables. They call typed, read-only Python functions with Pydantic inputs and outputs. Each result carries its evidence IDs.

| Tool | Returns |
| --- | --- |
| `get_footfall(window, granularity)` | Entries per bucket |
| `get_zone_dwell(zone, window)` | Dwell distribution, p50/p90, counts |
| `get_interactions(window, zone?)` | Count, duration stats, response-time stats |
| `get_unattended(window, zone?, min_seconds)` | Episodes with evidence IDs |
| `get_coverage(window, zone?, shift?)` | Staffed minutes vs open minutes per zone |
| `get_queue(window, counter?)` | Queue length and estimated wait |
| `get_pos_sales(window, category?)` | Reuses the POS pillar's metrics |
| `get_alerts(window, status?)` | Alerts with linked events |
| `get_pipeline_health(window)` | Drift and health metrics from Saqib’s CV pipeline |
| `run_readonly_sql(query)` | NL Query only, on a read-only connection with a row cap |

- [ ] Publish the signatures by end of week 2 (shared contract 3).
- [ ] Write tests that compare each tool against a hand-written SQL answer on the fixture.

### A2. LangGraph supervisor (weeks 4–6)

**Owner:** Moiz.

- [ ] Add `langgraph` to requirements and build `backend/agents/graph.py`: a supervisor node that classifies the request, then routes to one or more specialist nodes.
- [ ] Define shared state: request, role (manager/employee), time window, tool results, draft answer, citations, pending actions.
- [ ] Add a **grounding node** after every specialist. It checks that each number in the draft appears in a tool result, and sends the draft back once if not.
- [ ] Add an **approval node**: approval-required actions (such as schedule changes) become pending actions the manager approves in the UI. Moiz binds the UI and Ruhab refines it. Direct aisle dispatch bypasses this node.
- [ ] Model choice: keep the existing HF router (Qwen2.5-7B) as the default with an env switch for a stronger API model. Log tokens and latency per node.
- [ ] Expose `POST /agents/ask` and `GET /agents/runs/{id}` (trace of nodes, tools, citations).
- [ ] Fix the README: LangGraph is used here, and the CV steps are called pipeline stages, not agents.

### A3. Reasoning agents (weeks 6–11)

Build in this order. Each workstream is a LangGraph node with a system prompt, an allowed tool subset and 5+ golden questions before it counts as done. Supporting nodes do not expand the finalized top-level agent list.

1. **Owner: Ruhab.** **Customer Behavior Agent (weeks 6–7).** Tools: footfall, dwell, interactions, unattended, POS. Outputs behavior segments by zone and time (quick visits, browsing, lingering without help), friction points, and zone-level links to POS. Never per-person.
2. **Owner: Ruhab.** **Employee/Coverage Agent (weeks 7–8).** Tools: coverage, interactions, unattended, alerts. Outputs coverage gaps, response-time patterns and explanations of score changes, aggregated by zone and shift. Its prompt forbids ranking individuals; the output is advisory.
3. **Owner: Moiz.** **NL Query Agent (weeks 8–9).** Tries the typed tools first and falls back to `run_readonly_sql` against a documented schema. Returns the answer, the query used and the rows it rests on.
4. **Owner: Moiz.** **Anomaly Investigation Agent (weeks 9–10).** Triggered by an alert ID. Pulls events in a window around it, checks coverage, queue and pipeline health, and returns a ranked list of likely causes with evidence. It must say "pipeline issue" when health metrics explain the alert.
5. **Owner: Moiz.** **Staffing Planner (weeks 10–11).** Combines footfall forecasts (reusing the POS forecasting code), coverage history and the roster to propose a zone/shift plan for the next day. The proposal goes through the approval node; nothing changes automatically.

### A4. Agent evaluation (weeks 11–13)

**Owner:** Moiz leads evaluation; Ruhab owns report documentation and acceptance validation.

- [ ] Build a golden set of 50+ questions across the five agents, each with a SQL-derived ground-truth answer.
- [ ] Measure numeric accuracy (within tolerance), grounded-claim rate (claims with a valid citation), routing accuracy for the supervisor, refusals on out-of-scope questions (identity, theft), and latency and token cost per question.
- [ ] Run a with/without grounding-node ablation; this is the strongest defense table.
- [ ] Ruhab writes the agent architecture and evaluation chapters using Moiz’s results.

### A5. Buffer and integration (weeks 13–16)

**Owner:** Moiz.

Swap fixtures for real CV output, fix the gaps that exposes, support Ruhab on the demo and freeze the agent code by week 15.

**Done means:** all five original reasoning workstreams callable through the finalized architecture from the dashboard on real events, every numeric claim cited, and an evaluation table in the report.

## Plan B: Saqib (CV signals and evaluation)

Saqib turns the existing interaction module into measured, trustworthy signals, and owns the event store they land in. The work builds on the existing code, and the evaluation numbers it produces are what the panel will check first.

### B0. Event store and ingestion (weeks 1–3)

**Owner:** Saqib.

- [ ] Write `backend/events/schema.sql` for the eight tables in schema v1, with indexes on `(store_id, zone_id, ts_start)`.
- [ ] Build `backend/events/ingest.py` to load a CV run (`people.json`, `interactions.json`, `detections.json`) into the store, idempotent on `run_id`.
- [ ] Derive `unattended_episodes` deterministically: a customer dwelling over N seconds with no confirmed interaction. N comes from the settings thresholds already in `app.py`.
- [ ] Ship the synthetic fixture generator by end of week 2: one store, 3 cameras, 6 zones, 12 hours, with seeded patterns (a 5–7pm rush, one understaffed zone, one blocked camera) so agents have something to find.
- [ ] Add a CI contract test that validates any CV run against schema v1, plus unit tests for ingestion and episode derivation.

### B1. Labelling and honest splits (weeks 1–3)

**Owner:** Saqib leads labelling and split audit; Ruhab owns any required retraining.

- [ ] Label the ten waiting clips using `ANNOTATION_GUIDE.md`: role per track, interaction start/end, and close pass-bys that are not assistance. Aim for at least 30 interactions and 15 pass-bys in total.
- [ ] Label zone dwell on 3 clips (person, zone, enter/exit time) for the trajectory evaluation.
- [ ] Check the detector test split: if test frames share videos with training frames, re-split by video (Saqib) and retrain (Ruhab). Report both numbers if they differ.

### B2. Stage evaluation (weeks 3–5)

**Owner:** Saqib.

- [ ] Extend `benchmark.py` to run all labelled clips and report precision, recall and F1 for interactions, proximity-only vs with pose judge.
- [ ] Add start/end timing error, role accuracy per track, and ID switches per minute.
- [ ] Record CPU throughput (realtime factor) and, if the RTX 5060 laptop is available, GPU throughput with `USE_GPU = True`.
- [ ] Write an error analysis: 5–10 failure cases with frames and the reason each failed.

### B3. Role-weight refit (weeks 5–6)

**Owner:** Ruhab, with Saqib providing CV evidence.

The current weights (0.55 / 0.30 / 0.10 / 0.05, threshold 0.45) are hand-set.

- [ ] Fit a logistic regression on the per-track factors from the labelled clips, with cross-validation by clip.
- [ ] Compare hand-set vs fitted weights on held-out clips and keep whichever wins, with the table as justification.
- [ ] Add a threshold sweep plot (precision and recall vs threshold) for the report.

### B4. New signals into the event store (weeks 6–10)

**Owner:** Saqib leads CV/data feeds; Moiz owns Footfall Agent logic.

1. **Event writer (week 6).** Make the CLI and live mode write directly into schema v1 through the B0 ingestion function, filling `zone_id` and `camera_id` on every row.
2. **Zones and dwell (weeks 7–8).** Use the zones from `/settings/zones` to compute per-track zone dwell and transitions. Generate heatmap grids per camera per hour.
3. **Footfall (week 8; Moiz owns crossing logic, Saqib integrates its event feed).** Directional line crossing on the entrance camera, reusing the boundary logic from `handoff_core.py`.
4. **Queue length (week 9).** Use the existing `queue_temp` calibration: count people inside the queue polygon every N seconds, and estimate wait from the counter's interaction durations.
5. **Pipeline health (week 10).** Per camera per minute: frame rate, mean detection confidence, share of tracks with "unknown" role, ID churn, and a frozen-or-dark frame check. These feed `pipeline_health` and the Anomaly agent.

### B5. Camera handoff (weeks 10–12, stretch)

**Owner:** Saqib.

The two-camera handoff already exists as an experiment. Evaluate it on labelled crossings and report confirmed, uncertain and unmatched rates. Writing `master_id` into `tracks` is a bonus; it is not on the critical path.

### B6. Report and freeze (weeks 12–16)

**Owner:** Saqib handles model freeze; Ruhab writes the report.

Ruhab writes the CV evaluation chapter from Saqib’s results. Saqib freezes the models by week 14 and supports Ruhab’s demo footage selection.

**Done means:** every stage has measured numbers on labelled clips, the role weights are justified, and zones, footfall, queue and health signals land in the event store.

## Plan C: Integration, dashboard and operational capabilities

The team makes the system one working product: a single codebase, real data on screen, and the agents that act on the floor. Most of it extends things that already exist: dispatch, the voice agent and the alerts page.

### C1. Branch merge and CI (weeks 1–2)

Keep one integrated `main` with POS and interaction, CI tests, and run scripts. Saqib owns backend/AI run scripts; Moiz owns frontend run integration.

**Owner:** Saqib leads backend/AI merge and Python fixes; Moiz handles frontend build and integration; Ruhab coordinates CI and README structure updates.

- [ ] Merge `feature/interaction` into `main`, restoring the POS routes (`/pos/*`) that this branch lacks. Fold in or close `interaction-factors`, `interaction-flag`, `interaction-live`, `interaction-optimization` and `fyp2-a0-tracker-tuning`.
- [ ] Fix the relative-import errors so tests pass from both the repo root and `backend/`.
- [ ] Add a GitHub Actions workflow: Python tests, `npm run build` and lint on every PR.
- [ ] Update the README project structure, which no longer matches the repo.

### C2. Dashboard binding (weeks 3–8)

**Owner:** Moiz owns data binding, visualization and UI integration; Ruhab owns manager and employee interface refinement.

Bind one page at a time to the event store, keeping prototype data as a fallback behind a flag.

| Week | Page | Data source |
| --- | --- | --- |
| 3 | System Status | `pipeline_health`, agent run traces |
| 4 | Dashboard | Live interaction stream, footfall |
| 5 | Customer Info | Dwell, interactions, unattended episodes |
| 6 | Employee Info, My Performance | Coverage and response time by zone/shift |
| 7 | Spatial Analytics | Heatmap grids, zone transitions |
| 8 | Alerts | Real alerts with an evidence trail |

- [ ] Add an **Ask RetailPulse** panel that calls `POST /agents/ask` and renders citations as clickable links to events.
- [ ] Add an **Approvals** inbox for pending actions from Moiz’s approval node, excluding direct aisle dispatch.
- [ ] Replace the per-employee leaderboard with zone/shift views, or label scores as advisory with a "contest this" action. Agree the choice with the team in week 6.

### C3. Dispatch Agent with voice (weeks 8–10)

**Owner:** Saqib leads dispatch; Moiz supports graph integration; Ruhab validates outputs in acceptance QA.

Upgrade `/orchestrator/events` from "first available employee" to a LangGraph node in Moiz's graph.

- [ ] Inputs: the alert, zone adjacency (from zone settings), who is mid-interaction (from `interactions`), current tasks and the roster.
- [ ] Output: a ranked choice with a one-line reason, sent directly to the eligible employee for aisle dispatch. The approval inbox remains for separate approval-required actions; aisle dispatch requires no auto-mode switch.
- [ ] Keep the old rule as a fallback when the LLM fails or times out.
- [ ] Connect the existing `voice_agent.py` so the chosen employee hears the instruction; log acknowledgement time.
- [ ] Evaluate on 20 scripted scenarios against a human rater's choice.

### C4. Insight Narration and Digest (weeks 10–11)

**Owner:** Ruhab.

- [ ] Narration node: turns a page's data into a 3–5 sentence summary with citations, shown at the top of each analytics page.
- [ ] Digest: an end-of-day report built from narration plus the day's alerts, exported with the existing jsPDF report builder.

### C5. Clip Review (weeks 11–12)

**Owner:** Ruhab.

- [ ] For each alert, cut a 10–20 second clip around the evidence timestamps from the raw recordings and attach it to the alert.
- [ ] Draw the relevant track boxes on the clip so the manager can verify the alert in seconds.

### C6. Hardening and demo (weeks 13–16)

**Owner:** Ruhab leads security review, demo script and report; Saqib owns inference performance and deployment; Moiz leads final frontend integration.

- [ ] Security pass: replace the demo login rule with real accounts and invitations (routes already exist), check secrets, rate-limit `/agents/ask`.
- [ ] Performance: keep `analyze_frame`'s model loaded in a long-running process instead of starting one per request.
- [ ] Write the demo script: a recorded clip feeds the pipeline, an unattended alert fires, the Anomaly agent explains it, dispatch sends a voice task, and the digest summarises the day.
- [ ] Final deployment instructions and the integration and testing chapters of the report.

**Done means:** one `main` branch with CI, every page on real data, and dispatch, narration and clip review working in the demo.

## Integration checkpoints, risks and definition of done

Five joint checkpoints gate the plan. If a gate fails, the next phase starts on fixtures and the gap goes to the following week's top priority.

| Week | Checkpoint | Gate (all must hold) |
| --- | --- | --- |
| 2 | Contracts frozen | Schema v1 merged, tool signatures published, single `main` with CI green |
| 6 | Foundation live | Fixture store queried by tools, 10 clips labelled, stage benchmark report run, 3 pages bound |
| 10 | Agents on real data | One real CV run ingested end to end, 4 of 5 original reasoning workstreams returning results, direct dispatch reaches the employee |
| 13 | Evaluated | CV eval chapter, agent golden-set results, dispatch scenario results, all pages on real data |
| 15 | Feature freeze | Demo script rehearsed twice on recorded footage, no open P1 bugs |

### Risks

| Risk | Owner | Fallback |
| --- | --- | --- |
| Too few labelled interactions for meaningful numbers | Saqib | Record extra staged clips in week 4; report confidence intervals |
| Free HF model too weak for routing or grounding | Moiz | Env switch to a paid API model for the demo; report both |
| CV output misses fields the tools need | Saqib, Moiz | Contract test in CI that validates a CV run against schema v1 |
| Merge breaks the POS pillar | Saqib | Merge behind tests written first for `/pos/*` |
| Panel challenges employee scoring as surveillance | Ruhab, Moiz | Zone/shift aggregation, advisory labels, approval gate on separate approval-required schedule/roster actions |
| CPU too slow for live demo | Saqib, Ruhab | Demo on recorded footage; GPU laptop as optional live mode |

### Definition of done for FYP-2

- [ ] Recorded footage flows through CV stages into the event store without manual steps.
- [ ] All five original reasoning and three original operational workstreams are covered by the finalized architecture and supporting capabilities, with LangGraph traces visible on System Status.
- [ ] Every numeric agent claim is cited, and the grounded-claim rate is reported.
- [ ] Direct aisle assignments reach eligible employees without manager approval. Separate approval-required actions, such as next-day schedule changes, pass through the approval workflow.
- [ ] The report has measured results for each CV stage, each agent and the end-to-end demo.
- [ ] Future work lists Queue-driven counter opening at scale, multi-camera Re-ID, shelf interaction and promotion effectiveness; loss prevention stays out of scope.
