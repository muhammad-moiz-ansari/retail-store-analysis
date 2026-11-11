# PostgreSQL setup and SQLite import

The Python backend, CV ingestion, analytics readers, and camera identity store share PostgreSQL through `DATABASE_URL`. Next.js continues to call the Python backend through the session proxy. Supply the database URL to Python only.

## Initialize a fresh database

1. Provision a dedicated PostgreSQL database or a private schema with a backend role whose search path selects that schema. For a hosted provider, use its direct or session connection and TLS settings. Keep the application tables outside browser-accessible schemas.
2. Install `backend/requirements.txt` in the backend environment and set `DATABASE_URL` there. The standalone Python commands use exported environment variables. The repository's `npm run dev` launcher also loads the root local environment file.
3. Run `python -m backend.database` from the repository root to create the tables. For a fresh installation, set `RETAILPULSE_BOOTSTRAP_MANAGER_EMAIL` and `RETAILPULSE_BOOTSTRAP_MANAGER_PASSWORD` and run `python -m backend.database --bootstrap-manager` to create the first manager. For a disposable demo, `--seed-demo` creates the existing demo accounts and settings. If preserving existing accounts, import their application database before creating new accounts.
4. Start the Python backend and Next.js as usual. For configured dashboard analytics, follow [dashboard setup](DASHBOARD_BACKEND_SETUP.md). Remove the old `event_db` key from that configuration.

CV ingestion and fixture generation use the same environment variable. The SQLite `--db` and `--events-db` path options have been removed. Generate the canonical synthetic day with `python -m backend.events.fixtures` in a dedicated test database.

## Copy existing records

Stop writes to the legacy stores before taking consistent backups. Set `DATABASE_URL` to the new PostgreSQL destination and run the import against empty destination tables:

```powershell
python -m backend.import_sqlite --application "backup/retailpulse.sqlite3" --events "backup/events.sqlite3" --identities "backup/interaction.sqlite3"
```

Provide only the files you intend to copy. The command creates the PostgreSQL schema, opens the source files read-only, preserves account IDs and password hashes, copies records and validates row counts in one transaction. It rejects populated destination tables for the supplied sources. An invalid record rolls back the import. Event timestamps retain their instants in PostgreSQL `TIMESTAMPTZ`. Identity records retain their original listing order. Keep the backups until login, dashboard counts and camera identity behavior have been checked on the destination.

## Verify locally

Set `TEST_DATABASE_URL` to a disposable PostgreSQL database whose role can create schemas. Tests create and remove their own isolated schemas:

```powershell
python -m pytest backend/agents backend/events/test_events.py backend/interaction/test_identity.py backend/test_postgres_migration.py
npm run test:dashboard-provider
```

Only the import utility and its test use SQLite. The dashboard's operator configuration still defines source provenance and user/store/run/camera/region membership. Keep fixture and real deployments separated by database or by operator-approved run allowlists.
