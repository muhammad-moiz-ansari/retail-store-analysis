# Dashboard QA findings (Ruhab → Moiz)

Reviewed 12 November 2026 on `fyp2-ruhab`, which matches `fyp2-moiz` at `5f2c77c` for every frontend file. Scope: `frontend/src/app/dashboard/page.tsx`, `frontend/src/components/dashboard/DashboardAnalytics.tsx`, `frontend/src/lib/analytics-provider/` and `backend/agents/dashboard.py`. This is a review against the shared contracts. No frontend file was changed; the fixes are Moiz's call.

## What holds up

- No fabricated fallback anywhere: a backend failure shows "unavailable" and never switches to fixtures. Fixture preview is an explicit choice with a synthetic banner.
- Null metrics render as "Unavailable", observed-empty is labelled separately, and missing values are stated as "not zero".
- Unattended episodes are labelled "Derived", which matches the stored-derivation caveat.
- Dwell and coverage require a zone in the backend request (`DashboardRequest.zoneId`), so no all-zone distribution is invented.

## Findings

| # | Severity | Where | Finding | Suggested fix |
|---|---|---|---|---|
| Q1 | Medium | `DashboardAnalytics.tsx`, evidence list | The evidence list joins every cited ID inline. A metric can cite up to 200 IDs, which floods the card on mobile | Show the first ~5 IDs plus "N more", or a copyable list |
| Q2 | Medium | `metricValue()` | Seconds are always shown raw (for example "1,834.5 s"). Dwell and duration are hard to read | Use the same scale as the digest: s under 2 min, min under 2 h, then h. Keep the raw seconds in the evidence details |
| Q3 | Low | Scope block | Backend mode always has a zone, so the "All permitted regions" fallback only ever shows in fixture mode, and the window is printed as raw ISO strings | Show the zone's display name and a local-time window with "UTC" beside it |
| Q4 | Low | Confirmed and unverified cards | The two cards have equal visual weight, so a manager may add them together | Put unverified under confirmed as a secondary line: "4 unverified (not counted)" |
| Q5 | Low | `SystemStatusStrip` | The fetch has no abort on unmount and no retry button, unlike the analytics panel | Add an AbortController plus a Retry button, as `BackendDashboard` has |
| Q6 | Info | Ask panel and map panel | Still disabled. Both business agents are now registered through `business_specialists()`, and the four-category and layer contracts exist (see CONTRACTS.md, "Ruhab business agents and policies") | Wire them when the `POST /agents/ask` auth binding lands |
| Q7 | Info | Digest | There is no place for the Insight Narration digest yet | A "Today's digest" card that renders `Digest.sections`, the fixture banner and caveats as given |

## Status (17 November 2026)

| # | Status |
|---|---|
| Q1 | Fixed: each evidence line shows the first 5 IDs and "and N more" |
| Q2 | Fixed: seconds read as s under 2 min, min under 2 h, then h; the exact seconds stay in the evidence details |
| Q3 | Partly fixed: the window reads as `YYYY-MM-DD HH:MM UTC` (the ISO value stays in the `datetime` attribute). Zone display names are still the IDs; the backend has no display-name field |
| Q4 | Fixed: the card reads "Unverified interactions (not counted)" with a "Not added to confirmed interactions" line |
| Q5 | Fixed: the system status fetch aborts on unmount and has a Retry button (`manager/home/page.tsx`) |
| Q6 | Ask is wired (`8272140`); the map panel renders when a map is configured |
| Q7 | Open on this page; the manager home page has a digest panel (`c766434`) |

Tests: `DashboardAnalytics.test.tsx` covers Q1–Q4; `npm run test:dashboard-provider` gives 40/40.

## Checks run

See "Frontend check results" in PROGRESS.md for the exact commands and outcomes from this review.
