"use client";

import React, { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { RetroWindow } from "../ui/RetroWindow";
import { RetroButton } from "../ui/RetroButton";
import { RetroCard } from "../ui/RetroCard";
import { type AnalyticsProvider, type AnalyticsRequest, type DashboardMetric, type DashboardState, type MetricKey, metricKeys } from "../../lib/analytics-provider/contracts";
import { DashboardController } from "../../lib/analytics-provider/controller";
import { createFixtureProvider, fixtureRequest, type FixtureScenario } from "../../lib/analytics-provider/fixture";

const labels: Record<MetricKey, string> = {
  entries: "Recorded entries", exits: "Recorded exits", confirmedInteractions: "Confirmed interactions",
  unverifiedInteractions: "Unverified interactions", meanConfirmedDuration: "Mean confirmed interaction duration",
  customerDwellP50: "Customer median dwell", unattendedEpisodes: "Derived unattended episodes",
  staffedOpenRatio: "Staffed / open time",
};
const stateLabels = { ready: "Ready", partial: "Partial data", stale: "Stale data", unavailable: "Analytics unavailable" };
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
      <div role="status" aria-live="polite" className="rounded-md border border-border-soft bg-surface-alt p-4 space-y-2">
        <p className="font-heading font-semibold text-text">{snapshot.provenance.label}</p>
        <p className="font-mono text-sm text-accent">{stateLabels[state.status]}</p>
        {snapshot.provenance.synthetic && <p className="text-sm text-text-muted">Synthetic preview. These values are illustrative and are not live store measurements.</p>}
        {state.status === "stale" && <p className="text-sm text-danger">Cached values have expired. Refresh before using them; individual data limitations still apply.</p>}
        {state.status === "partial" && <p className="text-sm text-text-muted">Some metrics lack sufficient data. Supported values remain visible.</p>}
        {state.status === "unavailable" && <p className="text-sm text-text-muted">No supported analytics are available for this selection. Missing values are not zero.</p>}
      </div>
      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-xs font-mono text-text-muted break-words">
        <div><dt className="font-semibold">Store / region</dt><dd>{snapshot.request.storeId} / {snapshot.request.filters.zoneId ?? "All permitted regions"}</dd></div>
        <div><dt className="font-semibold">Observation window (UTC, end excluded)</dt><dd>{snapshot.request.window.start} → {snapshot.request.window.end}</dd></div>
        <div><dt className="font-semibold">Retrieved at (UTC)</dt><dd>{snapshot.generatedAt}</dd></div>
        <div><dt className="font-semibold">Cache valid until (UTC)</dt><dd>{snapshot.validUntil}</dd></div>
      </dl>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        {metricKeys.map(key => {
          const metric = snapshot.metrics[key];
          return (
            <article key={key} aria-label={labels[key]}>
              <RetroCard className="h-full">
                <h3 className="font-heading text-sm font-semibold text-text">{labels[key]}</h3>
                <p className="font-mono text-2xl font-bold text-text mt-3">{metricValue(metric)}</p>
                <p className="font-mono text-xs text-text-muted mt-1">
                  {metric.unit} · {metric.status === "empty" ? "Observed empty" : metric.status}
                  {metric.estimated ? " · Estimated" : ""}
                </p>
                {metric.reason && <p className="text-sm text-text-muted mt-2">{metric.reason}</p>}
                <details className="mt-3 text-xs text-text-muted break-words">
                  <summary className="cursor-pointer font-semibold">Evidence and limitations</summary>
                  <ul className="mt-2 space-y-2 list-disc pl-4">
                    {metric.limitations.map((text, index) => <li key={`limitation-${index}`}>{text}</li>)}
                    {metric.evidence.map((item, index) => <li key={`evidence-${index}`}>
                      {item.query} / {item.source}: {item.ids.join(", ")}. {item.ids.length} cited / {item.matchedCount} matched
                      {item.truncated ? " (sample truncated)" : ""}.
                    </li>)}
                    {!metric.evidence.length && <li>No source row IDs supplied; zero values require sufficient observation.</li>}
                  </ul>
                </details>
              </RetroCard>
            </article>
          );
        })}
      </div>
      <ul className="list-disc pl-5 text-sm text-text-muted space-y-1">
        {snapshot.limitations.map((text, index) => <li key={index}>{text}</li>)}
      </ul>
    </div>
  );
}

/** Phase 3 can supply a real provider/request here without replacing the view. */
export function DashboardAnalytics({ provider, request }: { provider: AnalyticsProvider; request: AnalyticsRequest }) {
  const controller = useMemo(() => new DashboardController(provider, request), [provider, request]);
  const state = useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getServerSnapshot);
  useEffect(() => {
    void controller.refresh();
    return controller.stop;
  }, [controller]);
  return (
    <section aria-label="Dashboard analytics" aria-busy={state.status === "loading"}>
      <RetroWindow title="Analytics">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
          <h2 className="font-heading font-bold text-text">Selected-window analytics</h2>
          <RetroButton variant="secondary" onClick={() => void controller.refresh()} disabled={state.status === "loading"}>
            Refresh analytics
          </RetroButton>
        </div>
        <AnalyticsView state={state} />
      </RetroWindow>
    </section>
  );
}

export function DashboardPreview() {
  const [scenario, setScenario] = useState<FixtureScenario>("ready");
  const provider = useMemo(() => createFixtureProvider(scenario), [scenario]);
  return (
    <div className="space-y-5">
      <RetroCard>
        <p className="font-heading font-semibold text-text">Dashboard fixture preview</p>
        <p className="text-sm text-text-muted mt-1">Analytics are in synthetic preview mode. Backend system status and the recorded clip below are separate sources.</p>
        <label htmlFor="dashboard-scenario" className="block font-mono text-xs text-text-muted mt-4 mb-2">Preview scenario</label>
        <select id="dashboard-scenario" value={scenario} onChange={event => setScenario(event.target.value as FixtureScenario)}
          className="w-full sm:w-auto rounded border border-border bg-surface px-3 py-2 text-text">
          {scenarios.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
        </select>
      </RetroCard>
      <DashboardAnalytics provider={provider} request={fixtureRequest} />
    </div>
  );
}
