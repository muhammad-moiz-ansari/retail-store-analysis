"""TEAM-ACCEPTANCE rehearsal (A1-A10) on the synthetic fixture day. This is NOT acceptance.

docs/fyp2-plan/ACCEPTANCE.md: a scenario passes only on real footage through the integrated system. This script runs
the same code paths on `backend.events.fixtures` (one planted day: 17-19 h rush, understaffed z3, camera c2 blocked
14:00-14:40) so the wiring is proven end to end against a real PostgreSQL database before real footage exists. Every
result is recorded as synthetic and must never be reported as a store result.

Real paths exercised: fixture -> event store + validate() (A1); stored dwell/health -> OccupancyTracker (A3);
AnalyticsService + business_specialists() over the stored events (A4); signal policy -> OperationalDispatchAdapter ->
backend.dispatch handler writing tasks/alerts (A5-A8); build_digest + verify_narrative (A9); blind Clip Review items
from stored interactions (A10). A2 (map registration, MAP-2) has no implementation yet, and A10 needs two human
reviewers and recordings, so those only get their contract checks.

python -m backend.acceptance_rehearsal [--schema acceptance_synthetic] [--output report.json] [--drop]
Needs TEST_DATABASE_URL (or DATABASE_URL) on a direct, unpooled connection. Everything is written to its own schema, recreated on each run and kept
afterwards for inspection; --drop removes it and exits. Dispatch runs with allow_synthetic=True inside that schema only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from psycopg import sql
from psycopg.conninfo import make_conninfo

from .agents.business.clip_review import from_interaction_rows, review_items
from .agents.business.employee_activity import business_specialists
from .agents.business.narration import build_digest, verify_narrative
from .agents.business.occupancy import CellObservation, OccupancyTracker
from .agents.business.signal_policy import SignalPolicy, evaluate_zone
from .agents.contracts import TimeWindow, TrustedAccessScope
from .agents.graph_contracts import AskRequest
from .agents.operational import OperationalDispatchAdapter
from .agents.service import AnalyticsService
from .agents.specialists import metric_at
from .agents.tools.common import ObservationContext
from .agents.tools.contextual import PostgresAnalyticsTools
from .agents.tools.registry import ScopedToolRegistry
from .database import connect, initialize
from .dispatch import make_dispatch_handler
from .events.fixtures import BLOCKED, CAMERA_OF, MINUTES, OPEN, RUN_ID, STORE, generate
from .events.ingest import TABLES, validate
from .operations import run_cycle
from .store_core import now_iso, seed_defaults

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "fyp2-plan" / "evidence" / "acceptance_rehearsal_synthetic.json"
DAY = TimeWindow(start=OPEN, end=OPEN + timedelta(minutes=MINUTES))
BLIND = (OPEN + timedelta(minutes=BLOCKED[1]), OPEN + timedelta(minutes=BLOCKED[2]))
SOURCES = ("footfall", "zone_dwell", "interactions", "unattended_episodes")
MANAGER = TrustedAccessScope(actor_id="acceptance-rehearsal-manager", store_id=STORE, role="manager")


def window(start_min: float, end_min: float) -> TimeWindow:
    return TimeWindow(start=OPEN + timedelta(minutes=start_min), end=OPEN + timedelta(minutes=end_min))


def check(name: str, passed: bool, detail="") -> dict:
    return {"check": name, "passed": bool(passed), "detail": detail}


def scenario(sid: str, title: str, checks: list[dict], evidence: dict | None = None, runnable=True, note="") -> dict:
    status = "not_runnable" if not runnable else "rehearsal_pass" if checks and all(c["passed"] for c in checks) else "rehearsal_fail"
    return {"id": sid, "scenario": title, "status": status, "synthetic": True, "checks": checks, "evidence": evidence or {}, "note": note}


def tools(dsn: str) -> PostgresAnalyticsTools:
    """Server-side observation contexts for the fixture layout: every zone, its camera, open 09-21 UTC."""
    contexts = tuple(ObservationContext(context_id=f"synthetic-{zone}", store_id=STORE, zone_id=zone, camera_ids=(camera,),
                                        available_sources=SOURCES, operating_windows=(DAY,))
                     for zone, camera in sorted(CAMERA_OF.items()))
    return PostgresAnalyticsTools(dsn, synthetic=True, contexts=contexts)


def union_seconds(intervals, lo, hi) -> float:
    spans = sorted((max(a, lo), min(b, hi)) for a, b in intervals if b > lo and a < hi)
    total, end = 0.0, lo
    for a, b in spans:
        a = max(a, end)
        if b > a:
            total, end = total + (b - a).total_seconds(), b
    return total


# ---- A1 ---------------------------------------------------------------------------------------------------------

def a1(dsn):
    with connect(dsn) as conn:
        counts = generate(conn)
    with connect(dsn) as conn:
        problems = validate(conn)
        rows = {t: conn.execute(f"SELECT COUNT(*) AS n FROM {t} WHERE run_id = %s", (RUN_ID,)).fetchone()["n"] for t in TABLES}
        ids = conn.execute("SELECT COUNT(*) AS n FROM tracks WHERE run_id = %s AND (store_id <> %s OR camera_id IS NULL)",
                           (RUN_ID, STORE)).fetchone()["n"]
        health = {r["camera_id"]: r["n"] for r in conn.execute(
            "SELECT camera_id, COUNT(DISTINCT ts_start) AS n FROM pipeline_health WHERE run_id = %s GROUP BY camera_id", (RUN_ID,))}
    checks = [check("rows land in every event table", all(rows.values()), rows),
              check("validate() returns []", problems == [], problems),
              check("rows carry the run, store and camera IDs", ids == 0, f"{ids} track rows with a wrong store or no camera"),
              check("health rows cover the whole day for every camera", all(health.get(c) == MINUTES for c in ("c1", "c2", "c3")),
                    {c: f"{n}/{MINUTES} minutes" for c, n in health.items()})]
    return scenario("A1", "Recorded clip to events", checks, {"generated": counts, "rows_by_table": rows},
                    note="CV inference is replaced by the fixture generator; `ingest --camera` on real CV output is not exercised.")


# ---- A2 / A3 ----------------------------------------------------------------------------------------------------

def a2():
    checks = []
    try:
        CellObservation(cell_id="z3-cell", window=window(0, 1), observed_s=60)
        checks.append(check("an observation without map_version is rejected", False))
    except Exception:
        checks.append(check("an observation without map_version is rejected", True))
    from .agents.business.occupancy import classify
    unmapped = CellObservation(cell_id="outside", window=window(0, 1), mapped=False, observed_s=60, map_version="v0")
    checks.append(check("an unmapped cell is masked as 'unmapped'", classify(unmapped) == (None, "unmapped"), classify(unmapped)))
    return scenario("A2", "Events to map", checks, runnable=False,
                    note="Blocked: no map registration (MAP-2) exists to project events onto the supplied map; only the "
                         "CellObservation contract is checked.")


def a3(dsn):
    """z3 as one cell: presence from stored zone_dwell, observed seconds from camera c2's stored health rows."""
    with connect(dsn) as conn:
        dwell = conn.execute("SELECT role, ts_start, ts_end FROM zone_dwell WHERE run_id = %s AND zone_id = 'z3'", (RUN_ID,)).fetchall()
        dark = {r["ts_start"] for r in conn.execute(
            "SELECT ts_start FROM pipeline_health WHERE run_id = %s AND camera_id = 'c2' AND frozen_or_dark = 1", (RUN_ID,))}
    by_role = {role: [(r["ts_start"], r["ts_end"]) for r in dwell if r["role"] == role] for role in ("customer", "employee")}
    tracker, states = OccupancyTracker(), []
    for minute in range(MINUTES):
        w = window(minute, minute + 1)
        observed = 0.0 if w.start in dark else 60.0
        states.append(tracker.update(CellObservation(
            cell_id="z3-whole-zone", window=w, observed_s=observed, map_version="synthetic-zone-as-cell-v0",
            customer_s=union_seconds(by_role["customer"], w.start, w.end) if observed else 0.0,
            employee_s=union_seconds(by_role["employee"], w.start, w.end) if observed else 0.0)))
    held = [s.window.start.isoformat() for prev, s in zip(states, states[1:])
            if prev.category == "customer" and prev.pending == "no_one" and s.category == "no_one"]
    immediate = [s.window.start.isoformat() for prev, s in zip(states, states[1:])
                 if prev.category == "customer" and s.observed_category == "no_one" and s.category == "no_one" and prev.pending is None]
    both = [s.window.start.isoformat() for s in states if s.category == "customer_employee"]
    blind = [s for s in states if BLIND[0] <= s.window.start < BLIND[1]]
    checks = [check("customer -> no_one happens only after the 2-window hold", bool(held) and not immediate,
                    {"held_transitions": len(held), "first": held[:3], "changed_without_hold": immediate[:3]}),
              check("staff plus a customer shows customer_employee", bool(both), {"windows": len(both), "first": both[:3]}),
              check("the blocked lens gives insufficient_coverage, never no_one",
                    bool(blind) and all(s.quality == "insufficient_coverage" and s.category is None for s in blind),
                    {"blocked_windows": len(blind), "qualities": sorted({s.quality for s in blind})})]
    counts = {c: sum(s.category == c for s in states) for c in ("customer", "employee", "customer_employee", "no_one", None)}
    return scenario("A3", "Live categories", checks, {"published_minutes": {str(k): v for k, v in counts.items()}},
                    note="Input cells are the fixture's z3 zone as a single cell, standing in for MAP-2 projected cells.")


