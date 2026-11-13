"use client";

import React, { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { RetroButton } from "../ui/RetroButton";
import { ManagerCard, ManagerPanel } from "../ui/ManagerLayout";
import { FootfallChart } from "./FootfallChart";
import { type AnalyticsProvider, type AnalyticsRequest, type AnalyticsSnapshot, type DashboardMetric, type DashboardState, type MetricKey, metricKeys } from "../../lib/analytics-provider/contracts";
import { DashboardController } from "../../lib/analytics-provider/controller";
import { createFixtureProvider, fixtureRequest, type FixtureScenario } from "../../lib/analytics-provider/fixture";
import { createBackendProvider, loadBackendSelection } from "../../lib/analytics-provider/backend";

const labels: Record<MetricKey, string> = {
  entries: "Recorded entries", exits: "Recorded exits", confirmedInteractions: "Confirmed interactions",
  unverifiedInteractions: "Unverified interactions", meanConfirmedDuration: "Mean confirmed interaction duration",
  customerDwellP50: "Customer median dwell", unattendedEpisodes: "Derived unattended episodes",
  staffedOpenRatio: "Staffed / open time",
};
const stateLabels = { ready: "Ready", partial: "Partial data", stale: "Stale data", unavailable: "Analytics unavailable" };
const headlineMetrics: MetricKey[] = ["entries", "exits", "confirmedInteractions", "staffedOpenRatio"];
const detailMetrics = metricKeys.filter(key => !headlineMetrics.includes(key));
const selectClass = "min-h-11 w-full rounded-lg border border-border-soft bg-surface px-3 py-2 text-sm text-text sm:w-auto";
const scenarios: { value: FixtureScenario; label: string }[] = [
  { value: "ready", label: "Ready" }, { value: "empty", label: "Observed empty" },
  { value: "partial", label: "Partial data" }, { value: "unavailable", label: "Unavailable" },
  { value: "stale", label: "Stale data" },
];

function metricValue(metric: DashboardMetric): string {
  if (metric.value === null) return "Unavailable";
  if (metric.unit === "ratio") return `${(metric.value * 100).toFixed(1)}%`;
  return `${metric.value.toLocaleString("en-US", { maximumFractionDigits: 2 })}${metric.unit === "seconds" ? " s" : ""}`;
}

/** Pure view also used by offline rendering checks. No fabricated fallbacks. */
export function AnalyticsView({ state }: { state: DashboardState }) {
  if (state.status === "loading") return <p role="status" className="font-mono text-sm text-text-muted py-6">Loading analytics…</p>;
  const { snapshot } = state;
  return (
    <div className="space-y-5">
      <div role="status" aria-live="polite" className="space-y-2 rounded-xl bg-surface-alt p-4">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <p className="font-heading font-semibold text-text">{snapshot.provenance.label}</p>
          <p className="rounded-full bg-surface px-2.5 py-1 text-xs font-semibold text-accent">{stateLabels[state.status]}</p>
        </div>
        {snapshot.provenance.synthetic && <p className="text-sm text-text-muted">Synthetic preview. These values are illustrative and are not live store measurements.</p>}
        {state.status === "stale" && <p className="text-sm text-danger">Cached values have expired. Refresh before using them; individual data limitations still apply.</p>}
        {state.status === "partial" && <p className="text-sm text-text-muted">Some metrics lack sufficient data. Supported values remain visible.</p>}
        {state.status === "unavailable" && <p className="text-sm text-text-muted">No supported analytics are available for this selection. Missing values are not zero.</p>}
      </div>
      <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm text-text-muted [overflow-wrap:anywhere] sm:grid-cols-2 xl:grid-cols-3">
        <div>
          <dt className="font-semibold">Observation window (UTC, end excluded)</dt>
          <dd className="flex flex-wrap gap-x-1">
            <time dateTime={snapshot.request.window.start}>{snapshot.request.window.start}</time>
            <span>→</span>
            <time dateTime={snapshot.request.window.end}>{snapshot.request.window.end}</time>
          </dd>
        </div>
        <div><dt className="font-semibold">Store / region</dt><dd>{snapshot.request.storeId} / {snapshot.request.filters.zoneId ?? "All permitted regions"}</dd></div>
        <div><dt className="font-semibold">Run / camera selection</dt><dd>{snapshot.request.filters.runId ?? "All permitted runs"} / {snapshot.request.filters.cameraId ?? "All permitted cameras"}</dd></div>
      </dl>
      <MetricGrid keys={headlineMetrics} metrics={snapshot.metrics} headline />
      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <FootfallChart metrics={snapshot.metrics} />
        <section aria-labelledby="activity-metrics-title">
          <h3 id="activity-metrics-title" className="mb-3 text-lg font-bold">Interaction and dwell details</h3>
          <MetricGrid keys={detailMetrics} metrics={snapshot.metrics} />
        </section>
      </div>
      <details className="rounded-lg bg-bg p-4 text-sm text-text-muted">
        <summary className="w-fit cursor-pointer font-semibold text-accent">Data freshness and coverage notes</summary>
        <dl className="mt-3 grid gap-3 [overflow-wrap:anywhere] sm:grid-cols-2">
          <div><dt className="font-semibold">Retrieved at (UTC)</dt><dd>{snapshot.generatedAt}</dd></div>
          <div><dt className="font-semibold">Cache valid until (UTC)</dt><dd>{snapshot.validUntil}</dd></div>
        </dl>
        <ul className="mt-3 list-disc space-y-1 pl-5">
          {snapshot.limitations.map((text, index) => <li key={index}>{text}</li>)}
        </ul>
      </details>
    </div>
  );
}

function MetricGrid({ keys, metrics, headline = false }: {
  keys: MetricKey[];
  metrics: AnalyticsSnapshot["metrics"];
  headline?: boolean;
}) {
  return (
      <div className={`grid gap-3 min-[540px]:grid-cols-2 ${headline ? "xl:grid-cols-4" : ""}`}>
        {keys.map(key => {
          const metric = metrics[key];
          return (
            <article key={key} aria-label={labels[key]}>
              <ManagerCard className={`h-full ${headline && key === "entries" ? "border-accent-soft bg-surface-alt" : ""}`}>
                <p className="font-heading text-sm font-semibold text-text">{labels[key]}</p>
                <p className={`mt-2 font-heading font-bold tabular-nums tracking-tight text-text ${headline && metric.value !== null ? "text-4xl" : "text-2xl"}`}>{metricValue(metric)}</p>
                <p className="mt-1 text-xs text-text-muted">
                  {metric.unit} · {metric.status === "empty" ? "Observed empty" : metric.status}
                  {metric.estimated ? " · Estimated" : ""}
                </p>
                {metric.reason && <p className="text-sm text-text-muted mt-2">{metric.reason}</p>}
                <details className="mt-3 text-xs text-text-muted break-words">
                  <summary className="w-fit cursor-pointer font-semibold text-accent">Evidence and limitations</summary>
                  <ul className="mt-2 space-y-2 list-disc pl-4">
                    {metric.limitations.map((text, index) => <li key={`limitation-${index}`}>{text}</li>)}
                    {metric.evidence.map((item, index) => <li key={`evidence-${index}`}>
                      {item.query} / {item.source}: {item.ids.join(", ")}. {item.ids.length} cited / {item.matchedCount} matched
                      {item.truncated ? " (sample truncated)" : ""}.
                    </li>)}
                    {!metric.evidence.length && <li>No source row IDs supplied; zero values require sufficient observation.</li>}
                  </ul>
                </details>
              </ManagerCard>
            </article>
          );
        })}
      </div>
  );
}

/** The same view supports authorized backend results and explicit fixtures. */
export function DashboardAnalytics({ provider, request }: { provider: AnalyticsProvider; request: AnalyticsRequest }) {
  const controller = useMemo(() => new DashboardController(provider, request), [provider, request]);
  const state = useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getServerSnapshot);
  useEffect(() => {
    void controller.refresh();
    return controller.stop;
  }, [controller]);
  return (
    <section aria-label="Dashboard analytics" aria-busy={state.status === "loading"}>
      <ManagerCard>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
          <h2 className="text-xl font-bold tracking-tight">Selected-window analytics</h2>
          <RetroButton variant="secondary" onClick={() => void controller.refresh()} disabled={state.status === "loading"}>
            Refresh analytics
          </RetroButton>
        </div>
        <AnalyticsView state={state} />
      </ManagerCard>
    </section>
  );
}

