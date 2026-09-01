"use client";

import React, { useState } from "react";
import { RetroButton, RetroCard, RetroWindow } from "@/components/ui";

type DateRange = "today" | "last7" | "last30" | "custom";

const PERIOD_SUMMARIES: Record<Exclude<DateRange, "custom">, {
  average: string;
  delta: string;
  interactions: string;
  bestDay: string;
}> = {
  today: {
    average: "87 / 100",
    delta: "↑ 4 pts vs. prior shift",
    interactions: "12 interactions",
    bestDay: "Today — 87 pts",
  },
  last7: {
    average: "83 / 100",
    delta: "↑ 6 pts vs. prior 7 days",
    interactions: "94 interactions",
    bestDay: "Thursday — 91 pts",
  },
  last30: {
    average: "79 / 100",
    delta: "↑ 8 pts vs. prior 30 days",
    interactions: "382 interactions",
    bestDay: "Aug 28 — 91 pts",
  },
};

const RANGE_OPTIONS: { id: DateRange; label: string }[] = [
  { id: "today", label: "Today" },
  { id: "last7", label: "Last 7 Days" },
  { id: "last30", label: "Last 30 Days" },
  { id: "custom", label: "Custom" },
];

export default function MyPerformancePage() {
  const [dateRange, setDateRange] = useState<DateRange>("last7");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const summary = dateRange === "custom" ? PERIOD_SUMMARIES.last7 : PERIOD_SUMMARIES[dateRange];

  return (
    <div className="min-h-screen bg-bg">
      <main className="mx-auto w-full max-w-[1280px] space-y-12 px-4 py-10 md:px-6 md:py-16 lg:px-8">
        <RetroWindow title="My Performance">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.16em] text-accent">
            Performance History
          </p>
          <h1 className="mt-2 font-heading text-3xl font-bold tracking-tight text-text md:text-[32px]">
            Your Performance Over Time
          </h1>
          <p className="mt-2 text-sm text-text-muted">
            Track your scores, interactions, and activity across any period.
          </p>
        </RetroWindow>

        <section aria-labelledby="date-range-heading">
          <RetroWindow title="Date Range">
            <h2 id="date-range-heading" className="sr-only">Date range selector</h2>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Select performance date range">
              {RANGE_OPTIONS.map((option) => (
                <RetroButton
                  key={option.id}
                  type="button"
                  variant={dateRange === option.id ? "primary" : "secondary"}
                  onClick={() => setDateRange(option.id)}
                >
                  {option.label}
                </RetroButton>
              ))}
            </div>
            {dateRange === "custom" && (
              <div className="mt-5 grid max-w-xl gap-4 sm:grid-cols-2">
                <label className="font-heading text-xs font-semibold uppercase tracking-wider text-text-muted">
                  From
                  <input
                    type="date"
                    value={customFrom}
                    onChange={(event) => setCustomFrom(event.target.value)}
                    className="mt-1.5 w-full rounded border border-border bg-surface px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </label>
                <label className="font-heading text-xs font-semibold uppercase tracking-wider text-text-muted">
                  To
                  <input
                    type="date"
                    value={customTo}
                    onChange={(event) => setCustomTo(event.target.value)}
                    className="mt-1.5 w-full rounded border border-border bg-surface px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </label>
              </div>
            )}
          </RetroWindow>
        </section>

        <section aria-label="Performance summary">
          <div className="grid gap-5 md:grid-cols-3">
            <SummaryCard label="Average Score" value={summary.average} detail="across selected period" trend={summary.delta} />
            <SummaryCard label="Total Interactions" value={summary.interactions} detail="customers engaged in this period" />
            <SummaryCard label="Best Day" value={summary.bestDay} detail="your strongest performance in this period" />
          </div>
        </section>
      </main>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  detail,
  trend,
}: {
  label: string;
  value: string;
  detail: string;
  trend?: string;
}) {
  return (
    <RetroCard>
      <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-text-muted">{label}</p>
      <p className="mt-3 font-mono text-2xl font-bold text-accent">{value}</p>
      <p className="mt-1 text-sm text-text-muted">{detail}</p>
      {trend && <p className="mt-3 font-mono text-xs font-semibold text-success">{trend}</p>}
    </RetroCard>
  );
}
