-- Opt-in Ask retention. Apply separately to the intended backend database.
CREATE TABLE IF NOT EXISTS agent_ask_traces (
    run_id TEXT PRIMARY KEY,
    actor_id TEXT NOT NULL,
    store_id TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS agent_ask_traces_expiry ON agent_ask_traces(expires_at);
