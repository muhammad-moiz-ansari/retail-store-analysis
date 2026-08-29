"use client";

import React, { useState } from "react";
import { RetroWindow, RetroCard, RetroButton, Badge } from "@/components/ui";

type DateRangeOption = "last7" | "last30" | "thisMonth" | "custom";

interface ReportModule {
  key: string;
  label: string;
  description: string;
  checked: boolean;
}

export default function ReportsPage() {
  const [dateRange, setDateRange] = useState<DateRangeOption>("last7");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [showAISummary, setShowAISummary] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const [modules, setModules] = useState<ReportModule[]>([
    {
      key: "footfall",
      label: "Footfall & Traffic",
      description: "Daily in/out counts, peak hours, crowd density",
      checked: true,
    },
    {
      key: "service",
      label: "Service Quality & Engagement",
      description: "Attended ratio, response times, interaction durations",
      checked: true,
    },
    {
      key: "employee",
      label: "Employee Performance",
      description: "Staff scores, leaderboard, idle time, zone coverage",
      checked: true,
    },
    {
      key: "spatial",
      label: "Spatial Analytics & Heatmaps",
      description: "Zone dwell times, customer paths, heatmap snapshot",
      checked: true,
    },
    {
      key: "sales",
      label: "Sales & Product Trends",
      description: "Top SKUs, category performance, sales funnel",
      checked: true,
    },
    {
      key: "raw",
      label: "Raw Data Tables (CSV-style)",
      description: "Exportable tabular data for each selected module",
      checked: false,
    },
  ]);

  const toggleModule = (key: string) => {
    setModules((prev) =>
      prev.map((m) => (m.key === key ? { ...m, checked: !m.checked } : m))
    );
  };

  const handleGenerateSummary = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      setShowAISummary(true);
      // Smooth scroll to AI summary
      setTimeout(() => {
        document.getElementById("ai-summary")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 100);
    }, 1500);
  };

  const handleExport = () => {
    window.print();
  };

  const getDateRangeDisplay = () => {
    if (dateRange === "last7") return "Last 7 Days (21 Aug – 28 Aug 2026)";
    if (dateRange === "last30") return "Last 30 Days (29 Jul – 28 Aug 2026)";
    if (dateRange === "thisMonth") return "This Month (1 Aug – 28 Aug 2026)";
    if (dateRange === "custom" && customFrom && customTo) {
      return `Custom Range (${new Date(customFrom).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
      })} – ${new Date(customTo).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })})`;
    }
    return "Last 7 Days (21 Aug – 28 Aug 2026)";
  };

  return (
    <div className="min-h-screen bg-background pb-16">
      <div className="max-w-[1280px] mx-auto px-4 md:px-6 lg:px-8 pt-6 space-y-6">
        {/* ── Page Header ── */}
        <RetroWindow title="Reports & Exports">
          <p className="text-sm text-text-muted leading-relaxed">
            Generate, preview, and export store analytics reports. Select a date
            range and modules, then run the AI summary before exporting.
          </p>
        </RetroWindow>

        {/* ── Section 1: Report Builder ── */}
        <RetroWindow title="Configure Report">
          <RetroCard>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-6">
              {/* Left: Date Range */}
              <div className="space-y-3">
                <label className="block font-heading text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Date Range
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <DateRangeButton
                    label="Last 7 Days"
                    active={dateRange === "last7"}
                    onClick={() => setDateRange("last7")}
                  />
                  <DateRangeButton
                    label="Last 30 Days"
                    active={dateRange === "last30"}
                    onClick={() => setDateRange("last30")}
                  />
                  <DateRangeButton
                    label="This Month"
                    active={dateRange === "thisMonth"}
                    onClick={() => setDateRange("thisMonth")}
                  />
                  <DateRangeButton
                    label="Custom"
                    active={dateRange === "custom"}
                    onClick={() => setDateRange("custom")}
                  />
                </div>

                {dateRange === "custom" && (
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div>
                      <label className="block text-xs text-text-muted mb-1">
                        From:
                      </label>
                      <input
                        type="date"
                        value={customFrom}
                        onChange={(e) => setCustomFrom(e.target.value)}
                        className="w-full px-3 py-2 text-sm bg-surface border border-border rounded text-text focus:outline-none focus:ring-2 focus:ring-accent"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-text-muted mb-1">
                        To:
                      </label>
                      <input
                        type="date"
                        value={customTo}
                        onChange={(e) => setCustomTo(e.target.value)}
                        className="w-full px-3 py-2 text-sm bg-surface border border-border rounded text-text focus:outline-none focus:ring-2 focus:ring-accent"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Right: Report Modules */}
              <div className="space-y-3">
                <label className="block font-heading text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Include in Report
                </label>
                <div className="space-y-2">
                  {modules.map((module) => (
                    <ModuleCheckbox
                      key={module.key}
                      label={module.label}
                      description={module.description}
                      checked={module.checked}
                      onChange={() => toggleModule(module.key)}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-border-soft">
              <RetroButton
                variant="primary"
                onClick={handleGenerateSummary}
                disabled={isGenerating}
              >
                {isGenerating ? "Generating summary…" : "Generate AI Summary"}
              </RetroButton>
              <RetroButton variant="secondary" onClick={handleExport}>
                ↓ Export PDF
              </RetroButton>
              <p className="text-xs text-text-muted italic ml-auto">
                Opens browser print dialog. Select 'Save as PDF' to export.
              </p>
            </div>
          </RetroCard>
        </RetroWindow>

        {/* ── Section 2: AI Insight Narrative ── */}
        {showAISummary && (
          <div
            id="ai-summary"
            className="animate-fadeIn"
            style={{
              animation: "fadeIn 0.4s ease-out",
            }}
          >
            <RetroWindow title="AI-Generated Summary">
              <RetroCard
                className="border-l-4 !border-l-accent-soft !shadow-lg"
                style={{ padding: "1.5rem" }}
              >
                {/* Header */}
                <div className="space-y-2 mb-6 pb-4 border-b border-border-soft">
                  <Badge variant="accent">
                    Generated by RetailPulse Insight Agent
                  </Badge>
                  <p className="text-sm text-text-muted font-mono">
                    Report period: {getDateRangeDisplay()}
                  </p>
                </div>

                {/* AI Narrative */}
                <div className="space-y-5 text-text leading-relaxed">
                  <p>
                    This week, your store recorded <strong>1,742 customer visits</strong> — a <strong>12% increase</strong> over the previous 7-day period. Peak footfall occurred on Thursday between 2:00 PM and 5:00 PM, accounting for 18% of weekly traffic in a single afternoon window.
                  </p>
                  <p>
                    Service quality improved marginally: the store-wide average staff score reached <strong>84/100</strong>, up from 79 last week. Average time to first approach held at <strong>1 minute 52 seconds</strong> — within the 2-minute target — though 3 coverage gaps were recorded in Aisle 2 and the Promo Display zone, totaling 1 hour 47 minutes of unstaffed floor time. This is the primary area flagged for operational attention.
                  </p>
                  <p>
                    Customer engagement deepened: average interaction duration increased to <strong>3 minutes 27 seconds</strong> (up from 2 minutes 58 seconds), and the attended-to-unattended customer ratio improved to 72% attended. Customers spent an average of 14 minutes 30 seconds in-store, with the Promo Display and Checkout Counter recording the highest dwell times at 4m 50s and 5m 30s respectively.
                  </p>
                  <p>
                    The Promo Display zone continues to generate strong dwell time but has not converted to proportionally high sales — this warrants a review of the current promotional placement or product mix in that zone.
                  </p>
                  <p>
                    Staffing efficiency was strongest between 10:00 AM and 11:00 AM. Staff 03 led the leaderboard with 87 points; Staff 04 recorded the lowest score at 60 points, driven primarily by above-average idle time. Workload distribution is uneven — consider redeploying underutilized staff to high-traffic periods.
                  </p>
                </div>

                {/* Export Action */}
                <div className="mt-6 pt-4 border-t border-border-soft flex items-center justify-between">
                  <RetroButton variant="secondary" onClick={handleExport}>
                    ↓ Export PDF
                  </RetroButton>
                  <p className="text-xs text-text-muted italic">
                    The AI summary will be included in the exported report.
                  </p>
                </div>
              </RetroCard>
            </RetroWindow>
          </div>
        )}

        {/* ── Section 3: Export History ── */}
        <RetroWindow title="Recent Exports">
          <RetroCard>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border-soft">
                    <th className="text-left py-2 px-3 font-mono text-xs uppercase tracking-wider text-text-muted">
                      Date Generated
                    </th>
                    <th className="text-left py-2 px-3 font-mono text-xs uppercase tracking-wider text-text-muted">
                      Period
                    </th>
                    <th className="text-left py-2 px-3 font-mono text-xs uppercase tracking-wider text-text-muted">
                      Modules
                    </th>
                    <th className="text-left py-2 px-3 font-mono text-xs uppercase tracking-wider text-text-muted">
                      Exported By
                    </th>
                    <th className="text-left py-2 px-3 font-mono text-xs uppercase tracking-wider text-text-muted">
                      Format
                    </th>
                    <th className="text-right py-2 px-3 font-mono text-xs uppercase tracking-wider text-text-muted">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <ExportHistoryRow
                    date="27 Aug 2026"
                    period="Last 7 Days"
                    modules="All modules"
                    exportedBy="Manager"
                    format="PDF"
                    onReexport={handleExport}
                  />
                  <ExportHistoryRow
                    date="20 Aug 2026"
                    period="Last 30 Days"
                    modules="Footfall, Engagement"
                    exportedBy="Manager"
                    format="PDF"
                    onReexport={handleExport}
                  />
                  <ExportHistoryRow
                    date="13 Aug 2026"
                    period="This Month"
                    modules="All modules"
                    exportedBy="Manager"
                    format="PDF"
                    onReexport={handleExport}
                  />
                </tbody>
              </table>
            </div>
            <p className="text-xs text-text-muted italic mt-4">
              Export history is stored locally for this session only.
            </p>
          </RetroCard>
        </RetroWindow>
      </div>

      {/* Print Styles */}
      <style jsx global>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @media print {
          header,
          footer,
          .no-print {
            display: none !important;
          }

          /* Hide everything except AI summary when printing */
          body * {
            visibility: hidden;
          }

          #ai-summary,
          #ai-summary * {
            visibility: visible;
          }

          #ai-summary {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}

/* ── Helper Components ── */

interface DateRangeButtonProps {
  label: string;
  active: boolean;
  onClick: () => void;
}

function DateRangeButton({ label, active, onClick }: DateRangeButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "px-3 py-2 text-sm font-heading font-semibold rounded border-2 transition-all duration-150",
        active
          ? "bg-accent text-surface border-accent"
          : "bg-surface text-text border-border hover:border-accent",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

interface ModuleCheckboxProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: () => void;
}

function ModuleCheckbox({
  label,
  description,
  checked,
  onChange,
}: ModuleCheckboxProps) {
  return (
    <label className="flex items-start gap-3 p-3 rounded border border-border-soft bg-surface hover:border-accent/50 cursor-pointer transition-colors group">
      <div className="relative flex-shrink-0 mt-0.5">
        <input
          type="checkbox"
          checked={checked}
          onChange={onChange}
          className="sr-only"
        />
        <div
          className={[
            "w-5 h-5 rounded border-2 flex items-center justify-center transition-all",
            checked
              ? "bg-accent border-accent"
              : "bg-surface border-border group-hover:border-accent",
          ].join(" ")}
        >
          {checked && (
            <svg
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="none"
              className="text-surface"
            >
              <path
                d="M2 6L5 9L10 3"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </div>
      </div>
      <div className="flex-1">
        <div className="text-sm font-medium text-text">{label}</div>
        <div className="text-xs text-text-muted mt-0.5">{description}</div>
      </div>
    </label>
  );
}

interface ExportHistoryRowProps {
  date: string;
  period: string;
  modules: string;
  exportedBy: string;
  format: string;
  onReexport: () => void;
}

function ExportHistoryRow({
  date,
  period,
  modules,
  exportedBy,
  format,
  onReexport,
}: ExportHistoryRowProps) {
  return (
    <tr className="border-b border-border-soft/50 hover:bg-surface-alt/30 transition-colors">
      <td className="py-2.5 px-3 text-text">{date}</td>
      <td className="py-2.5 px-3 text-text">{period}</td>
      <td className="py-2.5 px-3 text-text">{modules}</td>
      <td className="py-2.5 px-3 text-text">{exportedBy}</td>
      <td className="py-2.5 px-3 text-text font-mono">{format}</td>
      <td className="py-2.5 px-3 text-right">
        <button
          type="button"
          onClick={onReexport}
          className="text-accent text-xs font-semibold hover:underline"
        >
          Re-export
        </button>
      </td>
    </tr>
  );
}
