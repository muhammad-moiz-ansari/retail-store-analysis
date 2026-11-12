# Security review (Ruhab, C6)

Reviewed 12 November 2026 on `fyp2-ruhab` (based on `fyp2-moiz` at `5f2c77c`). Scope: `backend/app.py`, `backend/store_core.py`, `backend/camera_service.py`, the Next.js auth and proxy routes under `frontend/src/app/api/`, `frontend/src/lib/pos-auth.ts` and `backend-identity.ts`, and Ruhab's `backend/agents/business/`. This was a code reading. No penetration test, dependency audit or deployed-environment check was run. No code was changed; each fix goes to the file's owner.

## Findings

| # | Severity | Where | Finding | Fix | Owner |
|---|---|---|---|---|---|
| S1 | **High** | `backend/app.py:42`, `frontend/src/app/api/auth/{session,signup}/route.ts:6`, `frontend/src/app/api/backend/[...path]/route.ts:7`, `frontend/src/lib/pos-auth.ts:14` | Secrets fall back to fixed values (`local-dev-pos-secret`, `local-dev-pos-session-secret`) when the environment variables are unset. A deployment that forgets them accepts forged session cookies and lets anyone who knows the default call every backend route as any role. Only the `/analytics` proxy path refuses the defaults. | Fail closed outside local development: refuse to start (backend) or return 503 (Next routes) when the variable is missing or equals the default. Apply the analytics guard to every proxied route | Saqib (backend), Moiz (frontend) |
| S2 | Medium | `backend/app.py:46` | The internal secret is compared with `!=`, not a constant-time comparison | `hmac.compare_digest(value or '', INTERNAL_SECRET)` | Saqib |
| S3 | Medium | `/auth/login`, future `POST /agents/ask` | No rate limiting or lockout, so passwords can be brute-forced through the login proxy. Team plan C6 asks for a rate limit on `/agents/ask` | Per-IP and per-account attempt limits on login; a per-user request budget on Ask | Saqib (backend), Moiz (Ask) |
| S4 | Medium | `backend/app.py:50-57` | After the secret check, the backend trusts the role and user headers as given. This is safe only while the secret never reaches a browser; the proxy does strip browser `x-retailpulse-*` headers (`backend-identity.ts`). | Keep the secret server-side only, rotate it per deployment, and record it in the deployment checklist. Longer term, sign the actor headers | Saqib, Moiz |
| S5 | Low | `store_core.py:22` | PBKDF2-SHA256 uses 120,000 iterations; current OWASP guidance is 600,000 | Raise the iteration count and rehash on next login (the format already stores the algorithm) | Saqib |
| S6 | Low | `app.py:341` | The minimum password length is 6 | 8 or more, plus a breached-password check if time allows | Saqib |
| S7 | Low | `store_core.py:168-177` | Invitation tokens are stored in plain text | Store a hash of the token and compare hashes | Saqib |
| S8 | Low | `/analyze-frame`, `/interaction/*` | Manager-only, but there is no limit on concurrent CV subprocesses, and `_jobs` grows without bound in memory | Cap concurrent jobs and expire finished jobs | Saqib |
| S9 | Info | `camera_service.resolve_video` | Good: video paths are confined to the repository, with a suffix allow-list | None | — |
| S10 | Info | `business/clip_render.resolve_video` | Good: opaque references only, confined to one recording root and tested against `../` escapes | Supply the recording root from server configuration | Ruhab |

## Privacy notes for the report and demo

- No agent names or ranks individual employees; the router refuses `rank`, `identify` and `identity` questions (`routing.py`).
- Occupancy categories describe areas, not people, and cell IDs are not authorization scopes.
- Review clips burn in a synthetic banner for fixture footage. Real clips show people, so a review page must be manager-only and must not be cached publicly.
- Dispatch events carry zone and time evidence, never CV track IDs as employee identities.

## Checks still needed

- Run `npm audit` and `pip-audit` once dependency changes freeze (week 14).
- After the first push, confirm that the GitHub repository has no committed `.env` and that CI secrets stay unused.
- Re-check S1 in the actual Vercel and backend deployment settings.