# ---- A4 ---------------------------------------------------------------------------------------------------------

def grounded(run) -> tuple[int, list[str]]:
    bad = []
    for claim in run.claims:
        metric = metric_at(run.tool_results[claim.call_id], claim.path)
        if metric.value is None or abs(metric.value - claim.value) > 1e-9:
            bad.append(f"{claim.call_id}{list(claim.path)}: claim {claim.value} vs metric {metric.value}")
    return len(run.claims), bad


def a4(dsn):
    service = AnalyticsService(tools(dsn), specialists=business_specialists())
    runs = [service.ask(AskRequest(question=q, window=DAY), scope=MANAGER)
            for q in ("Summarise customers today", "Where are the staffing gaps?")]
    checks, evidence = [], {}
    for run in runs:
        n, bad = grounded(run)
        q = run.request.question
        evidence[q] = {"status": run.status, "development_stub": run.development_stub, "claims": n,
                       "tools": sorted({r.tool for r in run.tool_results.values()}), "limitations": list(run.limitations)[:6]}
        checks += [check(f'"{q}": development_stub=false', run.development_stub is False),
                   check(f'"{q}": answered with grounded claims', run.status in ("ok", "partial") and n > 0, f"status {run.status}, {n} claims"),
                   check(f'"{q}": every number matches a tool metric', not bad, bad[:5]),
                   check(f'"{q}": caveats shown', bool(run.limitations), f"{len(run.limitations)} limitations")]
    return scenario("A4", "Manager question", checks, evidence,
                    note="Clip Review confirmation of cited interactions needs recordings; not part of this rehearsal."), runs


