# UI redesign route inventory

The root AuthProvider and RouteAccessGuard apply to the site. Phase 1 selects the shell by route and authenticated role. The backend proxy continues to enforce server-side access.

| Routes | Audience and data source | Existing workflow and later verification |
|---|---|---|
| /, /about | Public copy and labeled synthetic homepage preview | Phase 2 verified sign-in link, anchors, reveals, and motion fallbacks |
| /login, /signup | Public, auth APIs | Phase 2 verified form errors, submissions, and role redirects with a mock upstream and real frontend session cookies |
| /dashboard | Manager, configured analytics and explicit synthetic preview | Phase 3 verified scope, chart counts, evidence, refresh/retry, and preview states with a mock upstream |
| /customer-info, /employee-info | Manager, labeled page fixtures | Phase 3 checked charts, keyboard-readable values, and local table scrolling |
| /spatial-analytics | Manager, labeled page fixtures | Phase 3 checked the numeric heatmap scale, readable tiles, and zone comparison. Registered map and live role occupancy are pending |
| /interactions | Manager, backend CV runs and streams | Phase 3 exercised recorded and live controls, stream slot, and result rows against a mock service. Live inference and physical camera checks remain |
| /camera-handoff | Manager, backend CV jobs and identity data | Phase 3 exercised start, evidence and role edits against a mock service |
| /compare-people | Manager, backend comparison jobs | Phase 3 exercised the two-video form and sample result table against a mock service |
| /alerts | Manager, backend alerts and tasks, with a labeled sample fallback | Phase 3 exercised filters, resolution and dispatch with local fake handlers |
| /settings, /voice-agent | Manager, backend configuration and voice operations | Mock privacy save, voice output, and orchestration covered. External delivery, other settings mutations, and real provider acceptance remain outside mock coverage |
| /employee | Employee, redirect to /employee-home | Legacy employee bookmark retained |
| /employee-home | Employee, backend tasks and labeled shift fixtures | Assignment first, with duplicate-submit protection, recoverable feedback and manager readback through Alerts |
| /my-performance | Employee, labeled page fixtures | Existing period controls and expandable daily log retained in a keyboard-scrollable table |
| /profile | Both roles, session and sample profile fields | Logout uses the session API. Profile edits, passwords, and notification preferences are local simulations |
| /style-guide | Public, component examples | Approved palette and workspace states shown alongside legacy primitives |

Dashboard reference 1 guides the sidebar, public preview, and manager overview. References 2–4 informed the zone comparison, period context, and compact tables where the existing data supports them.
