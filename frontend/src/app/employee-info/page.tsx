"use client";

import React from "react";
import { RetroWindow, RetroCard } from "@/components/ui";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  PieChart,
  Pie,
  Cell,
} from "recharts";

/* ═══════════════════════════════════════════════════════════════
   Mock data
   ═══════════════════════════════════════════════════════════════ */

const LEADERBOARD = [
  { rank: 1, id: "Staff 03", approach: 28, idle: 22, interaction: 37, total: 87 },
  { rank: 2, id: "Staff 01", approach: 26, idle: 20, interaction: 35, total: 81 },
  { rank: 3, id: "Staff 05", approach: 25, idle: 19, interaction: 33, total: 77 },
  { rank: 4, id: "Staff 02", approach: 22, idle: 17, interaction: 30, total: 69 },
  { rank: 5, id: "Staff 04", approach: 19, idle: 14, interaction: 27, total: 60 },
];

const INTERACTION_SPARKLINE_7D = [
  { day: "Mon", mins: 3.1 },
  { day: "Tue", mins: 3.5 },
  { day: "Wed", mins: 4.0 },
  { day: "Thu", mins: 2.8 },
  { day: "Fri", mins: 3.9 },
  { day: "Sat", mins: 3.4 },
  { day: "Sun", mins: 3.2 },
];

const RESPONSE_TIME_HOURLY = [
  { hour: "9 AM", seconds: 85 },
  { hour: "10 AM", seconds: 92 },
  { hour: "11 AM", seconds: 105 },
  { hour: "12 PM", seconds: 145 },
  { hour: "1 PM", seconds: 168 },
  { hour: "2 PM", seconds: 198 },
  { hour: "3 PM", seconds: 155 },
  { hour: "4 PM", seconds: 130 },
  { hour: "5 PM", seconds: 142 },
  { hour: "6 PM", seconds: 195 },
  { hour: "7 PM", seconds: 110 },
  { hour: "8 PM", seconds: 78 },
  { hour: "9 PM", seconds: 72 },
];

const ACTIVE_IDLE_SPLIT = [
  { name: "Active", value: 67, color: "var(--color-success)" },
  { name: "Idle", value: 33, color: "var(--color-border-soft)" },
];

const STAFF_IDLE = [
  { id: "Staff 01", idle: "1h 20m", mins: 80 },
  { id: "Staff 02", idle: "2h 10m", mins: 130 },
  { id: "Staff 03", idle: "1h 05m", mins: 65 },
  { id: "Staff 04", idle: "2h 25m", mins: 145 },
  { id: "Staff 05", idle: "1h 40m", mins: 100 },
];

const UNSTAFFED_ALERTS = [
  { time: "10:15–10:57 AM", zone: "Aisle 2 - Beverages", duration: "42 min" },
  { time: "01:30–01:58 PM", zone: "Promo Display", duration: "28 min" },
  { time: "03:45–04:22 PM", zone: "Aisle 1 - Snacks", duration: "37 min" },
];

const HOURLY_DUAL = [
  { hour: "9 AM",  interactions: 14, idle: 2 },
  { hour: "10 AM", interactions: 19, idle: 1 },
  { hour: "11 AM", interactions: 18, idle: 2 },
  { hour: "12 PM", interactions: 12, idle: 4 },
  { hour: "1 PM",  interactions: 10, idle: 5 },
  { hour: "2 PM",  interactions: 8,  idle: 6 },
  { hour: "3 PM",  interactions: 11, idle: 4 },
  { hour: "4 PM",  interactions: 13, idle: 3 },
  { hour: "5 PM",  interactions: 12, idle: 4 },
  { hour: "6 PM",  interactions: 9,  idle: 5 },
  { hour: "7 PM",  interactions: 15, idle: 2 },
  { hour: "8 PM",  interactions: 16, idle: 1 },
  { hour: "9 PM",  interactions: 14, idle: 2 },
];

