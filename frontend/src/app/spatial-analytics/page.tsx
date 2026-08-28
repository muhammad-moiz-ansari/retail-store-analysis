"use client";

import React from "react";
import { RetroWindow, RetroCard, Badge } from "@/components/ui";

/* ═══════════════════════════════════════════════════════════════
   Mock data
   ═══════════════════════════════════════════════════════════════ */

const HEATMAP_ZONES = [
  { id: "entrance",  name: "Entrance Lobby",       heat: 20, count: 4,  avgStay: "1.2 min" },
  { id: "aisle1",    name: "Aisle 1 — Snacks",     heat: 55, count: 9,  avgStay: "4.8 min" },
  { id: "aisle2",    name: "Aisle 2 — Beverages",  heat: 40, count: 6,  avgStay: "3.5 min" },
  { id: "aisle3",    name: "Aisle 3 — Household",  heat: 15, count: 2,  avgStay: "2.1 min" },
  { id: "promo",     name: "Promo Display",         heat: 70, count: 8,  avgStay: "6.3 min" },
  { id: "checkout",  name: "Checkout Counter",      heat: 95, count: 11, avgStay: "3.9 min" },
];

const ZONE_OCCUPANCY = [
  { zone: "Entrance Lobby",       count: 4,  capacityPct: 30,  status: "Normal" as const },
  { zone: "Aisle 1 — Snacks",     count: 9,  capacityPct: 65,  status: "Busy" as const },
  { zone: "Aisle 2 — Beverages",  count: 6,  capacityPct: 45,  status: "Normal" as const },
  { zone: "Aisle 3 — Household",  count: 2,  capacityPct: 15,  status: "Normal" as const },
  { zone: "Promo Display",         count: 8,  capacityPct: 80,  status: "Busy" as const },
  { zone: "Checkout Counter",      count: 11, capacityPct: 95,  status: "Crowded" as const },
];

const ALERTS = [
  {
    severity: "High" as const,
    headline: "Checkout congestion spilling into Aisle 3",
    description:
      "Checkout queue has extended into Aisle 3 — Household, blocking normal aisle traffic.",
    duration: "12 min",
  },
  {
    severity: "Moderate" as const,
    headline: "Promo Display approaching capacity",
    description:
      "Promo Display is at 80% of typical capacity and trending upward over the last 15 minutes.",
    duration: "8 min",
  },
];

const CONVERSION_DATA = [
  { zone: "Aisle 1 — Snacks",    walkedPast: 180, stopped: 97,  pct: 54 },
  { zone: "Aisle 2 — Beverages", walkedPast: 150, stopped: 62,  pct: 41 },
  { zone: "Aisle 3 — Household", walkedPast: 90,  stopped: 21,  pct: 23 },
  { zone: "Promo Display",        walkedPast: 210, stopped: 148, pct: 70 },
  { zone: "Checkout Counter",     walkedPast: 140, stopped: 140, pct: 100 },
];

const CONVERSION_TABLE = [...CONVERSION_DATA].sort((a, b) => b.pct - a.pct);

const POPULARITY_RANKING = [
  { rank: 1, zone: "Checkout Counter",      visits: 312, note: "" },
  { rank: 2, zone: "Promo Display",          visits: 210, note: "" },
  { rank: 3, zone: "Aisle 1 — Snacks",      visits: 180, note: "" },
  { rank: 4, zone: "Aisle 2 — Beverages",   visits: 150, note: "" },
  { rank: 5, zone: "Aisle 3 — Household",   visits: 90,  note: "" },
  { rank: 6, zone: "Entrance Lobby",         visits: 64,  note: "pass-through only, not a stop zone" },
];

/* ═══════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════ */

