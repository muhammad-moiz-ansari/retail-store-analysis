"""Operational producer cycle: Ruhab's signal policy -> Moiz's adapter -> Saqib's dispatch handler.

For each zone, evaluate_zone decides whether a completed window is an unattended_customer or unstaffed_zone event;
each emitted event goes through OperationalDispatchAdapter to the real handler (backend.dispatch). Run it after a
window closes (for example from a scheduler); repeats are safe because the handler deduplicates on idempotencyKey.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .agents.business.signal_policy import SignalPolicy, evaluate_zone
from .agents.operational import OperationalDispatchAdapter, TrustedOperationalScope
from .dispatch import STORE_ID, make_dispatch_handler

SERVICE_ID = "retailpulse-operations"


def run_cycle(registry, zone_ids, window, now: datetime, *, adapter=None, policy=SignalPolicy(), allow_synthetic=False) -> dict:
    """Returns the adapter receipts and the reason every non-emitted decision was suppressed.
    Synthetic (fixture) evidence never dispatches real tasks unless allow_synthetic is set (demo only)."""
    adapter = adapter or OperationalDispatchAdapter(make_dispatch_handler())
    scope = TrustedOperationalScope(service_id=SERVICE_ID, store_id=STORE_ID, allowed_zone_ids=tuple(zone_ids))
    receipts, suppressed = [], []
    for zone_id in zone_ids:
        for decision in evaluate_zone(registry, zone_id, window, now, policy):
            if decision.event is None:
                suppressed.append({"zoneId": zone_id, "eventType": decision.event_type, "reason": decision.reason})
            elif decision.event.evidence.demand.synthetic and not allow_synthetic:
                suppressed.append({"zoneId": zone_id, "eventType": decision.event_type, "reason": "synthetic_not_dispatched"})
            else:
                receipts.append(adapter.handle(decision.event, scope=scope))
    return {"receipts": receipts, "suppressed": suppressed}


def cycle_from_config(config, user_id: str | None, zone_ids, window, now: datetime, *, dry_run: bool, allow_synthetic: bool) -> dict:
    """One cycle over the operator's dashboard configuration (the same file the dashboard reads), so scope, runs,
    cameras and observation context are exactly what the manager sees. `dry_run` evaluates the policy and dispatches nothing."""
    from .agents.tools.contextual import PostgresAnalyticsTools
    from .agents.tools.registry import ScopedToolRegistry

    membership = next((m for m in config.memberships if user_id is None or m.user_id == user_id), None)
    if membership is None or (user_id is None and len(config.memberships) != 1):
        raise SystemExit("Name the manager with --user-id (the configuration has no single membership to default to)")
    if membership.store_id != STORE_ID:
        raise SystemExit(f"Configured store {membership.store_id!r} is not this backend's RETAILPULSE_STORE_ID {STORE_ID!r}")
    zones = list(zone_ids or membership.zone_ids)
    if not set(zones) <= set(membership.zone_ids):
        raise SystemExit("A zone is outside the manager's configured membership")
    window = window or membership.default_request.window
    tools = PostgresAnalyticsTools(synthetic=config.synthetic, contexts=config.contexts,
                                   verified_unattended_runs=config.verified_unattended_runs)
    registry = ScopedToolRegistry(tools, membership.scope())
    if dry_run:
        return {"decisions": [{"zoneId": z, "eventType": d.event_type, "reason": d.reason, "emitted": d.event is not None}
                              for z in zones for d in evaluate_zone(registry, z, window, now)]}
    return run_cycle(registry, zones, window, now, allow_synthetic=allow_synthetic)


def main() -> None:
    from .agents.dashboard import DashboardConfig
    from .agents.contracts import TimeWindow

    parser = argparse.ArgumentParser(description="Evaluate closed windows with the signal policy and dispatch the events it emits.")
    parser.add_argument("--config", type=Path, required=True, help="The dashboard analytics configuration JSON (RETAILPULSE_ANALYTICS_CONFIG)")
    parser.add_argument("--user-id", help="Manager whose membership scopes the cycle; optional when the file has one membership")
    parser.add_argument("--zones", nargs="+", help="Default: every zone in the membership")
    parser.add_argument("--start", type=datetime.fromisoformat, help="Window start, ISO 8601 with offset (default: the membership's window)")
    parser.add_argument("--end", type=datetime.fromisoformat, help="Window end, ISO 8601 with offset")
    parser.add_argument("--dry-run", action="store_true", help="Print the policy's decisions; dispatch nothing")
    parser.add_argument("--allow-synthetic", action="store_true", help="Dispatch even when the configuration attests synthetic data (demo only)")
    args = parser.parse_args()
    if bool(args.start) != bool(args.end):
        parser.error("--start and --end go together")
    window = TimeWindow(start=args.start, end=args.end) if args.start else None
    config = DashboardConfig.model_validate_json(args.config.read_text(encoding="utf-8"))
    result = cycle_from_config(config, args.user_id, args.zones, window, datetime.now(timezone.utc),
                               dry_run=args.dry_run, allow_synthetic=args.allow_synthetic)
    print(json.dumps(result, indent=2, default=lambda o: o.model_dump(mode="json") if hasattr(o, "model_dump") else str(o)))


if __name__ == "__main__":
    main()
