# FYP-2 Implementation Plan

Derived from `FYP Report-main.pdf` (Ch. 8.11 Current Limitations, Ch. 9 Remaining FYP Plan),
checked against the code on branch `feature/interaction-live` (2026-10-23).

**Rule for everything here: no new models.** All new analytics are plain logic over the tracks
the interaction pipeline already produces.

| Doc | What it covers |
|-----|----------------|
| [PLAN.md](PLAN.md) | Ordered steps, files touched, done-when checks, timeline |
| [MODELS.md](MODELS.md) | Current YOLO weights and the consolidation to one detector + pose |
| [CONTRACTS.md](CONTRACTS.md) | Existing pipeline JSON shapes and the new summary/API shapes |
| [EVALUATION.md](EVALUATION.md) | Labelling the 10 clips, metrics to report, CPU throughput |

## Report gaps this closes

| Report limitation / remaining item | Step |
|---|---|
| "Vision-derived dashboard metrics still use prototype or demo data" | 2, 3 |
| "Interaction results are available through the CLI; dashboard integration remains pending" | 2 |
| Footfall, zone dwell, heatmaps (in-scope analytics, not yet real) | 1 |
| Unattended-customer flags, employee idle time | 1, 3 |
| "Alerts on real events" (Iteration 3) | 3 |
| "Interaction accuracy is measured on one labelled clip only" | 4 |
| CPU throughput to record (deliverable 9.8) | 4 |

## Not in this plan (stays future work, as the report already says)

- Cross-camera handoff: needs appearance re-ID, i.e. more models.
- Shelf-level product interaction.
- Metric floor distance (descoped, Section 6.4.3).
- Multi-store, real-time as primary deliverable, retail-partner pilot.
- Insight Narration / Query agents over real analytics: possible after Step 2 exists, not planned here.
