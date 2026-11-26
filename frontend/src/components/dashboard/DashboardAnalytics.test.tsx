import React from "react";
import test from "node:test";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import { AnalyticsView, DashboardAnalytics, DashboardPreview, DashboardDataSource, durationText, utcText } from "./DashboardAnalytics";
import { createFixtureProvider, fixtureRequest } from "../../lib/analytics-provider/fixture";
import { loadDashboard } from "../../lib/analytics-provider/provider";

const now = () => Date.parse("2026-11-11T12:00:00Z");

test("dashboard starts in configured backend mode and offers fixtures only as an explicit choice", () => {
  const html = renderToStaticMarkup(<DashboardDataSource />);
  assert.match(html, /Loading authorized backend selection/);
  assert.match(html, /label for="dashboard-source"/);
  assert.match(html, /Configured backend/);
  assert.doesNotMatch(html, /fixture-entries|>12<|Preview scenario/);
});

test("initial server render shows loading and a labelled scenario selector, not invented numbers", () => {
  const html = renderToStaticMarkup(<DashboardPreview />);
  assert.match(html, /Dashboard fixture preview/);
  assert.match(html, /label for="dashboard-scenario"/);
  assert.match(html, /Loading analytics/);
  assert.match(html, /aria-busy="true"/);
  assert.match(html, /disabled=""[^>]*>Refresh analytics/);
  assert.doesNotMatch(html, /fixture-entries|>12<|Net inside|Analyzing store data/);
});

test("ready view renders supported metrics with units, provenance, window and evidence", async () => {
  const state = await loadDashboard(createFixtureProvider("ready", now), fixtureRequest, { now });
  const html = renderToStaticMarkup(<AnalyticsView state={state} />);
  assert.match(html, /Synthetic dashboard preview/);
  assert.match(html, /not live store measurements/);
  assert.match(html, /2026-11-03T09:00:00Z/);
  assert.match(html, /Recorded entries/);
  assert.match(html, /<caption[^>]*>Recorded crossing counts<\/caption>/);
  assert.match(html, /Entries<\/th><td[^>]*>12<\/td>/);
  assert.match(html, /Exits<\/th><td[^>]*>7<\/td>/);
  assert.match(html, /75\.0%/);
  assert.match(html, /24 s/);
  assert.match(html, /get_interactions \/ interactions/);
  assert.match(html, /not confirmed unattended assistance/);
  assert.match(html, /unvalidated until scored against a labelled clip/);
  assert.doesNotMatch(html, /Peak Hour|Density|Employee A|Net inside|avgResponse/);
});

test("empty view shows observed zero and explains undefined means and ratios", async () => {
  const state = await loadDashboard(createFixtureProvider("empty", now), fixtureRequest, { now });
  const html = renderToStaticMarkup(<AnalyticsView state={state} />);
  assert.match(html, /Observed empty/);
  assert.match(html, />0<\/p>/);
  assert.match(html, /Entries<\/th><td[^>]*>0<\/td>/);
  assert.match(html, />Unavailable<\/p>/);
  assert.match(html, /No samples or denominator/);
  assert.doesNotMatch(html, /0\.0%/);
});

test("partial, unavailable and stale views preserve explanations instead of filling zeros", async () => {
  for (const scenario of ["partial", "unavailable", "stale"] as const) {
    const state = await loadDashboard(createFixtureProvider(scenario, now), fixtureRequest, { now });
    const html = renderToStaticMarkup(<AnalyticsView state={state} />);
    assert.match(html, /Synthetic|synthetic/);
    if (scenario === "partial") {
      assert.match(html, /Partial data/);
      assert.match(html, /Operating-window configuration is missing/);
      assert.match(html, />12<\/p>/);
    } else if (scenario === "unavailable") {
      assert.match(html, /Missing values are not zero/);
      assert.match(html, /Entries<\/th><td[^>]*>Unavailable<\/td>/);
      assert.equal((html.match(/>Unavailable<\/p>/g) ?? []).length, 8);
      assert.doesNotMatch(html, />0<\/p>/);
    } else {
      assert.match(html, /Cached values have expired/);
      assert.match(html, />12<\/p>/);
    }
  }
});

test("estimated and partial evidence markers remain visible", async () => {
  const state = await loadDashboard(createFixtureProvider("ready", now), fixtureRequest, { now });
  state.snapshot.metrics.entries.estimated = true;
  state.snapshot.metrics.entries.evidence[0].matchedCount = 12;
  state.snapshot.metrics.entries.evidence[0].truncated = true;
  const html = renderToStaticMarkup(<AnalyticsView state={state} />);
  assert.match(html, /Estimated/);
  assert.match(html, /sample truncated/);
  assert.match(html, /1.*cited \/.*12.*matched/);
});

test("binding can accept an injected provider without invoking it during server rendering", () => {
  const html = renderToStaticMarkup(<DashboardAnalytics request={fixtureRequest} provider={{ mode: "backend", load() { assert.fail("no server-side provider invocation"); } }} />);
  assert.match(html, /Loading analytics/);
});

test("durations use s, min or h and windows read as UTC (QA Q2, Q3)", () => {
  assert.equal(durationText(24), "24 s");
  assert.equal(durationText(1834.5), "30.6 min");
  assert.equal(durationText(9000), "2.5 h");
  assert.equal(utcText("2026-11-03T09:00:00Z"), "2026-11-03 09:00 UTC");
  assert.equal(utcText("not a time"), "not a time");
});

test("evidence lists cap cited IDs and unverified interactions say they are not counted (QA Q1, Q4)", async () => {
  const state = await loadDashboard(createFixtureProvider("ready", now), fixtureRequest, { now });
  const metric = state.snapshot.metrics.entries;
  const ids = Array.from({ length: 12 }, (_, i) => `row-${i}`);
  const crowded = { ...state, snapshot: { ...state.snapshot, metrics: { ...state.snapshot.metrics,
    entries: { ...metric, evidence: [{ ...metric.evidence[0], ids, matchedCount: 12 }] } } } };
  const html = renderToStaticMarkup(<AnalyticsView state={crowded} />);
  assert.match(html, /row-4 and 7 more/);
  assert.doesNotMatch(html, /row-5/);
  assert.match(html, /Unverified interactions \(not counted\)/);
});
