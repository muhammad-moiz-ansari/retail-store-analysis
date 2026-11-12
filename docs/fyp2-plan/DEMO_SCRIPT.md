# Demo script (Ruhab, C6)

Target: about 12 minutes, rehearsed twice on recorded footage before week 15 (9–15 Feb). Each step names what to show, the source of the evidence, and the fallback if a live part fails. Never present fixture numbers as store results: if a step falls back to fixtures, say so out loud and leave the synthetic banner visible.

| # | Time | Show | Say | Evidence | Fallback |
|---|---|---|---|---|---|
| 1 | 1 min | Login as manager → dashboard | "One login per role. Analytics come only from the configured backend." | M-UI-P3 | Fixture preview with its banner, stated as synthetic |
| 2 | 2 min | Interactions page: run a recorded static-camera clip | "Detection, tracking, role labelling, then the pose judge confirms an interaction." | B2 benchmark (set B F1, stated as held-out) | Pre-rendered output video |
| 3 | 1 min | Event store rows for that run | "Every row has a run, store, camera and time span, so every later number traces back." | `validate()` returning `[]` | Recorded terminal output |
| 4 | 2 min | Ask "Summarise customers today", then "Where are the staff coverage gaps?" | "Each number is a checked reference to a tool result. Unverified interactions are shown, never counted." | Golden set scores (fixture), grounded claims | Run the golden evaluation command live |
| 5 | 2 min | Map: four live categories plus layers | "Customer, Employee, Both, No one. A covered camera is masked, never shown as empty." | ACCEPTANCE A3 | `test_occupancy.py` scenarios |
| 6 | 2 min | Customer waits → alert → task on the employee home page | "No manager approval for aisle dispatch. Repeating the event does not create a second task." | ACCEPTANCE A5–A7 | Fake-handler replay, stated as fake |
| 7 | 1 min | Digest and page summary | "The text is built from checked figures only; any LLM narrative is rejected if it adds a number." | `verify_narrative` | Template digest |
| 8 | 1 min | Clip Review on one alert | "Blind review measures precision and agreement between two reviewers." | Clip Review summary | Pre-rendered review clip |

## Before each rehearsal

- [ ] Freeze the model weights and config, and record the commit hash.
- [ ] Load real footage into the event store and record its run IDs.
- [ ] Set secrets (SECURITY_REVIEW S1) and confirm no default secret is in use.
- [ ] Play each fallback once so it is ready.
- [ ] Note which steps used fixtures, and write it on the closing slide.
