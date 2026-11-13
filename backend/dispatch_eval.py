"""C3 evaluation: run backend/dispatch_scenarios.json through the real dispatch and compare with a human rater.

python -m backend.dispatch_eval [scenarios.json]    (needs TEST_DATABASE_URL or DATABASE_URL; uses a throwaway schema)
Agreement is reported only over scenarios whose rater_choice is filled in.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

from psycopg import sql
from psycopg.conninfo import make_conninfo

from .database import connect, initialize
from .dispatch import handle_event
from .store_core import now_iso, seed_defaults

DEFAULT = Path(__file__).with_name("dispatch_scenarios.json")


def system_choice(conn, scenario: dict) -> tuple[str, str]:
    ts = now_iso()
    conn.execute("DELETE FROM rosters")
    conn.execute("DELETE FROM users WHERE role = 'Employee'")
    for e in scenario["employees"]:
        conn.execute("INSERT INTO users(id, name, email, role, password_hash, active, created_at, updated_at) VALUES (%s, %s, %s, 'Employee', 'x', 1, %s, %s)",
                     (e["id"], e["id"], f"{e['id']}@scenario", ts, ts))
        if e.get("rostered", True):
            conn.execute("INSERT INTO rosters(id, user_id, zone_id, shift, available, created_at, updated_at) VALUES (%s, %s, %s, 'all day', %s, %s, %s)",
                         (f"r_{e['id']}", e["id"], e["zone"], int(e["available"]), ts, ts))
        if e["busy"]:
            conn.execute("INSERT INTO tasks(id, employee_id, instruction, state, created_at, updated_at) VALUES (%s, %s, 'busy', 'in_progress', %s, %s)",
                         (uuid.uuid4().hex, e["id"], ts, ts))
    result = handle_event(conn, {"eventType": "unattended_customer", "zoneId": scenario["target_zone"]})
    return result["selectedEmployeeId"] or "none", result["reason"]


def evaluate(scenarios: list[dict], url: str) -> dict:
    rows = []
    for scenario in scenarios:
        schema = f"dispatch_eval_{uuid.uuid4().hex[:8]}"
        with connect(url) as admin:
            admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            with connect(make_conninfo(url, options=f"-csearch_path={schema}")) as conn:
                initialize(conn)
                seed_defaults(conn)
                choice, reason = system_choice(conn, scenario)
        finally:
            with connect(url) as admin:
                admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        rows.append({"id": scenario["id"], "system": choice, "rater": scenario.get("rater_choice"), "reason": reason})
    rated = [r for r in rows if r["rater"]]
    agree = sum(r["system"] == r["rater"] for r in rated)
    return {"scenarios": rows, "rated": len(rated), "agreement": agree / len(rated) if rated else None}


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("Set TEST_DATABASE_URL (a disposable database) or DATABASE_URL")
    report = evaluate(json.loads(path.read_text(encoding="utf-8"))["scenarios"], url)
    for r in report["scenarios"]:
        mark = "" if not r["rater"] else (" agree" if r["system"] == r["rater"] else f" DISAGREE (rater: {r['rater']})")
        print(f"{r['id']} -> {r['system']}{mark}  | {r['reason']}")
    print(f"rated {report['rated']}/{len(report['scenarios'])}, agreement {report['agreement']}")


if __name__ == "__main__":
    main()