# ---- A5-A8 ------------------------------------------------------------------------------------------------------

def add_floater(dsn, user_id="u_rehearsal_floater"):
    ts = now_iso()
    with connect(dsn) as conn:
        conn.execute("INSERT INTO users(id, name, email, role, password_hash, active, created_at, updated_at) "
                     "VALUES (%s, 'Rehearsal Floater', 'floater@rehearsal.local', 'Employee', 'x', 1, %s, %s)", (user_id, ts, ts))
        conn.execute("INSERT INTO rosters(id, user_id, zone_id, shift, available, created_at, updated_at) "
                     "VALUES (%s, %s, NULL, 'all day', 1, %s, %s)", (f"r_{user_id}", user_id, ts, ts))
    return user_id


def counts(dsn) -> dict:
    with connect(dsn) as conn:
        return {t: conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
                for t in ("orchestration_events", "dispatch_decisions", "alerts", "tasks")}


def find_window(registry, wanted: str, candidates) -> TimeWindow | None:
    """First candidate window whose z3 unattended decision has the wanted reason (pure policy, nothing dispatched)."""
    for w in candidates:
        if evaluate_zone(registry, "z3", w, w.end + timedelta(seconds=1))[0].reason == wanted:
            return w
    return None


def cycle(dsn, registry, w):
    adapter = OperationalDispatchAdapter(make_dispatch_handler(dsn))
    return run_cycle(registry, ["z3"], w, w.end + timedelta(seconds=1), adapter=adapter, allow_synthetic=True)