const ZONE_BREAKDOWN = [
  { zone: "Entrance Lobby",     active: 82, idle: 18 },
  { zone: "Aisle 1 - Snacks",   active: 61, idle: 39 },
  { zone: "Aisle 2 - Beverages", active: 55, idle: 45 },
  { zone: "Promo Display",       active: 70, idle: 30 },
  { zone: "Checkout Counter",    active: 91, idle: 9 },
];

const STAFF_WORKLOAD = [
  { id: "Staff 01", hours: 7.2, risk: "low" },
  { id: "Staff 02", hours: 5.1, risk: "low" },
  { id: "Staff 03", hours: 8.5, risk: "medium" },
  { id: "Staff 04", hours: 4.0, risk: "low" },
  { id: "Staff 05", hours: 9.3, risk: "high" },
];

/* ═══════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════ */

function formatDate(): string {
  const d = new Date();
  return d.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/* ═══════════════════════════════════════════════════════════════
   Page
   ═══════════════════════════════════════════════════════════════ */

export default function EmployeeInfoPage() {
  return (
    <div className="bg-bg min-h-screen">
      <main className="w-full max-w-[1280px] mx-auto px-4 md:px-6 lg:px-8 py-10 md:py-16 space-y-12 md:space-y-16">
        {/* ── Page Header ── */}
        <PageHeader />

        {/* ── Section 1: Overall Staff Performance ── */}
        <OverallPerformanceSection />

        {/* ── Section 2: Interaction & Responsiveness ── */}
        <InteractionResponsivenessSection />

        {/* ── Section 3: Idle Time & Floor Coverage ── */}
        <IdleCoverageSection />

        {/* ── Section 4: Advanced Visualizations ── */}
        <AdvancedChartsSection />

        {/* ── Section 5: Additional Insights ── */}
        <InsightsSection />
      </main>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Page Header
   ═══════════════════════════════════════════════════════════════ */

function PageHeader() {
  return (
    <RetroWindow title="Employee Info - Staff Performance Today">
      <p className="font-mono text-xs text-text-muted mb-5 tracking-wide">
        {formatDate()}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatPill label="Staff on Shift" value="5" color="var(--color-accent)" />
        <StatPill label="Total Interactions" value="143" color="var(--color-accent-soft)" />
        <RetroCard className="text-center">
          <p className="font-mono text-3xl font-bold" style={{ color: "var(--color-success)" }}>
            84 / 100
          </p>
          <p className="text-xs text-text-muted mt-1">Store Score</p>
        </RetroCard>
      </div>
    </RetroWindow>
  );
}

function StatPill({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <RetroCard className="text-center">
      <p className="font-mono text-2xl font-bold" style={{ color }}>
        {value}
      </p>
      <p className="text-xs text-text-muted mt-1">{label}</p>
    </RetroCard>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 1: Overall Staff Performance
   ═══════════════════════════════════════════════════════════════ */

function OverallPerformanceSection() {
  return (
    <RetroWindow title="Overall Staff Performance">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* ── Store Performance Score Ring ── */}
        <RetroCard label="Store Performance Score" className="flex flex-col items-center justify-center py-6">
          <ScoreRing score={84} max={100} />
          <h3 className="font-heading text-sm font-bold text-text mt-4">
            Today&apos;s Store Score
          </h3>
          <p className="text-xs text-text-muted mt-1 text-center max-w-[260px]">
            Good - staff are engaging customers effectively.
          </p>
        </RetroCard>

        {/* ── Staff Leaderboard ── */}
        <RetroCard label="Staff Leaderboard">
          <div className="overflow-x-auto -mx-1">
            <table className="w-full text-xs min-w-[420px]">
              <thead>
                <tr className="bg-surface-alt border-b border-border-soft">
                  <th className="py-2 px-2 text-left font-mono uppercase text-text-muted tracking-wider">#</th>
                  <th className="py-2 px-2 text-left font-mono uppercase text-text-muted tracking-wider">Staff ID</th>
                  <th className="py-2 px-2 text-right font-mono uppercase text-text-muted tracking-wider">Approach</th>
                  <th className="py-2 px-2 text-right font-mono uppercase text-text-muted tracking-wider">Idle</th>
                  <th className="py-2 px-2 text-right font-mono uppercase text-text-muted tracking-wider">Interact.</th>
                  <th className="py-2 px-2 text-right font-mono uppercase text-text-muted tracking-wider">Total</th>
                </tr>
              </thead>
              <tbody>
                {LEADERBOARD.map((row, i) => (
                  <tr
                    key={row.id}
                    className={`border-b border-border-soft/40 ${
                      i % 2 === 0 ? "bg-surface" : "bg-bg"
                    } ${row.rank === 1 ? "border-l-3 border-l-accent-soft" : ""}`}
                  >
                    <td className="py-2 px-2 font-mono text-text-muted">{row.rank}</td>
                    <td className="py-2 px-2 font-mono text-text">{row.id}</td>
                    <td className="py-2 px-2 text-right font-mono text-text-muted">{row.approach}</td>
                    <td className="py-2 px-2 text-right font-mono text-text-muted">{row.idle}</td>
                    <td className="py-2 px-2 text-right font-mono text-text-muted">{row.interaction}</td>
                    <td className="py-2 px-2 text-right font-mono font-bold text-accent">{row.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[10px] text-text-muted mt-3 leading-relaxed">
            Scores are computed from: Approach Speed (30 pts max), Idle Time (25 pts max),
            Interaction Duration (45 pts max). Used as manager decision-support - not an
            automated verdict.
          </p>
        </RetroCard>
      </div>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Score Ring (SVG)
   ═══════════════════════════════════════════════════════════════ */

function ScoreRing({ score, max }: { score: number; max: number }) {
  const size = 160;
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = score / max;
  const dashOffset = circumference * (1 - pct);

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-border-soft)"
          strokeWidth={strokeWidth}
          strokeOpacity={0.3}
        />
        {/* Filled arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
        />
      </svg>
      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-4xl font-bold text-accent">{score}</span>
        <span className="font-mono text-sm text-text-muted">/ {max}</span>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 2: Interaction & Responsiveness
   ═══════════════════════════════════════════════════════════════ */

function InteractionResponsivenessSection() {
  return (
    <RetroWindow title="Interaction & Responsiveness">
      <div className="space-y-6">
        {/* ── Top row: 3 stat cards ── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Total Interactions */}
          <RetroCard label="Total Interactions">
            <div className="flex flex-col items-center justify-center py-4">
              <p className="font-mono text-4xl font-bold text-accent">143</p>
              <p className="text-xs text-text-muted mt-2">interactions today</p>
              <p className="text-[10px] text-text-muted mt-1">
                successful staff–customer engagements
              </p>
              <p className="text-[10px] text-success mt-2 flex items-center gap-1">
                <TrendUpIcon /> <span className="font-mono">↑ 18</span> more than yesterday
              </p>
            </div>
          </RetroCard>

          {/* Avg Interaction Duration */}
          <RetroCard label="Avg. Interaction Duration">
            <div className="flex flex-col items-center justify-center py-4">
              <p className="font-mono text-4xl font-bold text-accent">3m 27s</p>
              <p className="text-xs text-text-muted mt-2 mb-4">avg. duration per engagement</p>

              {/* Sparkline bars */}
              <div className="flex items-end gap-1.5 h-10 w-full max-w-[180px]">
                {INTERACTION_SPARKLINE_7D.map((d) => {
                  const maxVal = Math.max(...INTERACTION_SPARKLINE_7D.map((s) => s.mins));
                  const pct = (d.mins / maxVal) * 100;
                  return (
                    <div key={d.day} className="flex-1 flex flex-col items-center gap-1">
                      <div
                        className="w-full rounded-sm min-h-[4px]"
                        style={{ height: `${pct}%`, backgroundColor: "var(--color-accent-soft)" }}
                        title={`${d.day}: ${d.mins}m`}
                      />
                      <span className="text-[8px] text-text-muted leading-none">{d.day.charAt(0)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </RetroCard>

          {/* Avg Response Time */}
          <RetroCard label="Avg. Response Time">
            <div className="flex flex-col items-center justify-center py-4">
              <p className="font-mono text-4xl font-bold text-accent">1m 52s</p>
              <p className="text-xs text-text-muted mt-2">
                from customer zone entry to staff greeting
              </p>
              <p className="text-[10px] text-text-muted mt-2">
                Target: <span className="text-success font-mono">under 2 minutes</span>
              </p>
            </div>
          </RetroCard>
        </div>

        {/* ── Full-width: Responsiveness line chart ── */}
        <RetroCard label="Responsiveness Throughout the Day">
          <div className="pt-4">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={RESPONSE_TIME_HOURLY} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid
                  strokeDasharray="4 4"
                  stroke="var(--color-border-soft)"
                  strokeOpacity={0.35}
                />
                <XAxis
                  dataKey="hour"
                  tick={{ fontSize: 11, fontFamily: "var(--font-mono)", fill: "var(--color-text-muted)" }}
                  tickLine={false}
                  axisLine={{ stroke: "var(--color-border-soft)", strokeOpacity: 0.5 }}
                />
                <YAxis
                  tick={{ fontSize: 11, fontFamily: "var(--font-mono)", fill: "var(--color-text-muted)" }}
                  tickLine={false}
                  axisLine={false}
                  unit="s"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--color-surface)",
                    border: "1px solid var(--color-border-soft)",
                    borderRadius: "6px",
                    fontFamily: "var(--font-mono)",
                    fontSize: 12,
                    color: "var(--color-text)",
                  }}
                  formatter={(value) => [`${value}s`, "Response Time"]}
                />
                <ReferenceLine
                  y={120}
                  stroke="var(--color-danger)"
                  strokeDasharray="6 4"
                  label={{
                    value: "Target (2m)",
                    position: "insideTopRight",
                    fill: "var(--color-danger)",
                    fontSize: 10,
                    fontFamily: "var(--font-mono)",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="seconds"
                  stroke="var(--color-accent)"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "var(--color-accent)", strokeWidth: 0 }}
                  activeDot={{ r: 5, fill: "var(--color-accent)", stroke: "var(--color-surface)", strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </RetroCard>
      </div>
    </RetroWindow>
  );
}

function TrendUpIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-success shrink-0 inline-block"
    >
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 3: Idle Time & Floor Coverage
   ═══════════════════════════════════════════════════════════════ */

function IdleCoverageSection() {
  const maxIdle = Math.max(...STAFF_IDLE.map((s) => s.mins));

  return (
    <RetroWindow title="Idle Time & Floor Coverage">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* ── Active vs Idle Donut ── */}
        <RetroCard label="Active vs. Idle Split">
          <div className="flex flex-col items-center py-2">
            <div className="relative w-full max-w-[200px] aspect-square">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={ACTIVE_IDLE_SPLIT}
                    cx="50%"
                    cy="50%"
                    innerRadius="60%"
                    outerRadius="85%"
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                  >
                    {ACTIVE_IDLE_SPLIT.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--color-surface)",
                      border: "1px solid var(--color-border-soft)",
                      borderRadius: "6px",
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                      color: "var(--color-text)",
                    }}
                    formatter={(value) => [`${value}%`, ""]}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="font-mono text-3xl font-bold text-success">67%</span>
                <span className="text-[10px] text-text-muted">Active</span>
              </div>
            </div>
            <div className="flex gap-5 mt-3 text-xs text-text-muted">
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-success" />
                Active
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-border-soft" />
                Idle
              </span>
            </div>
            <p className="text-[10px] text-text-muted mt-2 text-center">
              across all 5 staff members, today&apos;s shift
            </p>
          </div>
        </RetroCard>

        {/* ── Idle Time per Staff ── */}
        <RetroCard label="Idle Time per Staff">
          <div className="space-y-3">
            <div className="text-center mb-4">
              <p className="font-mono text-3xl font-bold text-accent">1h 44m</p>
              <p className="text-xs text-text-muted mt-1">avg. idle per employee</p>
            </div>

            <div className="space-y-2">
              {STAFF_IDLE.map((s) => {
                const pct = (s.mins / maxIdle) * 100;
                const isWorst = s.mins === maxIdle;
                return (
                  <div key={s.id} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-mono text-text">{s.id}</span>
                      <span className={`font-mono ${isWorst ? "text-danger font-bold" : "text-text-muted"}`}>
                        {s.idle}
                      </span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-surface-alt overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: isWorst ? "var(--color-danger)" : "var(--color-danger)",
                          opacity: isWorst ? 1 : 0.35,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </RetroCard>

        {/* ── Unstaffed Zone Alerts ── */}
        <RetroCard label="Unstaffed Zone Alerts">
          <div className="space-y-3">
            <p className="text-xs text-text-muted">
              <span className="font-mono font-bold text-danger">3</span> coverage gaps today -
              totaling <span className="font-mono font-bold text-danger">1h 47m</span> of unstaffed floor time.
            </p>

            <div className="space-y-2">
              {UNSTAFFED_ALERTS.map((alert, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-2 text-xs border-l-2 border-danger pl-3 py-2 rounded-r ${
                    i % 2 === 0 ? "bg-danger/5" : "bg-surface"
                  }`}
                >
                  <span className="text-danger shrink-0 mt-0.5">⚠</span>
                  <div className="min-w-0">
                    <p className="font-mono text-text-muted">{alert.time}</p>
                    <p className="text-text truncate">{alert.zone}</p>
                    <p className="font-mono text-danger">{alert.duration}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </RetroCard>
      </div>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 4: Advanced Visualizations
   ═══════════════════════════════════════════════════════════════ */

const CHART_TOOLTIP_STYLE = {
  backgroundColor: "var(--color-surface)",
  border: "1px solid var(--color-border-soft)",
  borderRadius: "6px",
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  color: "var(--color-text)",
};

function AdvancedChartsSection() {
  return (
    <RetroWindow title="Advanced Visualizations">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* ── Dual Line: Interactions vs Idle ── */}
        <RetroCard label="Interactions vs. Idle Events (Hourly)">
          <div className="pt-4">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={HOURLY_DUAL} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid
                  strokeDasharray="4 4"
                  stroke="var(--color-border-soft)"
                  strokeOpacity={0.35}
                />
                <XAxis
                  dataKey="hour"
                  tick={{ fontSize: 10, fontFamily: "var(--font-mono)", fill: "var(--color-text-muted)" }}
                  tickLine={false}
                  axisLine={{ stroke: "var(--color-border-soft)", strokeOpacity: 0.5 }}
                />
                <YAxis
                  tick={{ fontSize: 11, fontFamily: "var(--font-mono)", fill: "var(--color-text-muted)" }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                <Legend
                  verticalAlign="top"
                  height={28}
                  iconType="plainline"
                  wrapperStyle={{ fontSize: 11, fontFamily: "var(--font-mono)" }}
                />
                <Line
                  type="monotone"
                  dataKey="interactions"
                  name="Interactions"
                  stroke="var(--color-accent)"
                  strokeWidth={2}
                  dot={{ r: 3, fill: "var(--color-accent)", strokeWidth: 0 }}
                  activeDot={{ r: 5, fill: "var(--color-accent)", stroke: "var(--color-surface)", strokeWidth: 2 }}
                />
                <Line
                  type="monotone"
                  dataKey="idle"
                  name="Idle Events"
                  stroke="var(--color-danger)"
                  strokeWidth={2}
                  strokeDasharray="5 3"
                  dot={{ r: 3, fill: "var(--color-danger)", strokeWidth: 0 }}
                  activeDot={{ r: 5, fill: "var(--color-danger)", stroke: "var(--color-surface)", strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
            <p className="text-[10px] text-text-muted mt-2 text-center">
              Notice the inverse correlation - interactions dip when idle events rise during
              the midday lull (12 PM – 2 PM).
            </p>
          </div>
        </RetroCard>

        {/* ── Zone-by-Zone Horizontal Bars ── */}
        <RetroCard label="Zone Activity Breakdown">
          <div className="pt-4">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={ZONE_BREAKDOWN}
                layout="vertical"
                margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
              >
                <CartesianGrid
                  strokeDasharray="4 4"
                  stroke="var(--color-border-soft)"
                  strokeOpacity={0.35}
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  domain={[0, 100]}
                  tick={{ fontSize: 11, fontFamily: "var(--font-mono)", fill: "var(--color-text-muted)" }}
                  tickLine={false}
                  axisLine={{ stroke: "var(--color-border-soft)", strokeOpacity: 0.5 }}
                  unit="%"
                />
                <YAxis
                  type="category"
                  dataKey="zone"
                  tick={{ fontSize: 10, fontFamily: "var(--font-mono)", fill: "var(--color-text-muted)" }}
                  tickLine={false}
                  axisLine={false}
                  width={110}
                />
                <Tooltip
                  contentStyle={CHART_TOOLTIP_STYLE}
                  formatter={(value) => [`${value}%`, ""]}
                />
                <Legend
                  verticalAlign="top"
                  height={28}
                  iconType="square"
                  wrapperStyle={{ fontSize: 11, fontFamily: "var(--font-mono)" }}
                />
                <Bar dataKey="active" name="Active %" fill="var(--color-success)" radius={[0, 3, 3, 0]} barSize={10} />
                <Bar dataKey="idle" name="Idle %" fill="var(--color-border-soft)" radius={[0, 3, 3, 0]} barSize={10} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </RetroCard>
      </div>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 5: Additional Insights
   ═══════════════════════════════════════════════════════════════ */

function InsightsSection() {
  const maxHours = Math.max(...STAFF_WORKLOAD.map((s) => s.hours));

  return (
    <RetroWindow title="Additional Insights">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* ── Best Performing Hour ── */}
        <RetroCard label="Best Performing Hour">
          <div className="flex flex-col items-center justify-center py-6 space-y-3">
            <ClockIcon />
            <p className="font-mono text-2xl font-bold text-success">10:00 AM – 11:00 AM</p>
            <div className="text-center space-y-1">
              <p className="text-xs text-text-muted">
                Highest interaction count (<span className="font-mono text-accent">19</span>) with the lowest idle
                events (<span className="font-mono text-success">1</span>).
              </p>
              <p className="text-[10px] text-text-muted">
                Staff were most engaged during the late-morning window.
              </p>
            </div>
          </div>
        </RetroCard>

        {/* ── Workload & Burnout Risk ── */}
        <RetroCard label="Workload Distribution">
          <div className="space-y-4 py-2">
            <p className="text-xs text-text-muted">
              Active hours per staff member - prolonged high activity may signal burnout risk.
            </p>

            <div className="space-y-3">
              {STAFF_WORKLOAD.map((s) => {
                const pct = (s.hours / maxHours) * 100;
                const riskColor =
                  s.risk === "high"
                    ? "var(--color-danger)"
                    : s.risk === "medium"
                      ? "var(--color-accent-soft)"
                      : "var(--color-success)";
                const riskLabel =
                  s.risk === "high" ? "High" : s.risk === "medium" ? "Moderate" : "Normal";

                return (
                  <div key={s.id} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-mono text-text">{s.id}</span>
                      <span className="flex items-center gap-2">
                        <span className="font-mono text-text-muted">{s.hours}h</span>
                        <span
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                          style={{
                            color: riskColor,
                            backgroundColor: `color-mix(in srgb, ${riskColor} 12%, transparent)`,
                          }}
                        >
                          {riskLabel}
                        </span>
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-surface-alt overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: riskColor,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <p className="text-[10px] text-text-muted mt-2 leading-relaxed">
              Workload flags are decision-support signals - consider rotation adjustments for
              staff flagged <span className="text-danger font-mono">High</span>.
            </p>
          </div>
        </RetroCard>
      </div>
    </RetroWindow>
  );
}

function ClockIcon() {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--color-success)"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}