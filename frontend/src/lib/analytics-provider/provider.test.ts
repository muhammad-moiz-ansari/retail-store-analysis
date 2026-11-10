import test from "node:test";
import assert from "node:assert/strict";
import { createFixtureProvider, fixtureRequest, type FixtureScenario } from "./fixture";
import { loadDashboard, parseSnapshot, snapshotState } from "./provider";
import { type AnalyticsProvider, type AnalyticsSnapshot, metricKeys } from "./contracts";

const time = Date.parse("2026-11-11T12:00:00Z");
const now = () => time;
async function snapshot(): Promise<AnalyticsSnapshot> {
  return parseSnapshot(await createFixtureProvider("ready", now).load(fixtureRequest), fixtureRequest, "fixture");
}

for (const scenario of ["ready", "empty", "partial", "unavailable", "stale"] as FixtureScenario[]) {
  test(`fixture ${scenario} preserves status and synthetic provenance`, async () => {
    const result = await loadDashboard(createFixtureProvider(scenario, now), fixtureRequest, { now });
    assert.equal(result.status, scenario === "empty" ? "ready" : scenario);
    assert.equal(result.snapshot.provenance.synthetic, true);
    assert.match(result.snapshot.provenance.label, /[Ss]ynthetic/);
    assert.deepEqual(Object.keys(result.snapshot.metrics), metricKeys);
  });
}

test("observed empty counts are zero while undefined averages and ratios remain null", async () => {
  const { snapshot } = await loadDashboard(createFixtureProvider("empty", now), fixtureRequest, { now });
  assert.equal(snapshot.metrics.confirmedInteractions.value, 0);
  assert.equal(snapshot.metrics.confirmedInteractions.status, "empty");
  assert.equal(snapshot.metrics.meanConfirmedDuration.value, null);
  assert.equal(snapshot.metrics.staffedOpenRatio.value, null);
  assert.ok(snapshot.metrics.meanConfirmedDuration.reason);
});

test("partial coverage leaves supported values intact and explains the missing denominator", async () => {
  const { snapshot } = await loadDashboard(createFixtureProvider("partial", now), fixtureRequest, { now });
  assert.equal(snapshot.metrics.entries.value, 12);
  assert.equal(snapshot.metrics.staffedOpenRatio.value, null);
  assert.match(snapshot.metrics.staffedOpenRatio.reason!, /Operating-window/);
});

test("staleness uses cache expiry, not the historical observation period", async () => {
  const value = await snapshot();
  assert.equal(snapshotState(value, time).status, "ready");
  assert.equal(snapshotState(value, time + 60001).status, "stale");
  assert.equal(value.metrics.confirmedInteractions.value, 3);
});

test("fixture cannot relabel fixed scenario data as another store, time, camera, run or zone", async () => {
  const requests = [
    { ...fixtureRequest, storeId: "another-store" },
    { ...fixtureRequest, window: { start: "2026-11-04T09:00:00Z", end: "2026-11-04T10:00:00Z" } },
    ...["runId", "cameraId", "zoneId"].map(key => ({ ...fixtureRequest, filters: { ...fixtureRequest.filters, [key]: "other" } })),
  ];
  for (const request of requests) {
    const result = await loadDashboard(createFixtureProvider("ready", now), request, { now });
    assert.equal(result.status, "unavailable");
    assert.ok(Object.values(result.snapshot.metrics).every(metric => metric.value === null));
  }
});

test("invalid request rejects before invoking any provider", async () => {
  let called = false;
  const provider: AnalyticsProvider = { mode: "backend", async load() { called = true; } };
  for (const request of [
    { ...fixtureRequest, window: { start: "2026-11-03T09:00:00", end: fixtureRequest.window.end } },
    { ...fixtureRequest, window: { start: "2026-02-30T09:00:00Z", end: "2026-03-03T09:00:00Z" } },
    { ...fixtureRequest, window: { start: fixtureRequest.window.end, end: fixtureRequest.window.start } },
    { ...fixtureRequest, filters: { ...fixtureRequest.filters, unexpected: "field" } },
  ]) await assert.rejects(loadDashboard(provider, request, { now }));
  assert.equal(called, false);
});

