"""Phase 1 contracts over backend/events/schema.sql; no database or provider I/O.

TrustedAccessScope is constructed by a trusted server adapter, never by parsing
the manager's tool arguments. Pydantic validation does not authenticate a user.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(strict=True, min_length=1, max_length=200, pattern=r"^\S(?:.*\S)?$")]
TableName = Literal["tracks", "role_decisions", "interactions", "zone_dwell", "footfall",
                    "queue_samples", "unattended_episodes", "pipeline_health", "heatmaps"]
ToolName = Literal["get_footfall", "get_zone_dwell", "get_interactions", "get_unattended", "get_coverage"]
MAX_WINDOW = timedelta(days=31)
MAX_RESULTS = 1000
MAX_EVIDENCE_IDS = 200
MAX_BUCKETS = 1000


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class TimeWindow(Contract):
    start: datetime
    end: datetime

    @field_validator("start", "end", mode="before")
    @classmethod
    def aware_iso_input(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError("Use a timezone-aware ISO timestamp, not an epoch or date")
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Naive dates/times are ambiguous; supply a timezone offset")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def bounded_window(self):
        if not timedelta(0) < self.end - self.start <= MAX_WINDOW:
            raise ValueError("Window must have start < end and span at most 31 days")
        return self


class EventFilters(Contract):
    run_id: Identifier | None = None
    camera_id: Identifier | None = None
    zone_id: Identifier | None = None


class TrustedAccessScope(Contract):
    actor_id: Identifier
    store_id: Identifier
    role: Literal["manager", "employee"]
    allowed_run_ids: tuple[Identifier, ...] | None = Field(default=None, min_length=1, max_length=1000)
    allowed_camera_ids: tuple[Identifier, ...] | None = Field(default=None, min_length=1, max_length=1000)
    allowed_zone_ids: tuple[Identifier, ...] | None = Field(default=None, min_length=1, max_length=1000)

    def validate_filters(self, filters: EventFilters) -> None:
        for key, allowed in (("run_id", self.allowed_run_ids), ("camera_id", self.allowed_camera_ids),
                             ("zone_id", self.allowed_zone_ids)):
            requested = getattr(filters, key)
            if requested is not None and allowed is not None and requested not in allowed:
                raise ValueError(f"Requested {key} is outside the trusted access scope")


class ToolRequest(Contract):
    window: TimeWindow
    filters: EventFilters = Field(default_factory=EventFilters)
    limit: int = Field(default=100, strict=True, ge=1, le=MAX_RESULTS)


class Granularity(str, Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


class FootfallRequest(ToolRequest):
    granularity: Granularity = Granularity.HOUR

    @model_validator(mode="after")
    def bounded_buckets(self):
        seconds = {Granularity.MINUTE: 60, Granularity.HOUR: 3600, Granularity.DAY: 86400}[self.granularity]
        # Buckets align to UTC wall-clock boundaries, including clipped edge buckets.
        count = int((self.window.end.timestamp() - 1e-6) // seconds - self.window.start.timestamp() // seconds + 1)
        if count > MAX_BUCKETS:
            raise ValueError("At most 1000 buckets; use a coarser granularity or shorter window")
        return self


class ZoneDwellRequest(ToolRequest):
    filters: EventFilters  # A zone is required rather than an ambiguous all-zone distribution.

    @model_validator(mode="after")
    def zone_required(self):
        if self.filters.zone_id is None:
            raise ValueError("get_zone_dwell requires filters.zone_id")
        return self


class InteractionsRequest(ToolRequest):
    pass


class UnattendedRequest(ToolRequest):
    min_seconds: float = Field(default=180, strict=True, ge=0, le=31 * 86400)


class CoverageRequest(ToolRequest):
    shift: Identifier | None = None  # Lookup key only; trusted operating context supplies its bounds.


class DataStatus(str, Enum):
    OK = "ok"
    EMPTY = "empty"
    UNAVAILABLE = "unavailable"
    PARTIAL = "partial"


class Evidence(Contract):
    source: TableName
    ids: tuple[Identifier, ...] = Field(min_length=1, max_length=MAX_EVIDENCE_IDS)
    query: ToolName
    matched_count: int = Field(strict=True, ge=1)
    truncated: bool = False

    @model_validator(mode="after")
    def consistent_sample(self):
        if len(set(self.ids)) != len(self.ids):
            raise ValueError("Evidence IDs must be unique")
        if self.matched_count < len(self.ids) or self.truncated != (self.matched_count > len(self.ids)):
            raise ValueError("Evidence truncation must disclose the full matched count")
        return self


class Metric(Contract):
    value: float | None = Field(strict=True)
    unit: Literal["count", "seconds", "ratio", "percent"]
    evidence: tuple[Evidence, ...] = Field(default=(), max_length=20)
    unavailable_reason: str | None = Field(default=None, min_length=1, max_length=1000)
    estimated: bool = False

    @field_validator("value", mode="before")
    @classmethod
    def numeric_not_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("A boolean is not a metric")
        return value

    @model_validator(mode="after")
    def supported_value(self):
        if self.value is None:
            if not self.unavailable_reason:
                raise ValueError("Unavailable metrics require a reason")
        else:
            if self.unavailable_reason is not None or self.value < 0:
                raise ValueError("Available metrics must be nonnegative and have no unavailable reason")
            if self.unit == "count" and not self.value.is_integer():
                raise ValueError("Counts must be integers")
            if self.unit == "ratio" and self.value > 1 or self.unit == "percent" and self.value > 100:
                raise ValueError("Ratio/percent outside its unit range")
            if not self.evidence:
                raise ValueError("Numeric metrics require their own event/observation evidence, including zero")
        return self


class CountMetric(Metric):
    unit: Literal["count"] = "count"


class SecondsMetric(Metric):
    unit: Literal["seconds"] = "seconds"


class RatioMetric(Metric):
    unit: Literal["ratio"] = "ratio"


class ResultContext(Contract):
    tool: ToolName
    scope: TrustedAccessScope
    window: TimeWindow
    filters: EventFilters = Field(default_factory=EventFilters)
    status: DataStatus
    synthetic: bool  # Explicit provenance from the selected database, not inferred from an ID prefix.
    limitations: tuple[Annotated[str, Field(min_length=1, max_length=2000)], ...] = Field(default=(), max_length=50)
    truncated: bool = False  # Result-row cap; separate from each metric's evidence sample cap.

    @model_validator(mode="after")
    def scoped_result(self):
        self.scope.validate_filters(self.filters)
        if self.status in (DataStatus.PARTIAL, DataStatus.UNAVAILABLE) and not self.limitations:
            raise ValueError("Partial/unavailable results require an explanation")
        def check(value):
            if isinstance(value, Evidence):
                if value.query != self.tool:
                    raise ValueError("Metric evidence must cite the tool that produced this result")
            elif isinstance(value, Metric):
                if self.status == DataStatus.UNAVAILABLE and value.value is not None:
                    raise ValueError("Unavailable results cannot contain numeric metrics")
                for item in value.evidence:
                    check(item)
            elif isinstance(value, BaseModel):
                for key in type(value).model_fields:
                    check(getattr(value, key))
            elif isinstance(value, tuple):
                for item in value:
                    check(item)
        for key in type(self).model_fields:
            check(getattr(self, key))
        return self


class FootfallBucket(Contract):
    window: TimeWindow
    entries: CountMetric
    exits: CountMetric


class FootfallResult(ResultContext):
    tool: Literal["get_footfall"] = "get_footfall"
    buckets: tuple[FootfallBucket, ...] = Field(default=(), max_length=MAX_RESULTS)
    occupancy: CountMetric


class DwellSummary(Contract):
    role: Literal["customer", "employee", "unknown"]
    sample_count: CountMetric
    total: SecondsMetric
    p50: SecondsMetric
    p90: SecondsMetric


class ZoneDwellResult(ResultContext):
    tool: Literal["get_zone_dwell"] = "get_zone_dwell"
    by_role: tuple[DwellSummary, ...] = Field(default=(), max_length=3)


class InteractionsResult(ResultContext):
    tool: Literal["get_interactions"] = "get_interactions"
    confirmed_count: CountMetric
    unverified_count: CountMetric
    mean_confirmed_duration: SecondsMetric
    mean_approach: SecondsMetric
    approach_reference: Literal["camera_first_seen"] = "camera_first_seen"
    approach_sample_count: CountMetric


class UnattendedEpisode(Contract):
    event_id: Identifier
    run_id: Identifier
    camera_id: Identifier
    zone_id: Identifier
    customer_track_id: int = Field(strict=True, ge=0)
    window: TimeWindow  # Clipped interval; zero-length overlaps are excluded.
    waited: SecondsMetric
    helped: bool
    provenance: Literal["stored_derivation_verdict_unfiltered"] = "stored_derivation_verdict_unfiltered"


class UnattendedResult(ResultContext):
    tool: Literal["get_unattended"] = "get_unattended"
    episodes: tuple[UnattendedEpisode, ...] = Field(default=(), max_length=MAX_RESULTS)
    episode_count: CountMetric


class CoverageSummary(Contract):
    zone_id: Identifier
    observed_staffed: SecondsMetric
    unknown_observation: SecondsMetric
    open_seconds: SecondsMetric
    staffed_open_ratio: RatioMetric
    evaluated_windows: tuple[TimeWindow, ...] = Field(default=(), max_length=100)
    operating_windows: tuple[TimeWindow, ...] = Field(default=(), max_length=100)
    operating_context_id: Identifier | None = None


class CoverageResult(ResultContext):
    tool: Literal["get_coverage"] = "get_coverage"
    zones: tuple[CoverageSummary, ...] = Field(default=(), max_length=MAX_RESULTS)
