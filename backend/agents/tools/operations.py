"""Scoped readers for dated queue samples and camera-health observations."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from ..contracts import (Contract, CountMetric, Evidence, Identifier, MAX_RESULTS, Metric,
                         ResultContext, SecondsMetric, ToolRequest)
from .analytics import EventAnalytics
from .store import SourceUnavailable, read_session


class QueueSample(Contract):
    camera_id: Identifier
    zone_id: Identifier
    observed_at: datetime
    queue_length: CountMetric
    estimated_wait_seconds: SecondsMetric
    evidence: Evidence


class PipelineHealthSample(Contract):
    camera_id: Identifier
    observed_from: datetime
    observed_to: datetime
    fps: Metric
    mean_confidence: float | None = Field(ge=0, le=1)
    unknown_role_share: float | None = Field(ge=0, le=1)
    id_churn: int = Field(ge=0, strict=True)
    frozen_or_dark: Literal[0, 1] | None
    evidence: Evidence


class QueueResult(ResultContext):
    tool: Literal["get_queue"] = "get_queue"
    samples: tuple[QueueSample, ...] = Field(default=(), max_length=MAX_RESULTS)


class PipelineHealthResult(ResultContext):
    tool: Literal["get_pipeline_health"] = "get_pipeline_health"
    samples: tuple[PipelineHealthSample, ...] = Field(default=(), max_length=MAX_RESULTS)


class OperationsAnalytics(EventAnalytics):
    """Read committed event rows; no configuration, alert or dispatch writes."""

    def get_queue(self, *, scope, request: ToolRequest) -> QueueResult:
        return self._read(scope, request, "queue_samples", QueueResult, self._queue_sample,
                          "Queue wait is a heuristic. A sample is not a measured customer wait.")

    def get_pipeline_health(self, *, scope, request: ToolRequest) -> PipelineHealthResult:
        return self._read(scope, request, "pipeline_health", PipelineHealthResult, self._health_sample,
                          "Missing health fields are unknown; absence of samples does not establish camera health.")

    def _read(self, scope, request, table, result_type, make_sample, caveat):
        context = self._context(scope, request, status="empty")
        name = result_type.model_fields["tool"].default
        try:
            with read_session(self.dsn) as session:
                rows = session.rows(table, scope, request.filters, request.window)
                samples = tuple(make_sample(row, Evidence(source=table, query=name, ids=(row["event_id"],),
                                                           matched_count=1)) for row in rows[:request.limit])
        except (SourceUnavailable, ValueError):
            return result_type(**(context | {"status": "unavailable", "limitations": (f"Cannot provide reliable {table} samples",)}))
        truncated = len(rows) > request.limit
        return result_type(**(context | {
            "status": "partial" if truncated else "ok" if samples else "empty",
            "limitations": (caveat, "Sample rows truncated") if truncated else (caveat,),
            "truncated": truncated,
        }), samples=samples)

    @staticmethod
    def _queue_sample(row, evidence):
        return QueueSample(camera_id=row["camera_id"], zone_id=row["zone_id"], observed_at=row["_start"],
                           queue_length=CountMetric(value=float(row["queue_length"]), evidence=(evidence,)),
                           estimated_wait_seconds=SecondsMetric(
                               value=row["est_wait_s"], estimated=True, evidence=(evidence,),
                               unavailable_reason="Estimated wait is unavailable" if row["est_wait_s"] is None else None,
                           ), evidence=evidence)

    @staticmethod
    def _health_sample(row, evidence):
        return PipelineHealthSample(camera_id=row["camera_id"], observed_from=row["_start"], observed_to=row["_end"],
                                    fps=Metric(value=row["fps"], unit="fps", evidence=(evidence,)), mean_confidence=row["mean_confidence"],
                                    unknown_role_share=row["unknown_role_share"], id_churn=row["id_churn"],
                                    frozen_or_dark=row["frozen_or_dark"], evidence=evidence)
