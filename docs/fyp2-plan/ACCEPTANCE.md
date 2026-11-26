# TEAM-ACCEPTANCE plan and threshold review (Ruhab)

Updated 12 November 2026. Ruhab leads acceptance; Saqib and Moiz supply evidence. A scenario passes only on **real footage through the deployed or locally integrated system**. Fixture runs prove the logic, not acceptance. Every result records the data source, commit, model weights, config and policy versions used.

## Evidence rules

| Rule | Why |
|---|---|
| Record `synthetic` for every run, and never mix fixture and real data in one result | A fixture pass cannot be reported as a store result |
| Quote numbers only from grounded claims, Clip Review summaries or the benchmark reports | The report and demo must trace back to stored evidence |
| A masked or unknown observation is never counted as an empty or unstaffed area | This is the four-category rule in the combined plan |
| A handler-reported `dispatched` is not proof of delivery; acknowledgement needs Saqib's delivery evidence | Matches the operational contract |

## End-to-end scenarios

Owners: **S** = Saqib, **M** = Moiz, **R** = Ruhab. Status is "not run" until real evidence exists.

| ID | Scenario | Steps | Pass when | Needs | Status |
|---|---|---|---|---|---|
| A1 | Recorded clip to events | Run CV on one static-camera clip, then ingest it with `--camera` | Rows land in every event table with the run, store and camera IDs; `validate()` returns `[]`; health rows cover the clip | S: MAP-1 | not run |
| A2 | Events to map | Register the supplied map for that camera; produce `CellObservation`s per window | Each cell has `map_version`; unmapped areas carry `mapped=false` | S: MAP-2 | not run |
| A3 | Live categories | Feed A2 into `OccupancyTracker` | A person walking through changes a cell customer → no_one after the hold. Staff plus a customer shows `customer_employee`. Covering the lens gives `insufficient_coverage`, not `no_one` | S/R | not run |
| A4 | Manager question | Ask "Summarise customers today" and "Where are the staffing gaps?" with `business_specialists()` | `development_stub=false`; every number matches a tool metric; caveats shown; Clip Review confirms a sample of the cited interactions | M: HTTP/auth binding | not run |
| A5 | Unattended to eligible employee | A customer waits more than `min_wait_s` with no staff nearby | `evaluate_zone` emits `unattended_customer`; the adapter calls Saqib's handler; an eligible employee gets a task; the manager view shows it | S: real handler | not run |
| A6 | No eligible employee | Repeat A5 with no on-shift employee for the zone | Outcome `no_eligible_employee`; no task created; the manager is told | S | not run |
| A7 | Duplicate event | Replay A5's window | Same `idempotencyKey`; outcome `duplicate`; still one task | S | not run |
| A8 | Blind camera | Block the camera during an A5 wait | Policy suppresses with `unknown_observation_too_high`; no task; the digest caveat names the blind time | S/R | not run |
| A9 | Digest | Build the day's digest from A4 runs plus A5 decisions | Provenance `real`; no `FIXTURE` caveat; all figures match the claims | M: UI | not run |
| A10 | Clip Review precision | Blind-review 30 or more confirmed interactions from A1 with two reviewers | Precision and Cohen's kappa recorded; disagreements resolved and logged | S: recording map | not run |

### Fixture rehearsal (done)

The logic behind A3–A9 has been run on labelled fixtures only, by `backend/agents/business/test_*.py`: 48 tests, all passing on 12 November 2026. This is a rehearsal, not acceptance.

### Synthetic end-to-end rehearsal on PostgreSQL (14 November 2026, Ruhab)

`python -m backend.acceptance_rehearsal` runs A1–A10 through the integrated code paths on the synthetic fixture day (`backend/events/fixtures.py`: 17–19 h rush, understaffed z3, camera c2 blocked 14:00–14:40) against the team's Neon PostgreSQL, in its own schema `acceptance_synthetic`. Every row is `synthetic`; **none of this is acceptance**, and the status column above stays "not run" until real footage passes. Report: `docs/fyp2-plan/evidence/acceptance_rehearsal_synthetic.json` (regenerated 17 Nov 2026 on a throwaway local PostgreSQL; earlier runs used Neon).

| ID | Rehearsal | What ran | Notes |
|---|---|---|---|
| A1 | pass | Fixture day → event store; `validate()` = `[]`; rows in all 9 tables; health covers 720/720 minutes per camera | CV inference and `ingest --camera` on real output not exercised |
| A2 | blocked | `CellObservation` contract only (map_version required, unmapped masked) | Registration code exists (`backend/events/spatial.py`, `1364810`), but no floor plan or camera calibration points are configured |
| A3 | pass | z3 as one cell from stored dwell + c2 health → `OccupancyTracker` | customer → no_one only after the 2-window hold; customer_employee seen; blackout gives `insufficient_coverage`, never no_one |
| A4 | pass | Both questions via `business_specialists()` on stored events | `development_stub=false`; every claim equals its tool metric; caveats shown. Clip Review of cited interactions needs recordings |
| A5 | pass | z3, 09:00–10:00: policy → adapter → real `dispatch` handler | Eligible floater got a task; alert + task rows visible to the manager |
| A6 | pass | z3, 10:00–11:00 with every roster unavailable | `no_eligible_employee`, no task, alert raised |
| A7 | pass | Replay of A5's window | Same `idempotencyKey`, `duplicate`, still one task |
| A8 | pass | z3, 13:00–14:40 (c2 blind 40 of 100 min) | Suppressed `unknown_observation_too_high`, no task |
| A9 | pass (17 Nov rerun; failed on 14 Nov) | Digest from A4 runs + z3 decisions | Provenance `synthetic` (correct for fixtures); figures verified; the caveat names the blind time, 14:00–14:40 UTC (`agents/tools/common.py::blind_note`) |
| A10 | blocked | Blind sampling of 30 stored interactions | Precision/kappa need two human reviewers and the run→recording map |

