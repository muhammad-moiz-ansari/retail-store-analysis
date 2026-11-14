"""Operational producer cycle: Ruhab's signal policy -> Moiz's adapter -> Saqib's dispatch handler.

For each zone, evaluate_zone decides whether a completed window is an unattended_customer or unstaffed_zone event;
each emitted event goes through OperationalDispatchAdapter to the real handler (backend.dispatch). Run it after a
window closes (for example from a scheduler); repeats are safe because the handler deduplicates on idempotencyKey.
"""

from __future__ import annotations

from datetime import datetime

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