def receipts_of(result):
    return [{"event": r.event_id[:16], "key": r.idempotency_key[:16], "decision": r.decision, "task": r.task_id,
             "employee": r.selected_employee_id, "reason_code": r.reason_code} for r in result["receipts"]]


def a5_to_a8(dsn):
    registry = ScopedToolRegistry(tools(dsn), MANAGER)
    hours = [window(h * 60, h * 60 + 60) for h in range(12)]
    clear = [w for w in hours if not (w.start < BLIND[1] and w.end > BLIND[0])]
    floater = add_floater(dsn)
    out = {}

    # A5: unattended wait in z3 -> eligible employee gets a task, visible to the manager as an alert + task.
    w5 = find_window(registry, "emitted", clear)
    before = counts(dsn)
    r5 = cycle(dsn, registry, w5) if w5 else {"receipts": [], "suppressed": []}
    after = counts(dsn)
    unattended5 = r5["receipts"][:1]  # run_cycle handles the zone's unattended decision before its unstaffed one
    with connect(dsn) as conn:
        visible = conn.execute("SELECT t.id, t.employee_id, t.target_zone_id, t.state, a.category, a.status FROM tasks t "
                               "JOIN alerts a ON a.id = t.trigger_alert_id WHERE t.target_zone_id = 'z3'").fetchall()
    first = unattended5[0] if unattended5 else None
    out["A5"] = scenario("A5", "Unattended to eligible employee", [
        check("a window with an unhelped z3 wait >= min_wait_s exists", w5 is not None, w5 and f"{w5.start:%H:%M}-{w5.end:%H:%M} UTC"),
        check("evaluate_zone emits unattended_customer and the adapter calls the real handler",
              bool(first) and first.handler_invoked and first.reason_code == "handler_reported", receipts_of(r5)),
        check("an eligible employee gets a task", bool(first) and first.decision == "dispatched" and first.selected_employee_id == floater,
              first and {"decision": first.decision, "employee": first.selected_employee_id}),
        check("the manager view shows it (alert + task rows)", bool(visible) and visible[0]["category"] == "Unattended Customers",
              [dict(v) for v in visible][:2]),
    ], {"window": w5 and [w5.start.isoformat(), w5.end.isoformat()], "rows_before": before, "rows_after": after,
        "suppressed": r5["suppressed"]})

    # A7: replay A5's window -> same idempotency key, outcome duplicate, still one task.
    tasks_before = counts(dsn)["tasks"]
    r7 = cycle(dsn, registry, w5) if w5 else {"receipts": [], "suppressed": []}
    same_key = bool(first) and r7["receipts"] and r7["receipts"][0].idempotency_key == first.idempotency_key
    with connect(dsn) as conn:
        events_for_key = conn.execute("SELECT COUNT(*) AS n FROM orchestration_events WHERE dedupe_key = %s",
                                      (first.idempotency_key if first else "",)).fetchone()["n"]
    out["A7"] = scenario("A7", "Duplicate event", [
        check("same idempotencyKey", bool(same_key)),
        check("outcome duplicate", bool(r7["receipts"]) and r7["receipts"][0].decision == "duplicate", receipts_of(r7)),
        check("still one task", counts(dsn)["tasks"] == tasks_before and events_for_key == 1,
              {"tasks_before": tasks_before, "tasks_after": counts(dsn)["tasks"], "events_with_key": events_for_key}),
    ])

    # A6: nobody on shift for the zone -> no_eligible_employee, no task, the manager is told (alert).
    with connect(dsn) as conn:
        conn.execute("UPDATE tasks SET state = 'completed'")  # close A5's task so the zone is not 'already assigned'
        conn.execute("UPDATE rosters SET available = 0")
    w6 = find_window(registry, "emitted", [w for w in clear if w != w5])
    before6 = counts(dsn)
    r6 = cycle(dsn, registry, w6) if w6 else {"receipts": [], "suppressed": []}
    after6 = counts(dsn)
    first6 = r6["receipts"][0] if r6["receipts"] else None
    out["A6"] = scenario("A6", "No eligible employee", [
        check("outcome no_eligible_employee", bool(first6) and first6.decision == "no_eligible_employee", receipts_of(r6)),
        check("no task created", after6["tasks"] == before6["tasks"], {"before": before6["tasks"], "after": after6["tasks"]}),
        check("the manager is told (alert raised)", after6["alerts"] > before6["alerts"], {"before": before6["alerts"], "after": after6["alerts"]}),
    ], {"window": w6 and [w6.start.isoformat(), w6.end.isoformat()]})

    # A8: camera c2 blocked during a z3 wait -> suppressed with unknown_observation_too_high, no task.
    with connect(dsn) as conn:
        conn.execute("UPDATE rosters SET available = 1")  # someone could be sent, so only the policy can stop it
    blind_windows = [window(BLOCKED[1] - pre, BLOCKED[2] + post) for pre in (60, 45, 30, 20, 10) for post in (0, 10, 20)]
    w8 = find_window(registry, "unknown_observation_too_high", blind_windows)
    before8 = counts(dsn)
    r8 = cycle(dsn, registry, w8) if w8 else {"receipts": [], "suppressed": []}
    after8 = counts(dsn)
    reasons8 = [s for s in r8["suppressed"] if s["eventType"] == "unattended_customer"]
    out["A8"] = scenario("A8", "Blind camera", [
        check("a z3 wait overlaps the c2 blackout", w8 is not None, w8 and f"{w8.start:%H:%M}-{w8.end:%H:%M} UTC"),
        check("policy suppresses with unknown_observation_too_high",
              bool(reasons8) and reasons8[0]["reason"] == "unknown_observation_too_high", r8["suppressed"]),
        check("no task", after8["tasks"] == before8["tasks"] and not r8["receipts"], {"before": before8["tasks"], "after": after8["tasks"]}),
    ], {"window": w8 and [w8.start.isoformat(), w8.end.isoformat()]},
        note="The digest caveat naming the blind time is checked under A9.")
    return out, registry, w5


