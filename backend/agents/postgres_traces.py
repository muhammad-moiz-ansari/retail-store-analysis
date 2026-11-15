"""Optional PostgreSQL retention for authorized Ask runs."""
from psycopg import Error
from psycopg.types.json import Jsonb

from ..database import DatabaseNotConfigured, connect
from .graph_contracts import GraphRun
from .traces import TraceCapacityError


class PostgresTraceStore:
    def put(self, run: GraphRun) -> None:
        payload = run.model_dump_json()
        if len(payload.encode("utf-8")) > 2_097_152:
            raise TraceCapacityError("Trace exceeds 2 MiB")
        with connect() as conn:
            conn.execute("DELETE FROM agent_ask_traces WHERE expires_at <= CURRENT_TIMESTAMP")
            conn.execute(
                """INSERT INTO agent_ask_traces(run_id, actor_id, store_id, expires_at, payload)
                   VALUES (%s, %s, %s, CURRENT_TIMESTAMP + interval '24 hours', %s)""",
                (run.run_id, run.scope.actor_id, run.scope.store_id, Jsonb(run.model_dump(mode="json"))),
            )

    def get(self, run_id, scope) -> GraphRun:
        try:
            with connect() as conn:
                row = conn.execute(
                    """SELECT payload FROM agent_ask_traces
                       WHERE run_id = %s AND actor_id = %s AND store_id = %s
                         AND expires_at > CURRENT_TIMESTAMP""",
                    (run_id, scope.actor_id, scope.store_id),
                ).fetchone()
        except (Error, DatabaseNotConfigured):
            raise RuntimeError("Ask trace storage unavailable") from None
        if not row:
            raise KeyError("Analytics run not found")
        run = GraphRun.model_validate(row["payload"])
        if run.scope != scope or run.run_id != run_id:
            raise KeyError("Analytics run not found")
        return run
