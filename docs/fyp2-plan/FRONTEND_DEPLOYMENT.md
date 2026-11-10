# Frontend deployment on Vercel

The package manifest and lockfile live at the **repository root**, while the Next.js app lives in `frontend/`. This is one root npm package, not an independently installable frontend package. Do not set Vercel's Root Directory to `frontend` with this layout.

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
