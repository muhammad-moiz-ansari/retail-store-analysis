/** Presentation contract, not an authorization or event-ingestion API. */
export type AnalyticsRequest = {
  storeId: string;
  window: { start: string; end: string };
  filters: { runId?: string; cameraId?: string; zoneId?: string };
};

export const metricDefinitions = {
  entries: { unit: "count", tool: "get_footfall" },
  exits: { unit: "count", tool: "get_footfall" },
  confirmedInteractions: { unit: "count", tool: "get_interactions" },
  unverifiedInteractions: { unit: "count", tool: "get_interactions" },
  meanConfirmedDuration: { unit: "seconds", tool: "get_interactions" },
  customerDwellP50: { unit: "seconds", tool: "get_zone_dwell" },
  unattendedEpisodes: { unit: "count", tool: "get_unattended" },
  staffedOpenRatio: { unit: "ratio", tool: "get_coverage" },
} as const;

export type MetricKey = keyof typeof metricDefinitions;
export type ToolName = (typeof metricDefinitions)[MetricKey]["tool"];
export type DataStatus = "ok" | "empty" | "partial" | "unavailable";
export type DashboardMetric = {
  value: number | null;
  unit: "count" | "seconds" | "ratio";
  status: DataStatus;
  reason: string | null;
  estimated: boolean;
  evidence: { query: ToolName; source: string; ids: string[]; matchedCount: number; truncated: boolean }[];
  limitations: string[];
};

export type AnalyticsSnapshot = {
  version: 1;
  request: AnalyticsRequest;
  provenance: { mode: "fixture" | "backend"; synthetic: boolean; label: string };
  // Retrieval/cache timestamps; the observation period is request.window.
  generatedAt: string;
  validUntil: string;
  metrics: Record<MetricKey, DashboardMetric>;
  limitations: string[];
};

export interface AnalyticsProvider {
  readonly mode: "fixture" | "backend";
  load(request: AnalyticsRequest, signal?: AbortSignal): Promise<unknown>;
}

export type DashboardState =
  | { status: "loading" }
  | { status: "ready" | "partial" | "stale" | "unavailable"; snapshot: AnalyticsSnapshot };

export const metricKeys = Object.keys(metricDefinitions) as MetricKey[];