# ---- A9 / A10 ---------------------------------------------------------------------------------------------------

def a9(runs, registry, w5):
    decisions = evaluate_zone(registry, "z3", DAY, DAY.end + timedelta(seconds=1)) if registry else ()
    digest = build_digest(runs, title="Rehearsal digest (synthetic)", decisions=decisions)
    text = digest.text()
    check_numbers = verify_narrative("\n".join(line for s in digest.sections for line in s.lines), runs)
    caveats = "\n".join(digest.caveats)
    blind = re.findall(r"[^\n]*(?:blocked|dark|frozen|blind|unhealthy|unobserved)[^\n]*", caveats)
    blind_time = f"{BLIND[0]:%H:%M}"
    checks = [check("digest built from the A4 runs plus z3 decisions", bool(digest.sections),
                    [s.heading for s in digest.sections]),
              check("all figures match the claims (verify_narrative)", check_numbers.supported,
                    list(check_numbers.unsupported_numbers)),
              check("synthetic provenance is labelled, never shown as real", digest.provenance == "synthetic", digest.provenance),
              check("a caveat says the camera was blocked", bool(blind), blind[:3]),
              check(f"the caveat names the blind time ({blind_time}-{BLIND[1]:%H:%M} UTC)", blind_time in caveats,
                    "the coverage caveat is generic: it does not say when the camera was blind")]
    return scenario("A9", "Digest", checks, {"status": digest.status, "citations": digest.citation_count, "text": text.splitlines()[:40]},
                    note="Acceptance requires provenance 'real' with no FIXTURE caveat; on synthetic data the correct result is "
                         "the opposite, which is what is checked here.")