function formatLiveTime(): string {
  const d = new Date();
  return d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

/**
 * Interpolate between colors based on a 0-100 heat value.
 * 0 = surface-alt (#E4D4B0), 50 = accent-soft (#E8B84B), 100 = danger (#B5432E)
 */
function heatColor(heat: number): string {
  const cold = { r: 228, g: 212, b: 176 };  // --color-surface-alt
  const mid  = { r: 232, g: 184, b: 75 };   // --color-accent-soft
  const hot  = { r: 181, g: 67,  b: 46 };   // --color-danger

  let r: number, g: number, b: number;
  if (heat <= 50) {
    const t = heat / 50;
    r = Math.round(cold.r + (mid.r - cold.r) * t);
    g = Math.round(cold.g + (mid.g - cold.g) * t);
    b = Math.round(cold.b + (mid.b - cold.b) * t);
  } else {
    const t = (heat - 50) / 50;
    r = Math.round(mid.r + (hot.r - mid.r) * t);
    g = Math.round(mid.g + (hot.g - mid.g) * t);
    b = Math.round(mid.b + (hot.b - mid.b) * t);
  }
  return `rgb(${r}, ${g}, ${b})`;
}

/** Returns white or dark text depending on background luminance */
function contrastText(heat: number): string {
  return heat > 65 ? "#F7EFDD" : "#2E1F14";
}

/* ═══════════════════════════════════════════════════════════════
   Page
   ═══════════════════════════════════════════════════════════════ */

export default function SpatialAnalyticsPage() {
  return (
    <div className="bg-bg min-h-screen">
      <PulseStyle />
      <main className="w-full max-w-[1280px] mx-auto px-4 md:px-6 lg:px-8 py-10 md:py-16 space-y-12 md:space-y-16">
        {/* ── Page Header ── */}
        <PageHeader />

        {/* ── Section 1: Interactive Heatmap ── */}
        <HeatmapSection />
      </main>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Page Header
   ═══════════════════════════════════════════════════════════════ */

function PageHeader() {
  return (
    <RetroWindow title="Spatial Analytics — Live Store Map">
      <div className="flex items-center gap-2 mb-5">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inset-0 rounded-full bg-success animate-[pulse-dot_2s_ease-in-out_infinite]" />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-success" />
        </span>
        <p className="font-mono text-xs text-text-muted tracking-wide">
          Live · as of {formatLiveTime()}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <RetroCard className="text-center">
          <p className="font-mono text-2xl font-bold text-accent">34</p>
          <p className="text-xs text-text-muted mt-1">Total In Store</p>
        </RetroCard>

        <RetroCard className="text-center">
          <p className="font-mono text-lg font-bold text-danger">Checkout Counter</p>
          <p className="text-xs text-text-muted mt-1">Busiest Zone</p>
        </RetroCard>

        <RetroCard className="text-center">
          <p className="font-mono text-2xl font-bold text-danger">2</p>
          <p className="text-xs text-text-muted mt-1">Active Alerts</p>
        </RetroCard>
      </div>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 1: Interactive Heatmap
   ═══════════════════════════════════════════════════════════════ */

function HeatmapSection() {
  return (
    <RetroWindow title="Store Heatmap">
      <div className="space-y-5">
        {/* Heatmap grid — 3 cols on md+, 2 cols on small */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {/* Row 1: Entrance Lobby spans full width */}
          <HeatmapCell zone={HEATMAP_ZONES[0]} className="col-span-2 md:col-span-3 min-h-[80px]" />

          {/* Row 2: 3 aisles */}
          <HeatmapCell zone={HEATMAP_ZONES[1]} className="min-h-[120px] md:min-h-[160px]" />
          <HeatmapCell zone={HEATMAP_ZONES[2]} className="min-h-[120px] md:min-h-[160px]" />
          <HeatmapCell zone={HEATMAP_ZONES[3]} className="col-span-2 md:col-span-1 min-h-[120px] md:min-h-[160px]" />

          {/* Row 3: Promo Display */}
          <HeatmapCell zone={HEATMAP_ZONES[4]} className="col-span-2 md:col-span-2 min-h-[100px] md:min-h-[120px]" />

          {/* Row 3 right / Row 4: Checkout Counter */}
          <HeatmapCell zone={HEATMAP_ZONES[5]} className="col-span-2 md:col-span-1 min-h-[100px] md:min-h-[120px]" />
        </div>

        {/* ── Gradient legend ── */}
        <div className="flex flex-col items-center gap-1.5 pt-2">
          <div
            className="w-full max-w-[320px] h-3 rounded-full"
            style={{
              background: `linear-gradient(to right, var(--color-surface-alt), var(--color-accent-soft), var(--color-danger))`,
            }}
          />
          <div className="flex justify-between w-full max-w-[320px] text-[10px] font-mono text-text-muted">
            <span>Quiet</span>
            <span>Busy</span>
            <span>Crowded</span>
          </div>
        </div>
      </div>
    </RetroWindow>
  );
}

function HeatmapCell({
  zone,
  className = "",
}: {
  zone: (typeof HEATMAP_ZONES)[number];
  className?: string;
}) {
  const bg = heatColor(zone.heat);
  const fg = contrastText(zone.heat);

  return (
    <div
      className={`group relative rounded-lg border border-border-soft/50 p-3 flex flex-col justify-between transition-all duration-200 cursor-default hover:-translate-y-0.5 hover:shadow-lg ${className}`}
      style={{ backgroundColor: bg }}
    >
      {/* Zone name */}
      <span
        className="text-[11px] font-heading font-semibold leading-tight"
        style={{ color: fg }}
      >
        {zone.name}
      </span>

      {/* Occupancy count */}
      <span
        className="font-mono text-3xl md:text-4xl font-bold self-center"
        style={{ color: fg }}
      >
        {zone.count}
      </span>

      {/* Hover tooltip */}
      <div className="absolute z-20 bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 rounded-lg border border-border-soft bg-surface text-xs shadow-lg opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-150 whitespace-nowrap">
        <p className="font-heading font-semibold text-text">{zone.name}</p>
        <p className="font-mono text-text-muted">
          {zone.count} people · {zone.avgStay} avg stay
        </p>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   CSS keyframes — injected via a style tag for the pulse animation
   ═══════════════════════════════════════════════════════════════ */

function PulseStyle() {
  return (
    <style>{`
      @keyframes pulse-dot {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
      }
    `}</style>
  );
}
