"use client";

import React from "react";
import { RetroWindow, RetroCard } from "@/components/ui";
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

export default function CustomerInfoPage() {
  return (
    <div className="bg-bg min-h-screen">
      <main className="w-full max-w-[1280px] mx-auto px-4 md:px-6 lg:px-8 py-10 md:py-16 space-y-12 md:space-y-16">
        {/* ── Page Header ── */}
        <PageHeader />

        {/* ── Section 1: Traffic & Footfall ── */}
        <TrafficFootfallSection />

        {/* ── Section 2: Service Quality & Engagement ── */}
        <ServiceQualitySection />
      </main>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Page Header
   ═══════════════════════════════════════════════════════════════ */

function PageHeader() {
  return (
    <RetroWindow title="Customer Info — Today's Overview">
      <p className="font-mono text-xs text-text-muted mb-5 tracking-wide">
        {formatDate()}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatPill label="Customers In" value="247" color="var(--color-accent)" />
        <StatPill label="Customers Out" value="219" color="var(--color-accent-soft)" />
        <StatPill label="Avg. Time in Store" value="14m 30s" color="var(--color-success)" />
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
   Section 1: Traffic & Footfall
   ═══════════════════════════════════════════════════════════════ */

function TrafficFootfallSection() {
  return (
    <RetroWindow title="Traffic & Footfall">
      <div className="space-y-6">
        {/* Footfall Counter Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <RetroCard className="text-center">
            <p className="font-mono text-3xl font-bold text-accent">247</p>
            <p className="text-xs text-text-muted mt-1">Total Customers In</p>
          </RetroCard>

          <RetroCard className="text-center">
            <p className="font-mono text-3xl font-bold text-accent-soft">219</p>
            <p className="text-xs text-text-muted mt-1">Total Customers Out</p>
          </RetroCard>

          <RetroCard className="text-center">
            <div className="flex items-center justify-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-success" />
              </span>
              <p className="font-mono text-3xl font-bold text-success">28</p>
            </div>
            <p className="text-xs text-text-muted mt-1">Currently In Store</p>
          </RetroCard>
        </div>

        {/* Hourly Traffic Chart */}
        <RetroCard label="Peak Crowd Density — Hourly Traffic">
          <div className="pt-4">
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={HOURLY_TRAFFIC} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
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
                  tick={{ fontSize: 11, fontFamily: "var(--font-mono)", fill: "var(--color-text-muted)" }}
                  tickLine={false}
                  axisLine={{ stroke: "var(--color-border-soft)", strokeOpacity: 0.5 }}
                />
                <YAxis
                  tick={{ fontSize: 11, fontFamily: "var(--font-mono)", fill: "var(--color-text-muted)" }}
                  tickLine={false}
                  axisLine={false}
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
                  labelStyle={{ color: "var(--color-text-muted)", fontWeight: 600 }}
                />
                <Area
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
        </RetroCard>
      </div>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 2: Service Quality & Engagement
   ═══════════════════════════════════════════════════════════════ */

function ServiceQualitySection() {
  return (
    <RetroWindow title="Service Quality & Engagement">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* ── Donut: Attended vs Unattended ── */}
        <RetroCard label="Customer Attendance">
          <div className="flex flex-col items-center py-2">
            <div className="relative w-full max-w-[220px] aspect-square">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
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
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                      color: "var(--color-text)",
                    }}
                    formatter={(value) => [`${value}%`, ""]}
                  />
                </PieChart>
              </ResponsiveContainer>
              {/* Center label */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="font-mono text-3xl font-bold text-success">72%</span>
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
        </RetroCard>

        {/* ── Avg Response Time ── */}
        <RetroCard label="Avg. Response Time">
          <div className="flex flex-col items-center justify-center h-full py-4">
            <p className="font-mono text-4xl font-bold text-accent">1m 48s</p>
            <p className="text-xs text-text-muted mt-2 text-center">
              from zone entry to first staff contact
            </p>
            <p className="text-[10px] text-text-muted mt-1">
              Target: <span className="text-success font-mono">≤ 2m 00s</span>
            </p>
          </div>
        </RetroCard>

        {/* ── Avg Interaction Duration ── */}
        <RetroCard label="Avg. Interaction Duration">
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
        </RetroCard>

        {/* ── Unattended Events ── */}
        <RetroCard label="Unattended Events">
          <div className="space-y-3">
            <p className="font-mono text-2xl font-bold text-danger">
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
        </RetroCard>
      </div>
    </RetroWindow>
  );
}
