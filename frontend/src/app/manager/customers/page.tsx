"use client";

import React from "react";
import { ManagerChartValues, ManagerPage, ManagerHeader, ManagerPanel, ManagerCard } from "@/components/ui/ManagerLayout";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from "recharts";

/* ═══════════════════════════════════════════════════════════════
   Mock data
   ═══════════════════════════════════════════════════════════════ */

const ATTENDANCE_DATA = [
  { name: "Attended", value: 72, color: "var(--color-success)" },
  { name: "Unattended", value: 28, color: "var(--color-danger)" },
];

const INTERACTION_SPARKLINE = [
  { day: "Mon", mins: 3.2 },
  { day: "Tue", mins: 4.1 },
  { day: "Wed", mins: 3.8 },
  { day: "Thu", mins: 2.9 },
  { day: "Fri", mins: 4.5 },
  { day: "Sat", mins: 3.6 },
  { day: "Sun", mins: 3.0 },
];

const UNATTENDED_EVENTS = [
  { time: "10:14 AM", zone: "Electronics Aisle", wait: "4m 12s" },
  { time: "11:02 AM", zone: "Fitting Rooms", wait: "6m 45s" },
  { time: "11:38 AM", zone: "Checkout Queue", wait: "3m 20s" },
  { time: "12:15 PM", zone: "Electronics Aisle", wait: "5m 08s" },
  { time: "1:22 PM", zone: "Home Goods", wait: "4m 55s" },
  { time: "2:09 PM", zone: "Checkout Queue", wait: "7m 30s" },
  { time: "2:44 PM", zone: "Fitting Rooms", wait: "3m 58s" },
  { time: "3:18 PM", zone: "Grocery West", wait: "5m 22s" },
  { time: "4:05 PM", zone: "Electronics Aisle", wait: "4m 40s" },
  { time: "4:52 PM", zone: "Customer Service", wait: "6m 15s" },
  { time: "5:30 PM", zone: "Checkout Queue", wait: "3m 45s" },
  { time: "5:58 PM", zone: "Fitting Rooms", wait: "4m 10s" },
  { time: "6:14 PM", zone: "Electronics Aisle", wait: "5m 32s" },
  { time: "6:45 PM", zone: "Home Goods", wait: "3m 55s" },
  { time: "7:02 PM", zone: "Grocery West", wait: "4m 28s" },
  { time: "7:28 PM", zone: "Checkout Queue", wait: "6m 02s" },
  { time: "7:50 PM", zone: "Customer Service", wait: "5m 18s" },
];

const ZONE_DWELL = [
  { zone: "Electronics", mins: 6.2 },
  { zone: "Fitting Rooms", mins: 4.8 },
  { zone: "Grocery", mins: 3.5 },
  { zone: "Home Goods", mins: 3.1 },
  { zone: "Checkout", mins: 2.4 },
  { zone: "Customer Svc", mins: 1.9 },
];

const BEHAVIOR_DATA = [
  { name: "Browse & Leave", value: 38, color: "var(--color-accent)" },
  { name: "Purposeful Shop", value: 35, color: "var(--color-success)" },
  { name: "Quick Pickup", value: 18, color: "var(--color-accent-soft)" },
  { name: "Window Shop", value: 9, color: "var(--color-border-soft)" },
];

const TOP_PATHS = [
  { rank: 1, path: "Entrance → Electronics → Checkout", count: 42 },
  { rank: 2, path: "Entrance → Grocery → Home Goods → Checkout", count: 37 },
  { rank: 3, path: "Entrance → Fitting Rooms → Checkout", count: 29 },
  { rank: 4, path: "Entrance → Electronics → Grocery → Checkout", count: 24 },
  { rank: 5, path: "Entrance → Home Goods → Fitting Rooms → Checkout", count: 18 },
];

