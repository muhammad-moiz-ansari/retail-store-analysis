"use client";

import React, { useState } from "react";
import { RetroButton, RetroCard, RetroWindow } from "@/components/ui";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

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

const TODAY_SERIES = [
  { label: "9 AM", score: 78, approach: 25, idle: 20, interaction: 33 },
  { label: "10 AM", score: 80, approach: 26, idle: 20, interaction: 34 },
  { label: "11 AM", score: 82, approach: 27, idle: 20, interaction: 35 },
  { label: "12 PM", score: 79, approach: 25, idle: 20, interaction: 34 },
  { label: "1 PM", score: 83, approach: 27, idle: 21, interaction: 35 },
  { label: "2 PM", score: 85, approach: 28, idle: 21, interaction: 36 },
  { label: "3 PM", score: 87, approach: 28, idle: 22, interaction: 37 },
];

const LAST_SEVEN_DAYS_SERIES = [
  { label: "Mon", score: 74, approach: 24, idle: 18, interaction: 32 },
  { label: "Tue", score: 79, approach: 26, idle: 19, interaction: 34 },
  { label: "Wed", score: 76, approach: 24, idle: 20, interaction: 32 },
  { label: "Thu", score: 91, approach: 29, idle: 23, interaction: 39 },
  { label: "Fri", score: 84, approach: 27, idle: 21, interaction: 36 },
  { label: "Sat", score: 85, approach: 28, idle: 21, interaction: 36 },
  { label: "Sun", score: 87, approach: 28, idle: 22, interaction: 37 },
];

const LAST_THIRTY_DAYS_SERIES = Array.from({ length: 30 }, (_, index) => {
  const score = 71 + Math.min(index, 18) + [0, 2, -1, 1, -2][index % 5];
  const approach = 22 + Math.min(Math.floor(index / 5), 6) + (index % 3 === 0 ? 1 : 0);
  const idle = 17 + Math.min(Math.floor(index / 8), 5) + (index % 4 === 0 ? 1 : 0);
  return {
    label: `Aug ${index + 1}`,
    score,
    approach,
    idle,
    interaction: score - approach - idle,
  };
});

function getSeries(dateRange: DateRange) {
  if (dateRange === "today") return TODAY_SERIES;
  if (dateRange === "last30") return LAST_THIRTY_DAYS_SERIES;
  return LAST_SEVEN_DAYS_SERIES;
}

export default function MyPerformancePage() {
  const [dateRange, setDateRange] = useState<DateRange>("last7");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const summary = dateRange === "custom" ? PERIOD_SUMMARIES.last7 : PERIOD_SUMMARIES[dateRange];
  const series = getSeries(dateRange);

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

        <section aria-labelledby="score-trend-heading">
          <RetroWindow title="Score Trend">
            <h2 id="score-trend-heading" className="sr-only">Score trend</h2>
            <RetroCard>
              <ChartFrame>
                <LineChart data={series} margin={{ top: 12, right: 16, left: -20, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="var(--color-border-soft)" strokeOpacity={0.25} />
                  <XAxis {...axisProps} dataKey="label" interval={dateRange === "last30" ? 4 : 0} />
                  <YAxis {...axisProps} domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} />
                  <Tooltip {...tooltipProps} formatter={(value) => [`${value} / 100`, "Score"]} />
                  <ReferenceLine
                    y={80}
                    stroke="var(--color-text-muted)"
                    strokeDasharray="5 5"
                    label={{ value: "Good", position: "right", fill: "var(--color-text-muted)", fontSize: 12 }}
                  />
                  <Line type="monotone" dataKey="score" stroke="var(--color-accent)" strokeWidth={3} dot={{ fill: "var(--color-accent)", r: 4 }} activeDot={{ r: 5 }} />
                </LineChart>
              </ChartFrame>
            </RetroCard>
          </RetroWindow>
        </section>

        <section aria-labelledby="rubric-heading">
          <RetroWindow title="Score Breakdown by Category">
            <h2 id="rubric-heading" className="sr-only">Score breakdown by category</h2>
            <RetroCard>
              <ChartFrame>
                <LineChart data={series} margin={{ top: 12, right: 16, left: -20, bottom: 0 }}>
                  <CartesianGrid vertical={false} stroke="var(--color-border-soft)" strokeOpacity={0.25} />
                  <XAxis {...axisProps} dataKey="label" interval={dateRange === "last30" ? 4 : 0} />
                  <YAxis {...axisProps} domain={[0, 45]} ticks={[0, 15, 30, 45]} />
                  <Tooltip {...tooltipProps} />
                  <Legend wrapperStyle={{ fontFamily: "var(--font-jetbrains-mono)", fontSize: "12px", paddingTop: "12px" }} />
                  <Line type="monotone" name="Approach Speed" dataKey="approach" stroke="var(--color-accent)" strokeWidth={2.5} dot={{ r: 3 }} />
                  <Line type="monotone" name="Idle Time" dataKey="idle" stroke="var(--color-accent-soft)" strokeWidth={2.5} dot={{ r: 3 }} />
                  <Line type="monotone" name="Interaction Score" dataKey="interaction" stroke="var(--color-success)" strokeWidth={2.5} dot={{ r: 3 }} />
                </LineChart>
              </ChartFrame>
            </RetroCard>
          </RetroWindow>
        </section>
      </main>
    </div>
  );
}

const axisProps = {
  axisLine: false,
  tickLine: false,
  tick: { fill: "var(--color-text-muted)", fontSize: 12, fontFamily: "var(--font-jetbrains-mono)" },
};

const tooltipProps = {
  cursor: { stroke: "var(--color-accent-soft)", strokeWidth: 1 },
  contentStyle: {
    backgroundColor: "var(--color-surface)",
    border: "1px solid var(--color-border-soft)",
    borderRadius: "6px",
    color: "var(--color-text)",
    fontFamily: "var(--font-jetbrains-mono)",
    fontSize: "12px",
  },
};

function ChartFrame({ children }: { children: React.ReactElement }) {
  return <div className="h-[300px] w-full"><ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer></div>;
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