test("malformed or cross-scope backend payload fails closed with sanitized errors and no fixture fallback", async () => {
  const base = await snapshot();
  const payloads: unknown[] = [undefined, {}, { ...base, provenance: { ...base.provenance, mode: "backend" }, request: { ...fixtureRequest, storeId: "secret-store" } }];
  for (const payload of payloads) {
    const provider: AnalyticsProvider = { mode: "backend", async load() { return payload; } };
    const result = await loadDashboard(provider, fixtureRequest, { now });
    assert.equal(result.status, "unavailable");
    assert.equal(result.snapshot.provenance.mode, "backend");
    assert.ok(Object.values(result.snapshot.metrics).every(metric => metric.value === null));
    assert.doesNotMatch(JSON.stringify(result), /secret-store/);
  }
  const result = await loadDashboard({ mode: "backend", async load() { throw new Error("password=secret"); } }, fixtureRequest, { now });
  assert.doesNotMatch(JSON.stringify(result), /password/);
});

test("rejects invalid values, wrong units, missing explanations and forged evidence", async () => {
  const base = await snapshot();
  const mutations = [
    { value: NaN }, { value: Infinity }, { value: -1 }, { value: 1.5 },
    { value: null }, { unit: "seconds" }, { status: "empty" },
    { status: "unavailable" }, { status: "partial", limitations: [] },
    { evidence: [] }, { evidence: [{ ...base.metrics.entries.evidence[0], query: "get_interactions" }] },
    { evidence: [{ ...base.metrics.entries.evidence[0], source: "users" }] },
    { evidence: [{ ...base.metrics.entries.evidence[0], matchedCount: 2, truncated: false }] },
    { evidence: [{ ...base.metrics.entries.evidence[0], ids: ["id", "id"], matchedCount: 2 }] },
  ];
  for (const mutation of mutations) {
    const changed = structuredClone(base);
    Object.assign(changed.metrics.entries, mutation);
    assert.throws(() => parseSnapshot(changed, fixtureRequest, "fixture"));
  }
  base.metrics.staffedOpenRatio.value = 1.1;
  assert.throws(() => parseSnapshot(base, fixtureRequest, "fixture"));
});

test("truncated evidence is retained explicitly, never presented as a complete sample", async () => {
  const base = await snapshot();
  base.metrics.entries.evidence[0].matchedCount = 12;
  base.metrics.entries.evidence[0].truncated = true;
  const parsed = parseSnapshot(base, fixtureRequest, "fixture");
  assert.equal(parsed.metrics.entries.evidence[0].truncated, true);
  assert.equal(parsed.metrics.entries.evidence[0].matchedCount, 12);
});

test("provider cannot silently label fixtures as real backend observations", async () => {
  const base = await snapshot();
  base.provenance.synthetic = false;
  assert.throws(() => parseSnapshot(base, fixtureRequest, "fixture"));
  base.provenance.synthetic = true;
  assert.throws(() => parseSnapshot(base, fixtureRequest, "backend"));
});

test("validated snapshots are isolated from later provider mutation", async () => {
  const raw = await snapshot();
  const parsed = parseSnapshot(raw, fixtureRequest, "fixture");
  raw.metrics.entries.value = 999;
  assert.equal(parsed.metrics.entries.value, 12);
});

test("cancellation rejects instead of displaying a spurious unavailable state", async () => {
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(loadDashboard(createFixtureProvider(), fixtureRequest, { signal: controller.signal }), { name: "AbortError" });
  const during = new AbortController();
  await assert.rejects(loadDashboard({ mode: "backend", async load() { during.abort(); return {}; } }, fixtureRequest,
    { signal: during.signal }), { name: "AbortError" });
});
