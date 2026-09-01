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

type DailyLog = {
  date: string;
  approach: number;
  idle: number;
  interaction: number;
  total: number;
  interactions: number;
  shift: string;
  zone: string;
  flaggedMoments: string[];
};

const DAILY_LOGS: DailyLog[] = [
  { date: "Aug 28", approach: 28, idle: 22, interaction: 37, total: 87, interactions: 14, shift: "9:00 AM – 6:00 PM", zone: "Electronics Floor", flaggedMoments: ["11:15 AM — 4m 20s idle, Electronics Floor"] },
  { date: "Aug 27", approach: 26, idle: 20, interaction: 35, total: 81, interactions: 12, shift: "9:00 AM – 6:00 PM", zone: "Electronics Floor", flaggedMoments: ["2:40 PM — 3m 10s idle, Electronics Floor"] },
  { date: "Aug 26", approach: 24, idle: 19, interaction: 32, total: 75, interactions: 11, shift: "9:00 AM – 6:00 PM", zone: "Mobile Accessories", flaggedMoments: ["4:05 PM — 5m 05s idle, Mobile Accessories"] },
  { date: "Aug 25", approach: 29, idle: 23, interaction: 39, total: 91, interactions: 15, shift: "9:00 AM – 6:00 PM", zone: "Electronics Floor", flaggedMoments: [] },
  { date: "Aug 24", approach: 27, idle: 21, interaction: 36, total: 84, interactions: 13, shift: "9:00 AM – 6:00 PM", zone: "Electronics Floor", flaggedMoments: ["1:20 PM — 3m 45s idle, Electronics Floor"] },
  { date: "Aug 23", approach: 28, idle: 21, interaction: 36, total: 85, interactions: 14, shift: "10:00 AM – 7:00 PM", zone: "Electronics Floor", flaggedMoments: [] },
  { date: "Aug 22", approach: 24, idle: 18, interaction: 32, total: 74, interactions: 10, shift: "10:00 AM – 7:00 PM", zone: "Home Appliances", flaggedMoments: ["12:10 PM — 4m 40s idle, Home Appliances", "4:30 PM — unattended customer alert, Home Appliances"] },
  { date: "Aug 21", approach: 23, idle: 18, interaction: 31, total: 72, interactions: 9, shift: "9:00 AM – 6:00 PM", zone: "Home Appliances", flaggedMoments: ["3:05 PM — 4m 05s idle, Home Appliances"] },
  { date: "Aug 20", approach: 25, idle: 19, interaction: 33, total: 77, interactions: 11, shift: "9:00 AM – 6:00 PM", zone: "Mobile Accessories", flaggedMoments: [] },
  { date: "Aug 19", approach: 23, idle: 18, interaction: 31, total: 72, interactions: 9, shift: "10:00 AM – 7:00 PM", zone: "Electronics Floor", flaggedMoments: ["5:15 PM — 4m 30s idle, Electronics Floor"] },
];

function getSeries(dateRange: DateRange) {
  if (dateRange === "today") return TODAY_SERIES;
  if (dateRange === "last30") return LAST_THIRTY_DAYS_SERIES;
  return LAST_SEVEN_DAYS_SERIES;
}

function getDailyLogs(dateRange: DateRange) {
  if (dateRange === "today") return DAILY_LOGS.slice(0, 1);
  if (dateRange === "last30") return DAILY_LOGS;
  return DAILY_LOGS.slice(0, 7);
}

export default function MyPerformancePage() {
  const [dateRange, setDateRange] = useState<DateRange>("last7");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [expandedDate, setExpandedDate] = useState<string | null>(null);
  const summary = dateRange === "custom" ? PERIOD_SUMMARIES.last7 : PERIOD_SUMMARIES[dateRange];
  const series = getSeries(dateRange);
  const dailyLogs = getDailyLogs(dateRange);

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

        <section aria-labelledby="daily-log-heading">
          <RetroWindow title="Daily Log">
            <h2 id="daily-log-heading" className="sr-only">Daily performance log</h2>
            <RetroCard>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-sm">
                  <thead>
                    <tr className="border-b border-border-soft bg-surface-alt text-left">
                      {['Date', 'Approach Speed', 'Idle Time', 'Interaction', 'Total', 'Interactions'].map((heading, index) => (
                        <th key={heading} className={`px-3 py-2 font-mono text-[11px] font-semibold uppercase tracking-wider text-text-muted ${index > 0 ? 'text-right' : ''}`}>
                          {heading}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {dailyLogs.map((log, index) => {
                      const isExpanded = expandedDate === log.date;
                      return (
                        <React.Fragment key={log.date}>
                          <tr
                            role="button"
                            tabIndex={0}
                            aria-expanded={isExpanded}
                            onClick={() => setExpandedDate(isExpanded ? null : log.date)}
                            onKeyDown={(event) => {
                              if (event.key === "Enter" || event.key === " ") {
                                event.preventDefault();
                                setExpandedDate(isExpanded ? null : log.date);
                              }
                            }}
                            className={`cursor-pointer border-b border-border-soft/50 transition-colors hover:bg-surface ${index % 2 === 0 ? "bg-bg/30" : "bg-surface"}`}
                          >
                            <td className="px-3 py-3 font-mono text-text">{log.date}</td>
                            <td className="px-3 py-3 text-right font-mono text-text-muted">{log.approach}</td>
                            <td className="px-3 py-3 text-right font-mono text-text-muted">{log.idle}</td>
                            <td className="px-3 py-3 text-right font-mono text-text-muted">{log.interaction}</td>
                            <td className="px-3 py-3 text-right font-mono font-bold text-accent">{log.total}</td>
                            <td className="px-3 py-3 text-right font-mono text-text-muted">{log.interactions}</td>
                          </tr>
                          <tr aria-hidden={!isExpanded}>
                            <td colSpan={6} className="p-0">
                              <div className={`overflow-hidden transition-all duration-300 ${isExpanded ? "max-h-64 border-b border-border-soft/50" : "max-h-0"}`}>
                                <div className="grid gap-4 bg-surface-alt/40 px-4 py-4 sm:grid-cols-2">
                                  <div>
                                    <p className="font-mono text-[10px] font-semibold uppercase tracking-wider text-text-muted">Shift details</p>
                                    <p className="mt-1 text-sm text-text"><span className="font-medium">Shift:</span> {log.shift}</p>
                                    <p className="mt-1 text-sm text-text"><span className="font-medium">Zone:</span> {log.zone}</p>
                                  </div>
                                  <div>
                                    <p className="font-mono text-[10px] font-semibold uppercase tracking-wider text-text-muted">Flagged moments</p>
                                    {log.flaggedMoments.length > 0 ? (
                                      <ul className="mt-2 space-y-2">
                                        {log.flaggedMoments.map((moment) => (
                                          <li key={moment} className="border-l-4 border-l-accent-soft bg-surface px-3 py-2 text-xs leading-relaxed text-text-muted">
                                            {moment}
                                          </li>
                                        ))}
                                      </ul>
                                    ) : (
                                      <p className="mt-1 text-sm text-text-muted">No flagged idle or unattended moments.</p>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </td>
                          </tr>
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </RetroCard>
          </RetroWindow>
        </section>

        <section aria-label="Performance data context">
          <RetroCard className="border-l-4 border-l-accent-soft">
            <p className="text-sm leading-relaxed text-text-muted">
              Your performance data is visible only to you and your manager. If a number looks off, or a shift wasn&apos;t logged correctly, talk to your floor lead — this system supports conversations, it doesn&apos;t replace them.
            </p>
          </RetroCard>
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
