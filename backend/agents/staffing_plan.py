"""Advisory next-day zone staffing from trusted, cited inputs."""

from datetime import datetime, timedelta
from math import ceil
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field

from .contracts import Contract, Evidence, Identifier, TimeWindow, TrustedAccessScope


class ShiftInputs(Contract):
    zone_id: Identifier
    shift_id: Identifier
    window: TimeWindow
    forecast_customers: float | None = Field(ge=0)
    forecast_evidence: tuple[Evidence, ...] = Field(default=(), max_length=10)
    historical_staffed_ratio: float | None = Field(ge=0, le=1)
    coverage_evidence: tuple[Evidence, ...] = Field(default=(), max_length=10)
    rostered_staff: int | None = Field(ge=0, strict=True)
    minimum_staff: int = Field(ge=0, le=1000, strict=True)


class ZoneProposal(Contract):
    zone_id: Identifier
    shift_id: Identifier
    window: TimeWindow
    suggested_staff: int | None
    additional_staff: int | None
    historical_staffed_ratio: float | None
    evidence: tuple[Evidence, ...]
    missing_inputs: tuple[str, ...]


class StaffingProposal(Contract):
    store_id: Identifier
    approval_required: Literal[True] = True
    zones: tuple[ZoneProposal, ...]


def propose_next_day(scope: TrustedAccessScope, shifts: tuple[ShiftInputs, ...], *,
                     as_of: datetime, timezone_name: str, customers_per_employee: int) -> StaffingProposal:
    """Produce counts for later approval. The trusted caller supplies facts and policy."""
    if scope.role != "manager" or scope.allowed_zone_ids is None:
        raise PermissionError("Staffing proposal requires explicit zone authority")
    if as_of.utcoffset() is None or type(customers_per_employee) is not int or customers_per_employee <= 0:
        raise ValueError("A timezone-aware timestamp and positive staffing capacity are required")
    if not 1 <= len(shifts) <= 100:
        raise ValueError("Provide one to one hundred shifts")

    timezone = ZoneInfo(timezone_name)
    next_day = as_of.astimezone(timezone).date() + timedelta(days=1)
    proposals = []
    seen = set()
    for shift in shifts:
        key = (shift.zone_id, shift.shift_id)
        if shift.zone_id not in scope.allowed_zone_ids:
            raise PermissionError("Shift is outside the manager zone scope")
        start = shift.window.start.astimezone(timezone)
        last_instant = (shift.window.end - timedelta(microseconds=1)).astimezone(timezone)
        if key in seen or start.date() != next_day or last_instant.date() != next_day:
            raise ValueError("Shifts must be unique and fit within the next local day")
        seen.add(key)

        missing = []
        if shift.forecast_customers is None or not shift.forecast_evidence:
            missing.append("footfall_forecast")
        if shift.historical_staffed_ratio is None or not shift.coverage_evidence:
            missing.append("historical_coverage")
        if shift.rostered_staff is None:
            missing.append("roster")

        suggested = additional = None
        if not missing and shift.forecast_customers is not None and shift.rostered_staff is not None:
            suggested = max(shift.minimum_staff, ceil(shift.forecast_customers / customers_per_employee))
            additional = max(0, suggested - shift.rostered_staff)
        proposals.append(ZoneProposal(
            zone_id=shift.zone_id, shift_id=shift.shift_id, window=shift.window,
            suggested_staff=suggested, additional_staff=additional,
            historical_staffed_ratio=shift.historical_staffed_ratio if shift.coverage_evidence else None,
            evidence=tuple({ref.model_dump_json(): ref for ref in (*shift.forecast_evidence, *shift.coverage_evidence)}.values()),
            missing_inputs=tuple(missing),
        ))
    return StaffingProposal(store_id=scope.store_id, zones=tuple(proposals))
