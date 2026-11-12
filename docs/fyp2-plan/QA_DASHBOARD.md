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

## Checks run

See "Frontend check results" in PROGRESS.md for the exact commands and outcomes from this review.
