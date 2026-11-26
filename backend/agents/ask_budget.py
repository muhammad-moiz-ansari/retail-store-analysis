"""Shared fixed-window Ask budget, enabled explicitly for multi-worker deployments."""

from ..database import connect


def take_shared_request(actor_id: str, store_id: str) -> bool:
    with connect() as conn:
        row = conn.execute(
            """INSERT INTO agent_ask_budget(actor_id, store_id, window_start, requests)
               VALUES (%s, %s, date_trunc('minute', statement_timestamp()), 1)
               ON CONFLICT (actor_id, store_id) DO UPDATE
                   SET window_start = EXCLUDED.window_start,
                       requests = CASE
                           WHEN agent_ask_budget.window_start < EXCLUDED.window_start THEN 1
                           ELSE agent_ask_budget.requests + 1
                       END
                   WHERE agent_ask_budget.window_start < EXCLUDED.window_start
                      OR (agent_ask_budget.window_start = EXCLUDED.window_start
                          AND agent_ask_budget.requests < 10)
               RETURNING requests""",
            (actor_id, store_id),
        ).fetchone()
        return row is not None
