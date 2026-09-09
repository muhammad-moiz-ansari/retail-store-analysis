"use client";

import React, { useEffect, useMemo, useState } from "react";
import jsPDF from "jspdf";
import { Badge, RetroButton, RetroCard, RetroInput, RetroWindow } from "@/components/ui";
import { askPos, fetchPosAnalytics } from "@/lib/pos/api";
import type { PosAnalytics } from "@/lib/pos/types";

type DateRangeOption = "last7" | "last30" | "thisMonth" | "custom";

function isoDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function rangeFor(option: DateRangeOption, customFrom: string, customTo: string) {
  const end = new Date();
  const start = new Date();
  if (option === "last30") start.setDate(end.getDate() - 29);
  else if (option === "thisMonth") start.setDate(1);
  else start.setDate(end.getDate() - 6);
  if (option === "custom" && customFrom && customTo) return { from: customFrom, to: customTo };
  return { from: isoDate(start), to: isoDate(end) };
}

function fmtPKR(value: number) {
  return `Rs. ${Math.round(value).toLocaleString("en-PK")}`;
}

export default function ReportsPage() {
  const [dateRange, setDateRange] = useState<DateRangeOption>("last7");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [analytics, setAnalytics] = useState<PosAnalytics | null>(null);
  const [summary, setSummary] = useState("");
  const [status, setStatus] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const range = useMemo(() => rangeFor(dateRange, customFrom, customTo), [customFrom, customTo, dateRange]);

  useEffect(() => {
    fetchPosAnalytics({ from: range.from, to: range.to, horizon: 7 })
      .then((data) => {
        setAnalytics(data);
        setStatus("");
      })
      .catch((error) => {
        setAnalytics(null);
        setStatus(error instanceof Error ? error.message : "POS analytics unavailable");
      });
  }, [range.from, range.to]);

  async function handleGenerateSummary() {
    setIsGenerating(true);
    setStatus("");
    try {
      const answer = await askPos("Summarize POS performance and inventory recommendations for this report period", { from: range.from, to: range.to, horizon: 7 });
      setSummary(answer.answer);
      setAnalytics(await fetchPosAnalytics({ from: range.from, to: range.to, horizon: 7 }));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not generate POS summary");
    } finally {
      setIsGenerating(false);
    }
  }

  function generatePDF() {
    const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
    const marginLeft = 20;
    const contentWidth = 170;
    let y = 18;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(22);
    doc.text("RETAILPULSE", marginLeft, y);
    y += 8;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.text(`Report period: ${range.from} to ${range.to}`, marginLeft, y);
    y += 10;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    doc.text("POS Analytics Summary", marginLeft, y);
    y += 8;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    const paragraphs = [
      analytics ? `Net revenue: ${fmtPKR(analytics.kpis.net_revenue)}. Sale transactions: ${analytics.kpis.distinct_sale_transactions}. Purchase conversion: ${analytics.conversion.conversion === null ? "unavailable" : `${(analytics.conversion.conversion * 100).toFixed(1)}%`}.` : "No completed POS analytics run is available for this period.",
      summary || "No cited assistant summary has been generated for this report.",
      analytics ? `Quality flags: ${analytics.quality_flags.join(", ") || "none"}. Dataset version: ${analytics.dataset_version}.` : "",
    ].filter(Boolean);
    for (const paragraph of paragraphs) {
      const lines = doc.splitTextToSize(paragraph, contentWidth);
      for (const line of lines) {
        if (y > 280) {
          doc.addPage();
          y = 18;
        }
        doc.text(line, marginLeft, y);
        y += 6;
      }
      y += 3;
    }
    doc.save(`RetailPulse_POS_${range.from}_${range.to}.pdf`);
  }

  function handleExport() {
    setIsExporting(true);
    try {
      generatePDF();
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <div className="min-h-screen bg-background pb-16">
      <div className="mx-auto max-w-[1280px] space-y-6 px-4 pt-6 md:px-6 lg:px-8">
        <RetroWindow title="Reports & Exports">
          <p className="text-sm leading-relaxed text-text-muted">
            Reports now use the completed POS analytics run for the selected period. Missing POS data stays visible as unavailable instead of being replaced with mock figures.
          </p>
        </RetroWindow>

        <RetroWindow title="Configure Report">
          <RetroCard>
            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-3">
                <label className="block font-heading text-xs font-semibold uppercase tracking-wider text-text-muted">Date range</label>
                <div className="grid grid-cols-2 gap-2">
                  {(["last7", "last30", "thisMonth", "custom"] as DateRangeOption[]).map((option) => (
                    <button key={option} type="button" onClick={() => setDateRange(option)} className={`rounded-md border px-3 py-2 text-sm font-semibold ${dateRange === option ? "border-accent bg-accent text-surface" : "border-border bg-surface text-text"}`}>
                      {option === "last7" ? "Last 7" : option === "last30" ? "Last 30" : option === "thisMonth" ? "This month" : "Custom"}
                    </button>
                  ))}
                </div>
                {dateRange === "custom" && (
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <RetroInput label="From" type="date" value={customFrom} onChange={(event) => setCustomFrom(event.target.value)} />
                    <RetroInput label="To" type="date" value={customTo} onChange={(event) => setCustomTo(event.target.value)} />
                  </div>
                )}
              </div>
              <div className="space-y-3">
                <label className="block font-heading text-xs font-semibold uppercase tracking-wider text-text-muted">Included modules</label>
                <div className="space-y-2 text-sm text-text-muted">
                  <p className="rounded-md border border-border-soft bg-bg px-3 py-2">Sales & Product Trends</p>
                  <p className="rounded-md border border-border-soft bg-bg px-3 py-2">Purchase Conversion</p>
                  <p className="rounded-md border border-border-soft bg-bg px-3 py-2">Inventory Recommendations</p>
                </div>
              </div>
            </div>
            <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-border-soft pt-4">
              <RetroButton variant="primary" onClick={handleGenerateSummary} disabled={isGenerating}>
                {isGenerating ? "Generating" : "Generate cited summary"}
              </RetroButton>
              <RetroButton variant="secondary" onClick={handleExport} disabled={isExporting}>
                {isExporting ? "Exporting" : "Export PDF"}
              </RetroButton>
              <p className="ml-auto text-xs italic text-text-muted">Period: {range.from} to {range.to}</p>
            </div>
          </RetroCard>
        </RetroWindow>

        {status && (
          <RetroWindow title="Report Data Status">
            <p className="text-sm text-danger">{status}</p>
          </RetroWindow>
        )}

        <RetroWindow title="POS Report Preview">
          {analytics ? (
            <div className="grid gap-4 md:grid-cols-4">
              <RetroCard label="Net revenue"><p className="font-mono text-xl font-bold text-text">{fmtPKR(analytics.kpis.net_revenue)}</p></RetroCard>
              <RetroCard label="Transactions"><p className="font-mono text-xl font-bold text-text">{analytics.kpis.distinct_sale_transactions}</p></RetroCard>
              <RetroCard label="Conversion"><p className="font-mono text-xl font-bold text-text">{analytics.conversion.conversion === null ? "NA" : `${(analytics.conversion.conversion * 100).toFixed(1)}%`}</p></RetroCard>
              <RetroCard label="Recommendations"><p className="font-mono text-xl font-bold text-text">{analytics.recommendations.length}</p></RetroCard>
            </div>
          ) : (
            <p className="text-sm text-text-muted">No completed POS analytics run is available for this period.</p>
          )}
          {summary && (
            <div id="ai-summary" className="mt-6 rounded-md border border-border-soft bg-bg p-4">
              <Badge variant="accent">Cited POS assistant summary</Badge>
              <p className="mt-3 text-sm leading-relaxed text-text">{summary}</p>
            </div>
          )}
        </RetroWindow>
      </div>
    </div>
  );
}
