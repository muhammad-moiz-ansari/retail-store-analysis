import { type AnalyticsProvider, type AnalyticsRequest, type AnalyticsSnapshot, type DashboardMetric, metricDefinitions, metricKeys } from "./contracts";
import { unavailableSnapshot, validateRequest } from "./provider";

/** Hand-authored presentation scenarios, not generated CV results or Saqib's event fixture. */
export const fixtureRequest: AnalyticsRequest = {
  storeId: "demo-store", window: { start: "2026-11-03T09:00:00Z", end: "2026-11-03T10:00:00Z" },
  filters: { zoneId: "demo-region" },
};
export type FixtureScenario = "ready" | "empty" | "partial" | "unavailable" | "stale";

export function createFixtureProvider(scenario: FixtureScenario = "ready", now: () => number = Date.now): AnalyticsProvider {
  return {
    mode: "fixture",
    async load(request, signal) {
      signal?.throwIfAborted();
      validateRequest(request);
      const current = now();
      const unsupported = request.storeId !== fixtureRequest.storeId
        || Date.parse(request.window.start) !== Date.parse(fixtureRequest.window.start)
        || Date.parse(request.window.end) !== Date.parse(fixtureRequest.window.end)
        || request.filters.zoneId !== fixtureRequest.filters.zoneId || request.filters.cameraId !== undefined
        || request.filters.runId !== undefined;
      if (unsupported || scenario === "unavailable") return unavailableSnapshot(request, "fixture", current);
      const values = { entries: 12, exits: 7, confirmedInteractions: 3, unverifiedInteractions: 1,
        meanConfirmedDuration: 24, customerDwellP50: 90, unattendedEpisodes: 2, staffedOpenRatio: 0.75 };
      const metrics = Object.fromEntries(metricKeys.map(key => {
        const definition = metricDefinitions[key];
        const emptyUndefined = scenario === "empty" && definition.unit !== "count";
        const missing = scenario === "partial" && key === "staffedOpenRatio";
        const value = missing || emptyUndefined ? null : scenario === "empty" ? 0 : values[key];
        const reason = missing ? "Operating-window configuration is missing."
          : emptyUndefined ? "No samples or denominator in this scenario." : null;
        const source = definition.tool === "get_footfall" ? "footfall"
          : definition.tool === "get_zone_dwell" || definition.tool === "get_coverage" ? "zone_dwell"
          : definition.tool === "get_unattended" ? "unattended_episodes" : "interactions";
        const metric: DashboardMetric = {
          value, unit: definition.unit, status: missing ? "unavailable" : scenario === "empty" ? "empty" : "ok",
          reason, estimated: false,
          evidence: value !== null && value > 0 ? [{ query: definition.tool, source,
            ids: [`fixture-${key}`], matchedCount: 1, truncated: false }] : [],
          limitations: ["Hand-authored synthetic display scenario; not measured analytics."],
        };
        if (key === "unattendedEpisodes") metric.limitations.push("Stored derivation does not filter interaction verdicts; not confirmed unattended assistance.");
        if (definition.tool === "get_footfall") metric.limitations.push("Existing source writer records net crossings per track, not complete entrance counts.");
        if (reason) metric.limitations.push(reason);
        return [key, metric];
      })) as AnalyticsSnapshot["metrics"];
      return {
        version: 1, request: structuredClone(request),
        provenance: { mode: "fixture", synthetic: true, label: "Synthetic dashboard preview — not live data" },
        generatedAt: new Date(current - (scenario === "stale" ? 120000 : 0)).toISOString(),
        validUntil: new Date(current + (scenario === "stale" ? -60000 : 60000)).toISOString(),
        metrics, limitations: ["No camera, database, business agent, registered map or employee-account linkage is used."],
      } satisfies AnalyticsSnapshot;
    },
  };
}
