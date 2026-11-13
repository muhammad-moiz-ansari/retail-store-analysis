import {
  type AnalyticsProvider, type AnalyticsRequest, type AnalyticsSnapshot,
  type DashboardMetric, type DashboardState, metricDefinitions, metricKeys,
} from "./contracts";

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Expected object");
  return value as Record<string, unknown>;
}

function text(value: unknown): asserts value is string {
  if (typeof value !== "string" || !value.trim() || value.length > 2000) throw new Error("Invalid text");
}

function texts(value: unknown): asserts value is string[] {
  if (!Array.isArray(value) || value.length > 200) throw new Error("Invalid list");
  value.forEach(text);
}

function timestamp(value: unknown): number {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(value)) {
    throw new Error("UTC timestamps required");
  }
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed) || new Date(parsed).toISOString().slice(0, 19) !== value.slice(0, 19)) {
    throw new Error("Invalid timestamp");
  }
  return parsed;
}

export function validateRequest(value: unknown): asserts value is AnalyticsRequest {
  const request = record(value);
  text(request.storeId);
  const window = record(request.window);
  const duration = timestamp(window.end) - timestamp(window.start);
  if (duration <= 0 || duration > 31 * 86400000) throw new Error("Invalid observation window");
  const filters = record(request.filters);
  for (const key of Object.keys(filters)) {
    if (!["runId", "cameraId", "zoneId"].includes(key)) throw new Error("Unsupported filter");
    text(filters[key]);
  }
}

function sameRequest(a: AnalyticsRequest, b: AnalyticsRequest): boolean {
  return a.storeId === b.storeId && timestamp(a.window.start) === timestamp(b.window.start)
    && timestamp(a.window.end) === timestamp(b.window.end)
    && (["runId", "cameraId", "zoneId"] as const).every(key => a.filters[key] === b.filters[key]);
}

const sources: Record<string, string[]> = {
  get_footfall: ["footfall", "pipeline_health"], get_interactions: ["interactions", "tracks", "pipeline_health"],
  get_zone_dwell: ["zone_dwell", "pipeline_health"], get_unattended: ["unattended_episodes", "pipeline_health"],
  get_coverage: ["zone_dwell", "pipeline_health"],
};

/** Validate untrusted provider payloads before rendering; never repairs missing values into zero. */
export function parseSnapshot(value: unknown, request: AnalyticsRequest, mode: AnalyticsProvider["mode"]): AnalyticsSnapshot {
  validateRequest(request);
  const data = record(value);
  validateRequest(data.request);
  if (data.version !== 1 || !sameRequest(data.request, request)) throw new Error("Response scope mismatch");
  const provenance = record(data.provenance);
  text(provenance.label);
  if (provenance.mode !== mode || typeof provenance.synthetic !== "boolean"
    || (mode === "fixture" && provenance.synthetic !== true)) throw new Error("Invalid provenance");
  if (timestamp(data.validUntil) < timestamp(data.generatedAt)) throw new Error("Invalid cache window");
  texts(data.limitations);
  const metrics = record(data.metrics);
  if (Object.keys(metrics).length !== metricKeys.length) throw new Error("Unexpected metric set");
  for (const key of metricKeys) {
    const metric = record(metrics[key]);
    const definition = metricDefinitions[key];
    if (metric.unit !== definition.unit || !["ok", "empty", "partial", "unavailable"].includes(String(metric.status))) {
      throw new Error("Invalid metric metadata");
    }
    texts(metric.limitations);
    if (typeof metric.estimated !== "boolean" || !Array.isArray(metric.evidence) || metric.evidence.length > 20) {
      throw new Error("Invalid metric provenance");
    }
    if (metric.reason !== null) text(metric.reason);
    if (metric.value === null) {
      text(metric.reason);
      if (metric.status === "ok") throw new Error("Missing metric cannot be ok");
    } else {
      if (typeof metric.value !== "number" || !Number.isFinite(metric.value) || metric.value < 0
        || (metric.unit === "count" && !Number.isInteger(metric.value))
        || (metric.unit === "ratio" && metric.value > 1) || metric.status === "unavailable") {
        throw new Error("Invalid metric value");
      }
      if (metric.status === "empty" && metric.value !== 0) throw new Error("Empty counts must be zero");
      if (metric.value > 0 && metric.evidence.length === 0) throw new Error("Positive values require evidence");
    }
    if (["partial", "unavailable"].includes(String(metric.status)) && metric.limitations.length === 0) {
      throw new Error("Limitations required");
    }
    for (const item of metric.evidence) {
      const evidence = record(item);
      texts(evidence.ids);
      if (evidence.query !== definition.tool || !sources[definition.tool].includes(String(evidence.source))
        || evidence.ids.length === 0 || new Set(evidence.ids).size !== evidence.ids.length
        || !Number.isSafeInteger(evidence.matchedCount) || Number(evidence.matchedCount) < evidence.ids.length
        || evidence.truncated !== (Number(evidence.matchedCount) > evidence.ids.length)) {
        throw new Error("Invalid evidence");
      }
    }
  }
  // Isolate consumers from a provider mutating a shared object after validation.
  return structuredClone(data) as AnalyticsSnapshot;
}

export function unavailableSnapshot(request: AnalyticsRequest, mode: AnalyticsProvider["mode"], now: number): AnalyticsSnapshot {
  const reason = "Analytics could not be loaded for the requested scope.";
  const metrics = Object.fromEntries(metricKeys.map((key): [string, DashboardMetric] => [key, {
    value: null, unit: metricDefinitions[key].unit, status: "unavailable", reason,
    estimated: false, evidence: [], limitations: [reason],
  }])) as Record<(typeof metricKeys)[number], DashboardMetric>;
  return {
    version: 1, request: structuredClone(request),
    provenance: { mode, synthetic: mode === "fixture", label: mode === "fixture" ? "Synthetic fixture unavailable" : "Backend unavailable" },
    generatedAt: new Date(now).toISOString(), validUntil: new Date(now).toISOString(), metrics, limitations: [reason],
  };
}

export function snapshotState(snapshot: AnalyticsSnapshot, now = Date.now()): Exclude<DashboardState, { status: "loading" }> {
  const values = Object.values(snapshot.metrics);
  const status = values.every(metric => metric.status === "unavailable") ? "unavailable"
    : now > timestamp(snapshot.validUntil) ? "stale"
    : values.some(metric => metric.status === "partial" || metric.status === "unavailable") ? "partial" : "ready";
  return { status, snapshot };
}

/** No automatic fallback from failed backend data to fixtures. Invalid requests reject before I/O. */
export async function loadDashboard(provider: AnalyticsProvider, request: AnalyticsRequest, options: {
  signal?: AbortSignal; now?: () => number;
} = {}): Promise<Exclude<DashboardState, { status: "loading" }>> {
  validateRequest(request);
  const requested = structuredClone(request);
  const now = options.now ?? Date.now;
  options.signal?.throwIfAborted();
  try {
    const raw = await provider.load(structuredClone(requested), options.signal);
    options.signal?.throwIfAborted();
    return snapshotState(parseSnapshot(raw, requested, provider.mode), now());
  } catch {
    options.signal?.throwIfAborted();
    return snapshotState(unavailableSnapshot(requested, provider.mode, now()), now());
  }
}
