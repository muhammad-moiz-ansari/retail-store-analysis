import test from "node:test";
import assert from "node:assert/strict";
import { createBackendProvider, loadBackendSelection } from "./backend";
import { fixtureRequest, createFixtureProvider } from "./fixture";
import { loadDashboard, parseSnapshot } from "./provider";
import { backendHeaders } from "../backend-identity";

test("backend provider uses only same-origin proxy with session credentials, exact request and cancellation", async () => {
  const signal = new AbortController().signal;
  let called = false;
  const provider = createBackendProvider(async (url, options) => {
    called = true;
    assert.equal(url, "/api/backend/analytics/dashboard");
    assert.equal(options?.method, "POST");
    assert.equal(options?.credentials, "same-origin");
    assert.equal(options?.cache, "no-store");
    assert.equal(options?.signal, signal);
    assert.deepEqual(JSON.parse(String(options?.body)), fixtureRequest);
    assert.deepEqual(options?.headers, { "Content-Type": "application/json" });
    return Response.json({ received: true });
  });
  assert.deepEqual(await provider.load(fixtureRequest, signal), { received: true });
  assert.equal(called, true);
});

test("authorization, network and malformed response failures never substitute fixtures", async () => {
  for (const fetcher of [
    async () => new Response("private detail", { status: 403 }),
    async () => new Response("unconfigured", { status: 503 }),
    async () => { throw new Error("private detail"); },
    async () => Response.json({ invalid: true }),
  ]) {
    const result = await loadDashboard(createBackendProvider(fetcher), fixtureRequest);
    assert.equal(result.status, "unavailable");
    assert.equal(result.snapshot.provenance.mode, "backend");
    assert.ok(Object.values(result.snapshot.metrics).every(metric => metric.value === null));
    assert.doesNotMatch(JSON.stringify(result), /private detail/);
  }
});

test("backend context provides validated server selection without client authority fields", async () => {
  const request = await loadBackendSelection(undefined, async (url, options) => {
    assert.equal(url, "/api/backend/analytics/dashboard/context");
    assert.equal(options?.credentials, "same-origin");
    assert.equal(options?.cache, "no-store");
    return Response.json({ request: fixtureRequest, synthetic: true });
  });
  assert.deepEqual(request, fixtureRequest);
  await assert.rejects(loadBackendSelection(undefined, async () => Response.json({ request: {} })));
  await assert.rejects(loadBackendSelection(undefined, async () => new Response("no", { status: 403 })));
});

test("health-backed observed zero from real tools is accepted without inventing missing values", async () => {
  const raw = await createFixtureProvider("empty").load(fixtureRequest);
  const snapshot = parseSnapshot(raw, fixtureRequest, "fixture");
  snapshot.provenance.mode = "backend";
  snapshot.metrics.entries.evidence = [{ query: "get_footfall", source: "pipeline_health", ids: ["h1"], matchedCount: 1, truncated: false }];
  assert.equal(parseSnapshot(snapshot, fixtureRequest, "backend").metrics.entries.value, 0);
});

test("proxy strips injected identity even when the signed session has no user ID", () => {
  const incoming = new Headers({ "x-retailpulse-user-id": "victim", "x-retailpulse-role": "Manager",
    "x-retailpulse-internal-secret": "attacker", authorization: "Bearer private", cookie: "session=private", "content-type": "application/json" });
  const headers = backendHeaders(incoming, { role: "Employee", email: "employee@test.invalid" }, "test-secret");
  assert.equal(headers.get("x-retailpulse-user-id"), null);
  assert.equal(headers.get("x-retailpulse-role"), "Employee");
  assert.equal(headers.get("x-retailpulse-internal-secret"), "test-secret");
  assert.equal(headers.get("authorization"), null);
  assert.equal(headers.get("cookie"), null);
  assert.equal(headers.get("content-type"), "application/json");
  assert.equal(backendHeaders(incoming, { role: "Manager", email: "manager@test.invalid", userId: "actual-user" }, "test-secret").get("x-retailpulse-user-id"), "actual-user");
});
