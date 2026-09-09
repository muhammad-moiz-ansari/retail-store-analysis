"use client";

import React, { FormEvent, useEffect, useMemo, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, RetroButton, RetroCard, RetroInput, RetroWindow } from "@/components/ui";
import { fetchPosAnalytics, runPosAnalysis } from "@/lib/pos/api";
import type { PosAnalytics, PosRecommendationStatus } from "@/lib/pos/types";

const COLORS = ["var(--color-accent)", "var(--color-success)", "var(--color-accent-soft)", "var(--color-danger)", "var(--color-text-muted)"];

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoISO(days: number) {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
}

function fmtPKR(value: number) {
  return `Rs. ${Math.round(value).toLocaleString("en-PK")}`;
}

function fmtPct(value: number | null) {
  return value === null ? "Unavailable" : `${(value * 100).toFixed(1)}%`;
}

function statusVariant(status: PosRecommendationStatus) {
  if (status === "RESTOCK") return "danger";
  if (status === "HOLD") return "accent";
  return "neutral";
}

export default function SalesTrendsPage() {
  const [dateFrom, setDateFrom] = useState(daysAgoISO(6));
  const [dateTo, setDateTo] = useState(todayISO());
  const [horizon, setHorizon] = useState<7 | 30>(7);
  const [analytics, setAnalytics] = useState<PosAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [uploading, setUploading] = useState(false);

  async function load(showSpinner = true) {
    if (showSpinner) setLoading(true);
    setError("");
    try {
      setAnalytics(await fetchPosAnalytics({ from: dateFrom, to: dateTo, horizon }));
    } catch (loadError) {
      setAnalytics(null);
      setError(loadError instanceof Error ? loadError.message : "Could not load POS analytics");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchPosAnalytics({ from: dateFrom, to: dateTo, horizon })
      .then(setAnalytics)
      .catch((loadError) => {
        setAnalytics(null);
        setError(loadError instanceof Error ? loadError.message : "Could not load POS analytics");
      })
      .finally(() => setLoading(false));
  }, [dateFrom, dateTo, horizon]);

  const chartData = useMemo(() => analytics?.conversion.buckets.map((bucket) => ({
    period: bucket.period.slice(5),
    entries: bucket.entries,
    transactions: bucket.transactions,
    conversion: bucket.conversion === null ? 0 : Number((bucket.conversion * 100).toFixed(1)),
  })) || [], [analytics]);

  async function handleAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      await runPosAnalysis({ from: dateFrom, to: dateTo, horizon });
      await load();
    } catch (analysisError) {
      setError(analysisError instanceof Error ? analysisError.message : "Analysis failed");
    }
  }

  async function submitImport(form: HTMLFormElement, mode: "preview" | "commit") {
    const data = new FormData(form);
    setUploading(true);
    setError("");
    try {
      const response = await fetch(`/api/pos/import/${mode}`, { method: "POST", body: data });
      const body = await response.json();
      if (!response.ok || body.ok === false) throw new Error(body.error || body.errors?.[0]?.errors?.[0] || "Import failed");
      setPreview(body);
      if (mode === "commit") await load();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Import failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="min-h-screen bg-bg">
      <main className="mx-auto w-full max-w-[1280px] space-y-8 px-4 py-8 md:px-6 md:py-12">
        <RetroWindow title="Sales & Product Trends - Live POS Analytics">
          <form onSubmit={handleAnalyze} className="grid gap-4 md:grid-cols-[1fr_1fr_auto_auto] md:items-end">
            <RetroInput label="From" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
            <RetroInput label="To" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
            <label className="block">
              <span className="mb-1.5 block font-heading text-xs font-semibold uppercase tracking-wide text-text-muted">Horizon</span>
              <select value={horizon} onChange={(event) => setHorizon(Number(event.target.value) as 7 | 30)} className="h-[42px] rounded-md border-2 border-border bg-surface px-3 font-mono text-sm text-text">
                <option value={7}>7 days</option>
                <option value={30}>30 days</option>
              </select>
            </label>
            <RetroButton type="submit" disabled={loading}>Run analysis</RetroButton>
          </form>
          <p className="mt-4 text-xs leading-relaxed text-text-muted">
            Purchase conversion is completed sale transactions divided by entrance events over covered camera intervals.
          </p>
        </RetroWindow>

        {error && (
          <RetroWindow title="POS Status">
            <p className="text-sm text-danger">{error}</p>
            <p className="mt-2 text-xs text-text-muted">Start the POS service with `uvicorn backend.pos_service:app --host 127.0.0.1 --port 8011` and sign in as the configured manager.</p>
          </RetroWindow>
        )}

        <ImportPanel uploading={uploading} preview={preview} onUpload={submitImport} />

        {!analytics || analytics.products.length === 0 ? (
          <RetroWindow title="No POS Data Imported">
            <p className="text-sm leading-relaxed text-text-muted">
              Upload transactions, inventory, footfall, and opening-calendar CSV/XLSX data to unlock live KPIs, forecasts, recommendations, and cited assistant answers. No mock POS figures are shown here.
            </p>
          </RetroWindow>
        ) : (
          <>
            <RunMeta analytics={analytics} />
            <KpiGrid analytics={analytics} />
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(340px,0.8fr)]">
              <RetroWindow title="Entry-To-Transaction Conversion">
                <div className="h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-soft)" />
                      <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Area type="monotone" dataKey="entries" stroke="var(--color-accent)" fill="var(--color-accent)" fillOpacity={0.12} />
                      <Area type="monotone" dataKey="transactions" stroke="var(--color-success)" fill="var(--color-success)" fillOpacity={0.12} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </RetroWindow>

              <RetroWindow title="Category Revenue Share">
                <div className="h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={analytics.categories} dataKey="net_revenue" nameKey="category" innerRadius={52} outerRadius={90} paddingAngle={3}>
                        {analytics.categories.map((category, index) => <Cell key={category.category} fill={COLORS[index % COLORS.length]} />)}
                      </Pie>
                      <Tooltip formatter={(value) => fmtPKR(Number(value))} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </RetroWindow>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <Leaderboard analytics={analytics} />
              <Recommendations analytics={analytics} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function ImportPanel({ uploading, preview, onUpload }: { uploading: boolean; preview: Record<string, unknown> | null; onUpload: (form: HTMLFormElement, mode: "preview" | "commit") => Promise<void> }) {
  const [form, setForm] = useState<HTMLFormElement | null>(null);
  return (
    <RetroWindow title="Import POS Workbook Or CSV Files">
      <form ref={setForm} className="grid gap-4 md:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_auto] lg:items-end" onSubmit={(event) => { event.preventDefault(); void onUpload(event.currentTarget, "preview"); }}>
        <RetroInput label="Source" name="source" placeholder="main-pos-export" defaultValue="manual-upload" />
        <RetroInput label="Coverage From" name="coverage_from" type="datetime-local" />
        <RetroInput label="Coverage To" name="coverage_to" type="datetime-local" />
        <label className="flex items-end gap-2 pb-2 text-sm text-text">
          <input name="complete" type="checkbox" value="true" className="h-4 w-4" /> Complete export
        </label>
        <input name="files" type="file" accept=".csv,.xlsx" multiple required className="text-sm text-text-muted file:mr-3 file:rounded file:border file:border-border file:bg-surface-alt file:px-3 file:py-2 file:text-text md:col-span-2 lg:col-span-4" />
        <div className="flex flex-wrap gap-2 md:col-span-2 lg:col-span-4">
          <RetroButton type="submit" variant="secondary" disabled={uploading}>Preview</RetroButton>
          <RetroButton type="button" disabled={uploading || !form} onClick={() => form && void onUpload(form, "commit")}>Commit import</RetroButton>
          <a className="inline-flex items-center px-3 text-xs font-semibold text-accent underline underline-offset-2" href="/api/pos/templates">Template contract</a>
        </div>
      </form>
      {preview && (
        <pre className="mt-4 max-h-64 overflow-auto rounded border border-border-soft bg-bg p-3 text-xs text-text-muted">{JSON.stringify(preview, null, 2)}</pre>
      )}
    </RetroWindow>
  );
}

function RunMeta({ analytics }: { analytics: PosAnalytics }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
      <Badge variant="neutral">{analytics.period.from} to {analytics.period.to}</Badge>
      <Badge variant="neutral">{analytics.horizon}-day forecast</Badge>
      <Badge variant={analytics.quality_flags.length ? "accent" : "success"}>{analytics.quality_flags.length ? analytics.quality_flags.join(", ") : "inputs passed basic quality checks"}</Badge>
    </div>
  );
}

function KpiGrid({ analytics }: { analytics: PosAnalytics }) {
  const items = [
    ["Net revenue", fmtPKR(analytics.kpis.net_revenue)],
    ["Sale transactions", analytics.kpis.distinct_sale_transactions.toLocaleString("en-PK")],
    ["Avg basket", fmtPKR(analytics.kpis.average_basket_value)],
    ["Conversion", fmtPct(analytics.conversion.conversion)],
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {items.map(([label, value]) => (
        <RetroCard key={label} label={label}>
          <p className="font-mono text-2xl font-bold text-text">{value}</p>
        </RetroCard>
      ))}
    </div>
  );
}

function Leaderboard({ analytics }: { analytics: PosAnalytics }) {
  return (
    <RetroWindow title="Product Performance">
      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={analytics.products.slice(0, 8)} layout="vertical" margin={{ left: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-soft)" />
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis dataKey="sku_name" type="category" width={120} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="gross_units" fill="var(--color-accent)" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </RetroWindow>
  );
}

function Recommendations({ analytics }: { analytics: PosAnalytics }) {
  return (
    <RetroWindow title="Inventory Recommendations">
      <div className="space-y-3">
        {analytics.recommendations.slice(0, 6).map((rec) => (
          <div key={rec.sku_id} className="rounded-md border border-border-soft bg-bg p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-heading text-sm font-bold text-text">{rec.sku_name}</p>
                <p className="mt-1 text-xs leading-relaxed text-text-muted">{rec.rule}</p>
              </div>
              <Badge variant={statusVariant(rec.status)}>{rec.status}</Badge>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 font-mono text-[11px] text-text-muted">
              <span>Order: <strong className="text-text">{rec.suggested_order_qty}</strong></span>
              <span>On hand: <strong className="text-text">{rec.on_hand ?? "NA"}</strong></span>
              <span>Confidence: <strong className="text-text">{rec.confidence}</strong></span>
            </div>
            {rec.warnings?.length ? <p className="mt-2 text-[11px] text-danger">{rec.warnings.join(", ")}</p> : null}
          </div>
        ))}
      </div>
    </RetroWindow>
  );
}
