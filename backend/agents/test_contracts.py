"""Offline Phase 1 validation. No SQL tools, CV models, or live providers."""
import json
import inspect
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.events.fixtures import RUN_ID, generate
from backend.events.ingest import connect, validate
from .contracts import (CountMetric, CoverageRequest, CoverageResult, DataStatus, EventFilters,
                        Evidence, FootfallRequest, FootfallResult, InteractionsRequest,
                        InteractionsResult, Metric, SecondsMetric, TimeWindow, TrustedAccessScope,
                        UnattendedRequest, UnattendedResult, ZoneDwellRequest, ZoneDwellResult)

WINDOW = {"start": "2026-11-03T09:00:00Z", "end": "2026-11-03T21:00:00Z"}


def scope(**kwargs):
    return TrustedAccessScope(actor_id="manager-1", store_id="store-1", role="manager", **kwargs)


def test_offsets_are_normalized_and_roundtrip():
    window = TimeWindow(start="2026-11-03T14:00:00+05:00", end="2026-11-03T11:00:00+00:00")
    assert window.start == datetime(2026, 11, 3, 9, tzinfo=timezone.utc)
    assert window.model_dump(mode="json")["start"] == "2026-11-03T09:00:00Z"
    assert TimeWindow.model_validate_json(window.model_dump_json()) == window


@pytest.mark.parametrize("start,end", [
    ("2026-11-03", WINDOW["end"]), ("2026-11-03T09:00:00", WINDOW["end"]),
    (datetime(2026, 11, 3, 9), WINDOW["end"]), (1793696400, WINDOW["end"]),
    (WINDOW["end"], WINDOW["start"]), (WINDOW["start"], WINDOW["start"]),
    (WINDOW["start"], "2026-12-05T09:00:00Z"), ("bad", WINDOW["end"]),
])
def test_ambiguous_invalid_or_excessive_windows_rejected(start, end):
    with pytest.raises(ValidationError):
        TimeWindow(start=start, end=end)


@pytest.mark.parametrize("kwargs", [{"store_id": "other"}, {"limit": 0}, {"limit": 1001},
                                     {"limit": True}, {"limit": "100"}, {"granularity": "week"}])
def test_untrusted_scope_and_invalid_limits_rejected(kwargs):
    with pytest.raises(ValidationError):
        FootfallRequest(window=WINDOW, **kwargs)


def test_bucket_cap_and_utc_edge_buckets():
    assert FootfallRequest(window=WINDOW, granularity="minute").limit == 100
    with pytest.raises(ValidationError):
        FootfallRequest(window={"start": WINDOW["start"], "end": "2026-11-05T09:00:00Z"}, granularity="minute")
    # 1000 minutes of duration, but 1001 partial/full UTC-aligned buckets.
    with pytest.raises(ValidationError):
        FootfallRequest(window={"start": "2026-11-03T09:00:30Z", "end": "2026-11-04T01:40:30Z"}, granularity="minute")


def test_scope_allowlists_and_immutable_identity():
    access = scope(allowed_run_ids=(RUN_ID,), allowed_camera_ids=("c2",), allowed_zone_ids=("z3",))
    access.validate_filters(EventFilters(run_id=RUN_ID, camera_id="c2", zone_id="z3"))
    access.validate_filters(EventFilters())  # Reader must still apply all three allowlists.
    for filters in (EventFilters(run_id="other"), EventFilters(camera_id="c1"), EventFilters(zone_id="z1")):
        with pytest.raises(ValueError):
            access.validate_filters(filters)
    with pytest.raises(ValidationError):
        access.store_id = "other"
    with pytest.raises(ValidationError):
        scope(allowed_zone_ids=())
    with pytest.raises(ValidationError):
        TrustedAccessScope(actor_id="", store_id="store-1", role="admin")


def test_five_request_shapes_and_required_zone():
    requests = [FootfallRequest(window=WINDOW), ZoneDwellRequest(window=WINDOW, filters={"zone_id": "z3"}),
                InteractionsRequest(window=WINDOW), UnattendedRequest(window=WINDOW, min_seconds=60),
                CoverageRequest(window=WINDOW, shift="morning")]
    for request in requests:
        assert type(request).model_validate_json(request.model_dump_json()) == request
    with pytest.raises(ValidationError):
        ZoneDwellRequest(window=WINDOW, filters={})
    with pytest.raises(ValidationError):
        UnattendedRequest(window=WINDOW, min_seconds=-1)


def evidence(**kwargs):
    return Evidence(source="footfall", ids=("synthetic:in:1",), query="get_footfall", matched_count=1, **kwargs)


@pytest.mark.parametrize("kwargs", [dict(value=None), dict(value=0), dict(value=-1), dict(value=0.5, evidence=(evidence(),)),
                                     dict(value=float('nan')), dict(value=True), dict(value="1")])
def test_invalid_count_metrics(kwargs):
    with pytest.raises(ValidationError):
        CountMetric(**kwargs)


def test_missing_vs_observed_zero_and_evidence_sampling():
    zero = CountMetric(value=0, evidence=(Evidence(source="pipeline_health", ids=("synthetic:healthy:1",),
                                               query="get_footfall", matched_count=1),))
    missing = CountMetric(value=None, unavailable_reason="Initial occupancy unknown")
    assert zero.value == 0 and missing.value is None
    sample = Evidence(source="footfall", ids=("e1",), query="get_footfall", matched_count=300, truncated=True)
    assert sample.truncated
    for kwargs in ({"source": "users"}, {"query": "run_readonly_sql"}, {"matched_count": 0},
                   {"matched_count": 2}, {"ids": ("same", "same"), "matched_count": 2},
                   {"ids": tuple(str(i) for i in range(201)), "matched_count": 201}):
        base = dict(source="footfall", ids=("e1",), query="get_footfall", matched_count=1)
        with pytest.raises(ValidationError):
            Evidence(**(base | kwargs))
    with pytest.raises(ValidationError):
        SecondsMetric(value=1, unit="count", evidence=(evidence(),))


