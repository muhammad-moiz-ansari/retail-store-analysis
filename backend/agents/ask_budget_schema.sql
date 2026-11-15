-- Optional shared Ask budget. One row per manager and store.
CREATE TABLE IF NOT EXISTS agent_ask_budget (
    actor_id TEXT NOT NULL,
    store_id TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    requests INTEGER NOT NULL CHECK (requests BETWEEN 1 AND 10),
    PRIMARY KEY (actor_id, store_id)
);