def a10(dsn):
    with connect(dsn) as conn:
        rows = conn.execute("SELECT event_id, run_id, store_id, camera_id, zone_id, ts_start, ts_end, verdict "
                            "FROM interactions WHERE run_id = %s ORDER BY ts_start", (RUN_ID,)).fetchall()
    candidates = from_interaction_rows([{**r, "ts_start": r["ts_start"].isoformat(), "ts_end": r["ts_end"].isoformat()} for r in rows],
                                       synthetic=True)
    items = review_items(candidates[:30], sources=(), blind=True)
    checks = [check("at least 30 confirmed interactions to sample", len(candidates) >= 30, len(candidates)),
              check("review items are blind (no CV verdict shown)", all(i.cv_verdict is None for i in items)),
              check("without a recording map every item says why it cannot play",
                    all(i.clip is None and i.unavailable_reason == "no_recording" for i in items), len(items))]
    return scenario("A10", "Clip Review precision", checks, {"candidates": len(candidates), "sampled": len(items)}, runnable=False,
                    note="Blocked: precision and Cohen's kappa need two human reviewers watching recorded clips, and the "
                         "run-to-recording map (S) does not exist. Only the blind sampling step is rehearsed.")


# ---- main -------------------------------------------------------------------------------------------------------

def run(url: str, schema: str) -> dict:
    ident = sql.Identifier(schema)
    with connect(url) as admin:
        admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(ident))
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(ident))
    dsn = make_conninfo(url, options=f"-csearch_path={schema}")
    with connect(dsn) as conn:
        initialize(conn)
        seed_defaults(conn)
    results = [a1(dsn), a2(), a3(dsn)]
    r4, runs = a4(dsn)
    results.append(r4)
    dispatch, registry, w5 = a5_to_a8(dsn)
    results += [dispatch["A5"], dispatch["A6"], dispatch["A7"], dispatch["A8"], a9(runs, registry, w5), a10(dsn)]
    return {"kind": "acceptance_rehearsal", "synthetic": True, "not_acceptance": True,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "fixture_run": RUN_ID,
            "database_schema": schema, "policy": SignalPolicy().model_dump(),
            "summary": {r["id"]: r["status"] for r in results}, "scenarios": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Rehearse acceptance A1-A10 on the synthetic fixture day (not acceptance).")
    parser.add_argument("--schema", default="acceptance_synthetic")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--drop", action="store_true", help="Drop the rehearsal schema and exit")
    args = parser.parse_args()
    # The schema is selected with a search_path startup option, which pooled endpoints (e.g. Neon -pooler) reject.
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("Set TEST_DATABASE_URL (a direct, unpooled connection) or DATABASE_URL")
    if args.drop:
        with connect(url) as admin:
            admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(args.schema)))
        print(f"dropped schema {args.schema}")
        return
    report = run(url, args.schema)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    for s in report["scenarios"]:
        print(f"{s['id']:>4}  {s['status']:<15} {s['scenario']}")
        for c in s["checks"]:
            print(f"        {'ok  ' if c['passed'] else 'FAIL'} {c['check']}")
    print(f"report: {args.output}")


if __name__ == "__main__":
    main()
