import test from "node:test";
import assert from "node:assert/strict";
import { DashboardController } from "./controller";
import { createFixtureProvider, fixtureRequest } from "./fixture";
import { type AnalyticsProvider } from "./contracts";

const time = Date.parse("2026-11-11T12:00:00Z");

function deferred() {
  let resolve!: (data: unknown) => void;
  const promise = new Promise<unknown>(done => { resolve = done; });
  return { promise, resolve };
}

test("refresh publishes loading and discards an obsolete response even if provider ignores abort", async () => {
  const first = deferred();
  const second = deferred();
  const signals: AbortSignal[] = [];
  let calls = 0;
  const provider: AnalyticsProvider = { mode: "fixture", load(_request, signal) {
    signals.push(signal!);
    return calls++ === 0 ? first.promise : second.promise;
  } };
  const controller = new DashboardController(provider, fixtureRequest, { now: () => time });
  const states: string[] = [];
  controller.subscribe(() => states.push(controller.getSnapshot().status));
  const oldLoad = controller.refresh();
  const newLoad = controller.refresh();
  assert.equal(signals[0].aborted, true);
  assert.equal(controller.getSnapshot().status, "loading");
  second.resolve(await createFixtureProvider("partial", () => time).load(fixtureRequest));
  await newLoad;
  assert.equal(controller.getSnapshot().status, "partial");
  first.resolve(await createFixtureProvider("ready", () => time).load(fixtureRequest));
  await oldLoad;
  assert.equal(controller.getSnapshot().status, "partial");
  assert.deepEqual(states, ["loading", "loading", "partial"]);
  controller.stop();
});

test("stop aborts pending loads and prevents late publication after unmount", async () => {
  const pending = deferred();
  const controller = new DashboardController({ mode: "fixture", load: () => pending.promise }, fixtureRequest);
  let notifications = 0;
  const unsubscribe = controller.subscribe(() => notifications++);
  const load = controller.refresh();
  controller.stop();
  unsubscribe();
  pending.resolve(await createFixtureProvider().load(fixtureRequest));
  await load;
  assert.equal(notifications, 1);
  assert.equal(controller.getSnapshot().status, "loading");
});

test("cache expiry changes partial data to stale without a second provider call and cleans up timers", async () => {
  let clock = time;
  let expire!: () => void;
  let delay = 0;
  let cancellations = 0;
  let loads = 0;
  const fixture = createFixtureProvider("partial", () => clock);
  const controller = new DashboardController({ mode: "fixture", load(...args) { loads++; return fixture.load(...args); } }, fixtureRequest, {
    now: () => clock,
    schedule(callback, milliseconds) { expire = callback; delay = milliseconds; return () => { cancellations++; }; },
  });
  await controller.refresh();
  assert.equal(controller.getSnapshot().status, "partial");
  assert.equal(delay, 60001);
  clock += delay;
  expire();
  const state = controller.getSnapshot();
  assert.equal(state.status, "stale");
  assert.equal(state.snapshot.metrics.staffedOpenRatio.status, "unavailable");
  assert.equal(loads, 1);
  controller.stop();
  assert.equal(cancellations, 1);
});

test("refresh and development effect replay cancel the previous expiry and can restart safely", async () => {
  let cancelled = 0;
  const controller = new DashboardController(createFixtureProvider("ready", () => time), fixtureRequest, {
    now: () => time, schedule() { return () => { cancelled++; }; },
  });
  assert.equal(controller.getServerSnapshot().status, "loading");
  await controller.refresh();
  assert.equal(controller.getSnapshot().status, "ready");
  controller.stop();
  await controller.refresh();
  assert.equal(controller.getSnapshot().status, "ready");
  assert.equal(cancelled, 1);
  controller.stop();
  assert.equal(cancelled, 2);
});

test("provider failures become unavailable and never start an expiry timer", async () => {
  const controller = new DashboardController({ mode: "backend", async load() { throw new Error("private detail"); } }, fixtureRequest, {
    schedule() { assert.fail("unavailable data must not schedule expiry"); },
  });
  await controller.refresh();
  const state = controller.getSnapshot();
  assert.equal(state.status, "unavailable");
  assert.doesNotMatch(JSON.stringify(state), /private detail/);
  controller.stop();
});
