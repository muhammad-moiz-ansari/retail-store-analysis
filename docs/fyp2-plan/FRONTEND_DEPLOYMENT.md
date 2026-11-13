# Frontend deployment on Vercel

The package manifest and lockfile live at the **repository root**, while the Next.js app lives in `frontend/`. This is one root npm package, not an independently installable frontend package. Do not set Vercel's Root Directory to `frontend` with this layout.

The Python backend uses [PostgreSQL](POSTGRESQL_SETUP.md). Set DATABASE_URL in the backend environment.

## Dashboard fixture preview — M-UI-P2

The manager dashboard now defaults to Configured backend (M-UI-P3); synthetic preview remains an explicit choice. Backend analytics requires the server secrets/membership/source setup in [DASHBOARD_BACKEND_SETUP.md](DASHBOARD_BACKEND_SETUP.md). Missing configuration displays unavailable and never falls back to fixtures. System status is a separate backend request. No Vercel settings, real server configuration or secrets were changed by these phases; deploying frontend code alone does not connect cameras or real agents.

To check manually:

1. From the repository root, run `npm run dev:frontend` (or `npm run build` then `npm start` for production). Use your normal configured backend and valid Manager account to sign in, or an existing valid authenticated session. Preview analytics do not require event feeds, but this phase does not bypass login or add an account.
2. Open `/dashboard`, then explicitly select Synthetic fixture preview under Analytics data source. Confirm the fixture-preview banner, demo-store/demo-region and 3 Nov 2026 09:00–10:00 UTC observation window. These are fixed scenario identifiers, not your real store. Configured backend instead uses the server-authorized selection.
3. In Preview scenario, select Ready, Observed empty, Partial data, Unavailable and Stale data. Check that empty counts show zero, undefined averages/ratios remain Unavailable, partial coverage explains the missing operating-window configuration, and stale values carry an expiry warning.
4. Click Refresh analytics. Change scenarios quickly; obsolete results must not overwrite the current selection. Leave Ready or Partial data open for just over one minute: it should become Stale data without another provider call. Selecting the Stale scenario already returns expired values, so refreshing that scenario remains stale by design.
5. Expand Evidence and limitations to inspect units/source IDs, matched/truncated evidence and source caveats. Confirm the video is labelled Recorded demo clip with playback controls; other live cameras, interaction rows and map layers are unavailable, and Ask is disabled.
6. Resize to mobile and check the single-column cards/select/refresh controls. Existing employee/anonymous route restrictions should still apply.

Automated checks: `npm run test:dashboard-provider` (34 checks), frontend typecheck and targeted ESLint as recorded in PROGRESS.md, plus `npm run build`. M-UI-P3 adds 16 backend HTTP/reader tests to the existing suite (155 passed/1 existing real-output skip) and normal username/password login-to-dashboard browser verification against disposable application/CV-fixture databases. This verifies the configured connection; real feed/context/deployment/agent acceptance remains pending. The fixture generator is unchanged and still synthetic.

## Project settings

| Setting | Value |
|---|---|
| Root Directory | Repository root (`.` / leave the directory field empty) |
| Git branch | `fyp2-moiz` for the current work; use a preview deployment if production remains on `main` |
| Framework Preset | Next.js |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `frontend/.next` |

The root `vercel.json` records the framework/install/build/output configuration. Root Directory is a project setting and must also point to the repository root; a config file inside an excluded parent does not fix a wrongly selected root. Deploy a Git branch/commit containing this manifest and configuration. Root `package.json` and `package-lock.json` pin the deployed Next.js dependency; do not judge the version by stale local node_modules.

The reported failed project selected `frontend` and the old `main` branch. In the Vercel project settings, correct Root Directory and framework/build settings, save, then redeploy the intended commit with the existing build cache disabled for this diagnostic run. The build should identify the locked Next.js version and invoke `next build frontend` via the root npm script.

`NEXT_NO_VERSION` is a framework/dependency detection failure, before application compilation. The npm `cache-dir` warning is separate and is not the fatal error shown. If detection still fails, inspect the deployment's Git branch/commit and Source files: verify that its selected root actually contains the expected package.json with a Next dependency. Do not add a second conflicting package manifest or upgrade Next merely to work around a directory setting. Local commits must be published to the intended remote branch before Vercel can build them; redeploying an old main deployment still builds that old commit. No push or cloud deployment is performed by this local fix.

## Backend connection is separate

This configuration builds the Next.js app; it does not deploy the Python/CV service. Existing proxy routes require a reachable `RETAILPULSE_SERVICE_URL` and the matching server-side internal secret for a separately running backend. A deployed Vercel function cannot reach a developer laptop through `127.0.0.1`. Backend authentication, durable data and production integration remain separate work. Never put server credentials in `NEXT_PUBLIC_*` variables.

References: [Vercel monorepo/root settings](https://vercel.com/docs/monorepos), [project configuration](https://vercel.com/docs/project-configuration).

## Local dependency consistency

The inspected machine had Next 16 in both root and nested `frontend/node_modules`, despite the committed manifest/lockfile selecting Next 15. `npm ci` restored root Next 15.5.25. The stale nested dependency folder was moved intact to ignored `data/outputs/vercel-check/frontend-node_modules-backup-20261110`; it was not deleted. Both root and frontend now resolve the locked version from root node_modules.

A root npm install does not remove an independently populated nested node_modules directory. Mixed versions caused the first local build to fail while collecting `/api/backend/[...path]` configuration with `this.load is not a function`; compilation alone was not a complete build check. A fresh Git-based Vercel checkout does not include these ignored local dependency folders. Use the root lockfile installation for this project's layout.

The existing Next configuration skips type checking and linting during production builds. Build success therefore confirms compilation/page generation, not a full type/lint verification; this change does not add or change those bypasses.

Verification: root `npm ci` restored locked Next 15.5.25; final `npm run build` passed compilation, all 26 page-generation steps and build tracing. Manifest/lock/config/output paths were checked. Vercel cloud deployment and live backend/auth behavior are not verified by this local build.

User subsequently confirmed the frontend deployment works. That is user-reported cloud success; live Python/CV backend, login/proxy and real-data connectivity still need separate verification. Current work resumes from the combined team plan, not the old deployment-blocker assumption.