def test_synthetic_result_roundtrip_and_metric_provenance():
    result = FootfallResult(scope=scope(), window=WINDOW, status="partial", synthetic=True,
                            limitations=("Net per-track events; occupancy unavailable",),
                            buckets=({"window": WINDOW, "entries": CountMetric(value=1, evidence=(evidence(),)),
                                      "exits": CountMetric(value=None, unavailable_reason="No observation evidence")},),
                            occupancy=CountMetric(value=None, unavailable_reason="Initial occupancy unknown"))
    assert FootfallResult.model_validate_json(result.model_dump_json()) == result
    assert result.buckets[0].entries.evidence[0].ids == ("synthetic:in:1",)
    bad = result.model_dump(mode="json")
    bad["buckets"][0]["entries"]["evidence"][0]["query"] = "get_coverage"
    with pytest.raises(ValidationError):
        FootfallResult.model_validate(bad)
    bad = result.model_dump(mode="json")
    bad["status"] = "unavailable"
    with pytest.raises(ValidationError):
        FootfallResult.model_validate(bad)
    with pytest.raises(ValidationError):
        CoverageResult(scope=scope(), window=WINDOW, status="unavailable", synthetic=True)


@pytest.mark.parametrize("result_type,extras", [
    (ZoneDwellResult, {}), (CoverageResult, {}),
    (InteractionsResult, {key: {"value": None, "unavailable_reason": "No supported observations"} for key in
                          ("confirmed_count", "unverified_count", "mean_confirmed_duration", "mean_approach", "approach_sample_count")}),
    (UnattendedResult, {"episode_count": {"value": None, "unavailable_reason": "Not queried"}}),
])
def test_unavailable_result_shapes(result_type, extras):
    result = result_type(scope=scope(), window=WINDOW, synthetic=True, status=DataStatus.UNAVAILABLE,
                         limitations=("Phase 1 contracts only; reader not implemented",), **extras)
    assert result_type.model_validate_json(result.model_dump_json()) == result


def test_existing_fixture_and_test_only_second_store(tmp_path):
    path = tmp_path / "synthetic.sqlite3"
    with connect(path) as conn:
        original_counts = generate(conn)
        assert validate(conn) == []
        assert generate(conn) == original_counts
        original = dict(conn.execute("SELECT * FROM footfall LIMIT 1").fetchone())
        # Same run/camera/track/time in a second store, unique event ID. Production
        # generator and schema stay unchanged. This tests contract separation only.
        other = original | {"event_id": "synthetic:second-store", "store_id": "store-2"}
        columns = list(other)
        conn.execute(f"INSERT INTO footfall ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", tuple(other.values()))
        conn.commit()
        assert validate(conn) == []
    with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as conn:
        assert conn.execute("SELECT COUNT(*) FROM footfall WHERE store_id=?", ("store-1",)).fetchone()[0] == original_counts["footfall"]
        assert conn.execute("SELECT COUNT(*) FROM footfall WHERE store_id=?", ("store-2",)).fetchone()[0] == 1
    assert scope().store_id != TrustedAccessScope(actor_id="manager-2", store_id="store-2", role="manager").store_id
    assert RUN_ID.startswith("fixture-")


def test_public_models_publish_json_schemas():
    for model in (FootfallRequest, ZoneDwellRequest, InteractionsRequest, UnattendedRequest, CoverageRequest,
                  FootfallResult, ZoneDwellResult, InteractionsResult, UnattendedResult, CoverageResult):
        schema = json.loads(json.dumps(model.model_json_schema()))
        assert schema['additionalProperties'] is False


def test_shared_documentation_result_example_is_valid():
    path = Path(__file__).resolve().parents[2] / "docs/fyp2-plan/CONTRACTS.md"
    section = path.read_text(encoding="utf-8").split("## Agent read-tool contracts", 1)[1]
    examples = re.findall(r"```json\s*\n(.*?)\n```", section, re.S)
    assert examples, "Shared contract must include a consumable result example"
    for example in examples:
        result = FootfallResult.model_validate_json(example)
        assert result.synthetic and result.buckets[0].entries.value == 1
        assert result.occupancy.value is None


def test_five_published_callable_signatures_keep_scope_separate():
    from .tools import AnalyticsTools
    shapes = {
        "get_footfall": (FootfallRequest, FootfallResult),
        "get_zone_dwell": (ZoneDwellRequest, ZoneDwellResult),
        "get_interactions": (InteractionsRequest, InteractionsResult),
        "get_unattended": (UnattendedRequest, UnattendedResult),
        "get_coverage": (CoverageRequest, CoverageResult),
    }
    for name, (request, result) in shapes.items():
        signature = inspect.signature(getattr(AnalyticsTools, name))
        assert list(signature.parameters) == ["self", "scope", "request"]
        assert signature.parameters['scope'].kind == inspect.Parameter.KEYWORD_ONLY
        assert signature.parameters['scope'].annotation is TrustedAccessScope
        assert signature.parameters['request'].annotation is request
        assert signature.return_annotation is result