export function DashboardPreview() {
  const [scenario, setScenario] = useState<FixtureScenario>("ready");
  const provider = useMemo(() => createFixtureProvider(scenario), [scenario]);
  return (
    <div className="space-y-5">
      <ManagerCard>
        <p className="font-heading font-semibold text-text">Dashboard fixture preview</p>
        <p className="text-sm text-text-muted mt-1">Analytics are in synthetic preview mode. Backend system status and the recorded clip below are separate sources.</p>
        <label htmlFor="dashboard-scenario" className="block font-mono text-xs text-text-muted mt-4 mb-2">Preview scenario</label>
        <select id="dashboard-scenario" value={scenario} onChange={event => setScenario(event.target.value as FixtureScenario)}
          className={selectClass}>
          {scenarios.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
        </select>
      </ManagerCard>
      <DashboardAnalytics provider={provider} request={fixtureRequest} />
    </div>
  );
}

function BackendDashboard() {
  const [selection, setSelection] = useState<AnalyticsRequest | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const provider = useMemo(() => createBackendProvider(), []);
  useEffect(() => {
    const controller = new AbortController();
    loadBackendSelection(controller.signal).then(request => {
      if (!controller.signal.aborted) setSelection(request);
    }).catch(() => {
      if (!controller.signal.aborted) setFailed(true);
    });
    return () => controller.abort();
  }, [attempt]);
  if (!selection) return <ManagerPanel title="Backend analytics">
    <p role="status" className="text-sm text-text-muted">{failed
      ? "Backend analytics unavailable. Check your manager membership, server source configuration and backend connection. No preview data has been substituted."
      : "Loading authorized backend selection…"}</p>
    {failed && <RetroButton variant="secondary" className="mt-4" onClick={() => { setFailed(false); setAttempt(value => value + 1); }}>Retry backend connection</RetroButton>}
  </ManagerPanel>;
  return <DashboardAnalytics provider={provider} request={selection} />;
}

export function DashboardDataSource() {
  const [mode, setMode] = useState<"backend" | "fixture">("backend");
  return <div className="space-y-5">
    <ManagerCard>
      <label htmlFor="dashboard-source" className="font-heading font-semibold text-text block mb-2">Analytics data source</label>
      <select id="dashboard-source" value={mode} onChange={event => setMode(event.target.value as "backend" | "fixture")}
        className={selectClass}>
        <option value="backend">Configured backend</option>
        <option value="fixture">Synthetic fixture preview</option>
      </select>
      <p className="text-sm text-text-muted mt-2">Backend mode uses your server-authorized selection. Preview mode is an explicit synthetic demonstration.</p>
    </ManagerCard>
    {mode === "backend" ? <BackendDashboard /> : <DashboardPreview />}
  </div>;
}