const HOURLY_TRAFFIC = [
  { hour: "9 AM", customers: 12 },
  { hour: "10 AM", customers: 28 },
  { hour: "11 AM", customers: 41 },
  { hour: "12 PM", customers: 37 },
  { hour: "1 PM", customers: 52 },
  { hour: "2 PM", customers: 61 },
  { hour: "3 PM", customers: 58 },
  { hour: "4 PM", customers: 43 },
  { hour: "5 PM", customers: 49 },
  { hour: "6 PM", customers: 34 },
  { hour: "7 PM", customers: 22 },
  { hour: "8 PM", customers: 14 },
];

/* ═══════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════ */

/* ═══════════════════════════════════════════════════════════════
   Page
   ═══════════════════════════════════════════════════════════════ */

export default function CustomerInfoPage() {
  return (
    <ManagerPage>
      {/* ── Page Header ── */}
      <ManagerHeader title="Customers"><p>Sample data · Customer traffic, service, and dwell for an illustrative day.</p></ManagerHeader>
      <SummaryMetrics />

      {/* ── Section 1: Traffic & Footfall ── */}
      <TrafficFootfallSection />

      {/* ── Section 2: Service Quality & Engagement ── */}
      <ServiceQualitySection />

      {/* ── Section 3: Trajectory & Spatial Behavior ── */}
      <TrajectorySection />

      {/* ── Section 4: Additional Insights ── */}
      <AdditionalInsightsSection />
    </ManagerPage>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Page Header
   ═══════════════════════════════════════════════════════════════ */

function SummaryMetrics() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <StatPill label="Customers In" value="247" color="var(--color-accent)" />
      <StatPill label="Customers Out" value="219" color="var(--color-accent)" />
      <StatPill label="Avg. Time in Store" value="14m 30s" color="var(--color-success)" />
    </div>
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
    <ManagerCard className="text-center">
      <p className="font-heading text-3xl font-bold tabular-nums tracking-tight" style={{ color }}>
        {value}
      </p>
      <p className="text-xs text-text-muted mt-1">{label}</p>
    </ManagerCard>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 1: Traffic & Footfall
   ═══════════════════════════════════════════════════════════════ */

function TrafficFootfallSection() {
  return (
    <ManagerPanel title="Traffic & Footfall">
      <div className="space-y-6">
        {/* Footfall Counter Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <ManagerCard className="text-center">
            <p className="font-heading text-3xl font-bold tabular-nums tracking-tight text-accent">247</p>
            <p className="text-xs text-text-muted mt-1">Total Customers In</p>
          </ManagerCard>

          <ManagerCard className="text-center">
            <p className="font-heading text-3xl font-bold tabular-nums tracking-tight text-accent-soft">219</p>
            <p className="text-xs text-text-muted mt-1">Total Customers Out</p>
          </ManagerCard>

          <ManagerCard className="text-center">
            <div className="flex items-center justify-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-success" />
              </span>
              <p className="font-heading text-3xl font-bold tabular-nums tracking-tight text-success">28</p>
            </div>
            <p className="text-xs text-text-muted mt-1">Currently In Store</p>
          </ManagerCard>
        </div>

        {/* Hourly Traffic Chart */}
        <ManagerCard label="Peak Crowd Density - Hourly Traffic">
          <div className="pt-4">
            <ResponsiveContainer minWidth={0} width="100%" height={260}>
              <AreaChart accessibilityLayer data={HOURLY_TRAFFIC} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="trafficGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-accent)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--color-accent)" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="4 4"
                  stroke="var(--color-border-soft)"
                  strokeOpacity={0.35}
                />
                <XAxis
                  dataKey="hour"
                  tick={{ fontSize: 11, fontFamily: "var(--font-jetbrains-mono)", fill: "var(--color-text-muted)" }}
                  tickLine={false}
                  axisLine={{ stroke: "var(--color-border-soft)", strokeOpacity: 0.5 }}
                />
                <YAxis
                  tick={{ fontSize: 11, fontFamily: "var(--font-jetbrains-mono)", fill: "var(--color-text-muted)" }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--color-surface)",
                    border: "1px solid var(--color-border-soft)",
                    borderRadius: "6px",
                    fontFamily: "var(--font-jetbrains-mono)",
                    fontSize: 12,
                    color: "var(--color-text)",
                  }}
                  labelStyle={{ color: "var(--color-text-muted)", fontWeight: 600 }}
                />
                <Area
                  isAnimationActive={false}
                  type="monotone"
                  dataKey="customers"
                  stroke="var(--color-accent)"
                  strokeWidth={2}
                  fill="url(#trafficGrad)"
                  dot={{ r: 3, fill: "var(--color-accent)", strokeWidth: 0 }}
                  activeDot={{ r: 5, fill: "var(--color-accent)", stroke: "var(--color-surface)", strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <ManagerChartValues label="Hourly customer traffic" columns={["Hour", "Customers"]}
            rows={HOURLY_TRAFFIC.map(({ hour, customers }) => [hour, customers])} />
        </ManagerCard>
      </div>
    </ManagerPanel>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 2: Service Quality & Engagement
   ═══════════════════════════════════════════════════════════════ */

function ServiceQualitySection() {
  return (
    <ManagerPanel title="Service Quality & Engagement">
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {/* ── Donut: Attended vs Unattended ── */}
        <ManagerCard label="Customer Attendance">
          <div className="flex flex-col items-center py-2">
            <div className="relative w-full max-w-[220px] aspect-square">
              <ResponsiveContainer minWidth={0} width="100%" height="100%">
                <PieChart>
                  <Pie
                    isAnimationActive={false}
                    data={ATTENDANCE_DATA}
                    cx="50%"
                    cy="50%"
                    innerRadius="60%"
                    outerRadius="85%"
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                  >
                    {ATTENDANCE_DATA.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--color-surface)",
                      border: "1px solid var(--color-border-soft)",
                      borderRadius: "6px",
                      fontFamily: "var(--font-jetbrains-mono)",
                      fontSize: 12,
                      color: "var(--color-text)",
                    }}
                    formatter={(value) => [`${value}%`, ""]}
                  />
                </PieChart>
              </ResponsiveContainer>
              {/* Center label */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="font-heading text-3xl font-bold tabular-nums tracking-tight text-success">72%</span>
                <span className="text-[10px] text-text-muted">Attended</span>
              </div>
            </div>
            <div className="flex gap-6 mt-3 text-xs text-text-muted">
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-success" />
                Attended
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-danger" />
                Unattended
              </span>
            </div>
          </div>
        </ManagerCard>

        {/* ── Avg Response Time ── */}
        <ManagerCard label="Avg. Response Time">
          <div className="flex flex-col items-center justify-center h-full py-4">
            <p className="font-mono text-4xl font-bold text-accent">1m 48s</p>
            <p className="text-xs text-text-muted mt-2 text-center">
              from zone entry to first staff contact
            </p>
            <p className="text-[10px] text-text-muted mt-1">
              Target: <span className="text-success font-mono">≤ 2m 00s</span>
            </p>
          </div>
        </ManagerCard>

        {/* ── Avg Interaction Duration ── */}
        <ManagerCard label="Avg. Interaction Duration">
          <div className="flex flex-col items-center justify-center py-4">
            <p className="font-mono text-4xl font-bold text-accent">3m 42s</p>
            <p className="text-xs text-text-muted mt-2 mb-4">last 7 days</p>

            {/* Sparkline bars */}
            <div className="flex items-end gap-1.5 h-10 w-full max-w-[180px]">
              {INTERACTION_SPARKLINE.map((d) => {
                const maxVal = Math.max(...INTERACTION_SPARKLINE.map((s) => s.mins));
                const pct = (d.mins / maxVal) * 100;
                return (
                  <div key={d.day} className="flex-1 flex flex-col items-center gap-1">
                    <div
                      className="w-full rounded-sm bg-accent/70 min-h-[4px]"
                      style={{ height: `${pct}%` }}
                      title={`${d.day}: ${d.mins}m`}
                    />
                    <span className="text-[8px] text-text-muted leading-none">{d.day.charAt(0)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </ManagerCard>

        {/* ── Unattended Events ── */}
        <ManagerCard label="Unattended Events">
          <div className="space-y-3">
            <p className="font-heading text-3xl font-bold tabular-nums tracking-tight text-danger">
              17 <span className="text-xs font-normal text-text-muted">events today</span>
            </p>

            <div className="max-h-[200px] overflow-y-auto pr-1 space-y-1.5 custom-scrollbar">
              {UNATTENDED_EVENTS.map((evt, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 text-xs border-l-2 border-danger pl-3 py-1.5 bg-danger/5 rounded-r"
                >
                  <span className="font-mono text-text-muted w-[70px] shrink-0">{evt.time}</span>
                  <span className="text-text flex-1 truncate">{evt.zone}</span>
                  <span className="font-mono text-danger shrink-0">{evt.wait}</span>
                </div>
              ))}
            </div>
          </div>
        </ManagerCard>
      </div>
    </ManagerPanel>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 3: Trajectory & Spatial Behavior
   ═══════════════════════════════════════════════════════════════ */

function TrajectorySection() {
  return (
    <ManagerPanel title="Trajectory & Spatial Behavior">
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {/* ── Avg Time in Store ── */}
        <ManagerCard label="Avg. Time in Store">
          <div className="flex flex-col items-center justify-center h-full py-4">
            <p className="font-mono text-4xl font-bold text-accent">14m 30s</p>
            <p className="text-xs text-text-muted mt-2">
              across <span className="font-mono text-text">247</span> customers today
            </p>
          </div>
        </ManagerCard>

        {/* ── Zone Dwell Horizontal Bar Chart ── */}
        <ManagerCard label="Zone Dwell Time (avg mins)">
          <div className="pt-2">
            <ResponsiveContainer minWidth={0} width="100%" height={200}>
              <BarChart accessibilityLayer
                data={ZONE_DWELL}
                layout="vertical"
                margin={{ top: 5, right: 20, left: 5, bottom: 5 }}
              >
                <CartesianGrid
                  strokeDasharray="4 4"
                  stroke="var(--color-border-soft)"
                  strokeOpacity={0.35}
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11, fontFamily: "var(--font-jetbrains-mono)", fill: "var(--color-text-muted)" }}
                  tickLine={false}
                  axisLine={false}
                  unit="m"
                />
                <YAxis
                  type="category"
                  dataKey="zone"
                  tick={{ fontSize: 11, fontFamily: "var(--font-jetbrains-mono)", fill: "var(--color-text-muted)" }}
                  tickLine={false}
                  axisLine={false}
                  width={95}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--color-surface)",
                    border: "1px solid var(--color-border-soft)",
                    borderRadius: "6px",
                    fontFamily: "var(--font-jetbrains-mono)",
                    fontSize: 12,
                    color: "var(--color-text)",
                  }}
                  formatter={(value) => [`${value} mins`, "Dwell"]}
                />
                <Bar isAnimationActive={false} dataKey="mins" fill="var(--color-accent)" radius={[0, 4, 4, 0]} barSize={16} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <ManagerChartValues label="Average zone dwell" columns={["Zone", "Average (minutes)"]}
            rows={ZONE_DWELL.map(({ zone, mins }) => [zone, mins])} />
        </ManagerCard>

        {/* ── Shopper Behavior Donut ── */}
        <ManagerCard label="Shopper Behavior">
          <div className="flex flex-col items-center py-2">
            <div className="relative w-full max-w-[220px] aspect-square">
              <ResponsiveContainer minWidth={0} width="100%" height="100%">
                <PieChart>
                  <Pie
                    isAnimationActive={false}
                    data={BEHAVIOR_DATA}
                    cx="50%"
                    cy="50%"
                    innerRadius="55%"
                    outerRadius="85%"
                    paddingAngle={2}
                    dataKey="value"
                    stroke="none"
                  >
                    {BEHAVIOR_DATA.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--color-surface)",
                      border: "1px solid var(--color-border-soft)",
                      borderRadius: "6px",
                      fontFamily: "var(--font-jetbrains-mono)",
                      fontSize: 12,
                      color: "var(--color-text)",
                    }}
                    formatter={(value) => [`${value}%`, ""]}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="font-mono text-lg font-bold text-text">Behavior</span>
                <span className="text-[10px] text-text-muted">Breakdown</span>
              </div>
            </div>
            <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 mt-3 text-xs text-text-muted">
              {BEHAVIOR_DATA.map((d) => (
                <span key={d.name} className="flex items-center gap-1.5">
                  <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
                  {d.name}
                </span>
              ))}
            </div>
          </div>
        </ManagerCard>

        {/* ── Top Customer Paths ── */}
        <ManagerCard label="Top Customer Paths">
          <div className="space-y-2">
            {TOP_PATHS.map((p) => (
              <div
                key={p.rank}
                className="flex items-center gap-3 text-xs py-1.5 border-b border-border-soft/40 last:border-0"
              >
                <span className="font-mono text-lg font-bold text-accent/40 w-6 text-right shrink-0">
                  {p.rank}
                </span>
                <span className="text-text flex-1">{p.path}</span>
                <span className="font-mono text-text-muted shrink-0">{p.count} trips</span>
              </div>
            ))}
          </div>
        </ManagerCard>
      </div>
    </ManagerPanel>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 4: Additional Insights
   ═══════════════════════════════════════════════════════════════ */

function AdditionalInsightsSection() {
  return (
    <ManagerPanel title="Additional Insights">
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {/* ── Return Visit Rate ── */}
        <ManagerCard label="Return Visit Rate">
          <div className="flex flex-col items-center justify-center py-6">
            <p className="font-mono text-5xl font-bold text-success">34%</p>
            <p className="text-xs text-text-muted mt-3 text-center">
              of today&apos;s customers have visited in the past 7 days
            </p>
            <div className="flex items-center gap-2 mt-4 text-xs">
              <TrendUpIcon />
              <span className="text-success font-mono">+4%</span>
              <span className="text-text-muted">vs last week</span>
            </div>
          </div>
        </ManagerCard>

        {/* ── Peak Service Pressure ── */}
        <ManagerCard label="Peak Service Pressure">
          <div className="flex flex-col items-center justify-center py-6">
            <p className="font-mono text-4xl font-bold text-danger">1:00 PM</p>
            <p className="text-xs text-text-muted mt-2 text-center">
              highest customer-to-staff ratio today
            </p>

            <div className="w-full max-w-[260px] mt-5 space-y-2">
              <PressureBar label="Customers" value={52} max={70} color="var(--color-accent)" />
              <PressureBar label="Staff on Floor" value={6} max={70} color="var(--color-success)" />
              <p className="text-[10px] text-text-muted text-center mt-1">
                Ratio: <span className="font-mono text-danger font-bold">8.7 : 1</span>
              </p>
            </div>
          </div>
        </ManagerCard>
      </div>
    </ManagerPanel>
  );
}

function PressureBar({
  label,
  value,
  max,
  color,
}: {
  label: string;
  value: number;
  max: number;
  color: string;
}) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px]">
        <span className="text-text-muted">{label}</span>
        <span className="font-mono text-text">{value}</span>
      </div>
      <div className="w-full h-2 rounded-full bg-surface-alt overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

function TrendUpIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-success shrink-0"
    >
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </svg>
  );
}
