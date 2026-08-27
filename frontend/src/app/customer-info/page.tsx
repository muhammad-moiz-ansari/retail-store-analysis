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
} from "recharts";

/* ═══════════════════════════════════════════════════════════════
   Mock data
   ═══════════════════════════════════════════════════════════════ */

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