Found and fixed by this rehearsal: the offline router refused A4's own question "Where are the staffing gaps?" (`routing.py` did not route *staffing*/*gaps*), and `verify_narrative` counted the digits in zone IDs such as `z3` as figures (`narration.py`). Both have regression tests. The coverage caveat now names the blind interval (16 Nov), and the 17 Nov rerun passes A9: 8 rehearsal passes, A2 and A10 not runnable.

## Threshold review sheet

These are Ruhab's proposed defaults. They are **not tuned on real store data**. The team should agree on them, or change them, before A5–A8. They are configured per store, so a different store can override them without code changes. That answers the generalisability question raised at the proposal defence.

| Setting | Default | Where | What it controls | Check against |
|---|---|---|---|---|
| `min_wait_s` | 180 s | `SignalPolicy`, plus the tool default | Unhelped wait that raises a customer-waiting event | Store service standard; A5 footage |
| `high_wait_s` | 360 s | `SignalPolicy` | Wait that makes the event high priority | Manager input |
| `high_episode_count` | 3 | `SignalPolicy` | Number of waiting customers in one zone that makes it high priority | Manager input |
| `min_staffed_ratio` | 0.25 | `SignalPolicy` | Staffed share of open time below which a zone is short of staff | Roster and floor plan |
| `max_unknown_share` | 0.2 | `SignalPolicy` | Blind share above which both events are suppressed | A8 footage |
| `min_coverage` | 0.8 | `OccupancyPolicy` | Observed share needed before a cell gets a category | A3 occlusion tests |
| `min_presence_s` | 5 s | `OccupancyPolicy` | Presence needed for a role to count in a cell | Walk-through footage |
| `hold_windows` | 2 | `OccupancyPolicy` | Consecutive windows before a category change shows | A3 flicker check |
| Clip padding | 3 s | `review_items(pad_s=)` | Footage shown before and after an event | Reviewer feedback |

Decision log (fill in at review):

Rows dated 17 Nov 2026 are **proposed, pending Ruhab's sign-off**. Each value is the current code default, checked against the code on that date. None is tuned on real store data. Ruhab adds her name to *Agreed by* or replaces the value; a changed value goes in a new row, so the history stays.

| Date | Setting | Agreed value | Agreed by | Evidence |
|---|---|---|---|---|
| 17 Nov 2026 | `min_wait_s` | 180 s | Saqib (proposed); Ruhab pending | Proposed default (`signal_policy.py`). No store service standard or A5 footage yet. A8 rehearsal suppresses as expected. Demo clips may use `python -m backend.operations --min-wait-s`; that override is for short clips only, not the store value |
| 17 Nov 2026 | `high_wait_s` | 360 s | Saqib (proposed); Ruhab pending | Proposed default, twice `min_wait_s`. No manager input yet |
| 17 Nov 2026 | `high_episode_count` | 3 | Saqib (proposed); Ruhab pending | Proposed default. No manager input yet |
| 17 Nov 2026 | `min_staffed_ratio` | 0.25 | Saqib (proposed); Ruhab pending | Proposed default. The fixture's understaffed z3 falls below it in the rehearsal. No roster or floor plan check |
| 17 Nov 2026 | `max_unknown_share` | 0.2 | Saqib (proposed); Ruhab pending | Proposed default. A8 rehearsal: c2 blind 40 of 100 min (0.4) suppresses. Not checked on real footage |
| 17 Nov 2026 | `min_coverage` | 0.8 | Saqib (proposed); Ruhab pending | Proposed default (`occupancy.py`). A3 rehearsal: blackout gives `insufficient_coverage`, never `no_one`. No real occlusion test |
| 17 Nov 2026 | `min_presence_s` | 5 s | Saqib (proposed); Ruhab pending | Proposed default. No walk-through footage yet |
| 17 Nov 2026 | `hold_windows` | 2 | Saqib (proposed); Ruhab pending | Proposed default. A3 rehearsal: customer → no_one only after the 2-window hold. No real flicker check |
| 17 Nov 2026 | Clip padding | 3 s | Saqib (proposed); Ruhab pending | Default `review_items(pad_s=3.0)`, clips 10–20 s. No reviewer feedback yet |

Live camera view state (FR-07, Interactions page only; not one of the four categories, see CONTRACTS.md "Live camera view state"). These do not affect the agents or dispatch:

| Date | Setting | Agreed value | Agreed by | Evidence |
|---|---|---|---|---|
| 17 Nov 2026 | `zone_hot_ratio` | 1.0 customer per employee | Saqib (proposed); Ruhab, Moiz pending | Default in `interaction/config.py`; unit tests in `test_live_zones.py` only |
| 17 Nov 2026 | `zone_served_seconds` | 30 s | Saqib (proposed); Ruhab, Moiz pending | Default; unit tests only |
| 17 Nov 2026 | `view_hold_seconds` | 1.5 s | Saqib (proposed); Ruhab, Moiz pending | Default; unit tests only |
