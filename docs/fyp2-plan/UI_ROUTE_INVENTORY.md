# UI redesign route inventory

The root AuthProvider and RouteAccessGuard apply to the site. Phase 1 selects the shell by route and authenticated role. The backend proxy continues to enforce server-side access.

| Routes | Audience and data source | Existing workflow and later verification |
|---|---|---|
| /, /about | Public copy and labeled synthetic homepage preview | Phase 2 verified sign-in link, anchors, reveals, and motion fallbacks |
| /login, /signup | Public, auth APIs | Phase 2 verified form errors, submissions, and role redirects with a mock upstream and real frontend session cookies |
| /dashboard | Manager, configured analytics and explicit synthetic preview | Phase 3 verify source, scenarios, refresh, and metric states |
| /customer-info, /employee-info | Manager, page fixtures | Phase 3 verify existing charts and controls |
| /spatial-analytics | Manager, page fixtures | Phase 3 verify filters and visual states |
| /interactions | Manager, backend CV runs and streams | Phase 3 verify camera controls, run selection, and overlays |
| /camera-handoff | Manager, backend CV jobs and identity data | Phase 3 verify start, results, and role edits |
| /compare-people | Manager, backend comparison jobs | Phase 3 verify source selection and results |
| /alerts | Manager, backend alerts and tasks | Phase 3 verify resolution and dispatch using test handlers |
| /settings, /voice-agent | Manager, backend configuration and voice operations | Phase 4 verify forms and status without external delivery |
| /employee | Employee, redirect to /employee-home | Phase 4 verify legacy bookmark and role restriction |
| /employee-home | Employee, backend tasks | Phase 4 verify assignment and status transitions using fixtures |
| /my-performance | Employee, page fixtures | Phase 4 verify period controls |
| /profile | Both roles, session and existing profile fields | Phase 4 verify account links and logout |
| /style-guide | Public, component examples | Phase 4 verify shared controls and states |

Dashboard reference 1 guides the Phase 1 sidebar and Phase 2 preview. References 2–4 inform later data panels where matching data is available.
