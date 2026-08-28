"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts";
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

        {/* ── Section 2: Live Zone Occupancy ── */}
        <LiveOccupancySection />

        {/* ── Section 3: Bottleneck & Crowd Density Alerts ── */}
        <BottleneckAlertsSection />

        {/* ── Section 4: Zone Conversion Rate ── */}
        <ConversionRateSection />

        {/* ── Section 5: Zone Popularity Ranking ── */}
        <PopularityRankingSection />
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
   Section 2: Live Zone Occupancy
   ═══════════════════════════════════════════════════════════════ */

function LiveOccupancySection() {
  return (
    <RetroWindow title="Live Zone Occupancy">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {ZONE_OCCUPANCY.map((z) => (
          <OccupancyCard key={z.zone} zone={z} />
        ))}
      </div>
    </RetroWindow>
  );
}

function OccupancyCard({
  zone,
}: {
  zone: (typeof ZONE_OCCUPANCY)[number];
}) {
  const statusVariant =
    zone.status === "Crowded"
      ? "danger"
      : zone.status === "Busy"
        ? "accent"
        : "success";

  /** Capacity bar color tiers: success <60%, accent-soft 60-85%, danger 85%+ */
  const barColor =
    zone.capacityPct >= 85
      ? "var(--color-danger)"
      : zone.capacityPct >= 60
        ? "var(--color-accent-soft)"
        : "var(--color-success)";

  return (
    <RetroCard label={zone.zone}>
      <div className="flex items-baseline justify-between mb-3">
        <span className="font-mono text-3xl font-bold text-text">
          {zone.count}
        </span>
        <Badge variant={statusVariant}>{zone.status}</Badge>
      </div>

      {/* Capacity bar */}
      <div className="space-y-1.5">
        <div className="h-2.5 w-full rounded-full bg-surface-alt overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${zone.capacityPct}%`, backgroundColor: barColor }}
          />
        </div>
        <p className="text-[11px] font-mono text-text-muted text-right">
          {zone.capacityPct}% capacity
        </p>
      </div>
    </RetroCard>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 3: Bottleneck & Crowd Density Alerts
   ═══════════════════════════════════════════════════════════════ */

function BottleneckAlertsSection() {
  const hasAlerts = ALERTS.length > 0;

  return (
    <RetroWindow title="Bottleneck & Crowd Density Alerts">
      {hasAlerts ? (
        <div className="space-y-4">
          {ALERTS.map((alert, idx) => (
            <AlertCard key={idx} alert={alert} />
          ))}
        </div>
      ) : (
        /* Empty state */
        <div className="flex items-center gap-3 py-6 px-4 rounded-lg bg-surface">
          <span className="text-xl">✅</span>
          <p className="font-body text-sm text-success font-medium">
            No active bottlenecks — floor traffic is flowing normally.
          </p>
        </div>
      )}
    </RetroWindow>
  );
}

function AlertCard({
  alert,
}: {
  alert: (typeof ALERTS)[number];
}) {
  const isHigh = alert.severity === "High";
  const borderColor = isHigh ? "var(--color-danger)" : "var(--color-accent-soft)";
  const severityVariant = isHigh ? "danger" : "accent";

  return (
    <div
      className="rounded-lg border border-border-soft bg-surface p-4 pl-5"
      style={{ borderLeftWidth: "4px", borderLeftColor: borderColor }}
    >
      <div className="flex items-start gap-3">
        {/* Warning icon */}
        <span className="text-lg mt-0.5 shrink-0" aria-hidden="true">
          ⚠️
        </span>

        <div className="flex-1 min-w-0 space-y-2">
          {/* Headline + severity badge */}
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-heading text-sm font-semibold text-text">
              {alert.headline}
            </h3>
            <Badge variant={severityVariant}>{alert.severity}</Badge>
          </div>

          {/* Description */}
          <p className="text-xs text-text-muted leading-relaxed">
            {alert.description}
          </p>

          {/* Duration tag */}
          <p className="font-mono text-[11px] text-text-muted">
            Duration: <span className="font-semibold text-text">{alert.duration}</span>
          </p>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 4: Zone Conversion Rate
   ═══════════════════════════════════════════════════════════════ */

/** Recharts tooltip matched to the design system */
function ConversionTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border-soft bg-surface px-3 py-2 shadow-lg text-xs">
      <p className="font-heading font-semibold text-text mb-1">{label}</p>
      {payload.map((entry: any) => (
        <p key={entry.name} className="font-mono text-text-muted">
          <span
            className="inline-block w-2.5 h-2.5 rounded-sm mr-1.5 align-middle"
            style={{ backgroundColor: entry.color }}
          />
          {entry.name}: {entry.value}
        </p>
      ))}
    </div>
  );
}

function ConversionRateSection() {
  return (
    <RetroWindow title="Zone Conversion Rate">
      <div className="space-y-8">
        {/* Horizontal grouped bar chart */}
        <div>
          <p className="text-xs text-text-muted mb-4 font-body">
            Walked Past vs. Stopped — per zone (today)
          </p>
          <div className="w-full h-[280px] md:h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={CONVERSION_DATA}
                layout="vertical"
                margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
              >
                <XAxis type="number" tick={{ fontSize: 11, fill: "#6B5642" }} />
                <YAxis
                  type="category"
                  dataKey="zone"
                  width={140}
                  tick={{ fontSize: 11, fill: "#2E1F14" }}
                />
                <Tooltip content={<ConversionTooltip />} />
                <Legend
                  iconSize={10}
                  wrapperStyle={{ fontSize: 11, fontFamily: "var(--font-mono)" }}
                />
                <Bar dataKey="walkedPast" name="Walked Past" fill="#8B6A4A" radius={[0, 4, 4, 0]} />
                <Bar dataKey="stopped" name="Stopped" fill="#C1652F" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Conversion table — sorted by pct descending */}
        <div>
          <h3 className="font-heading text-sm font-semibold text-text mb-3">
            Conversion Table
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border-soft text-left text-text-muted font-mono">
                  <th className="py-2 pr-3 font-medium">Zone</th>
                  <th className="py-2 pr-3 font-medium text-right">Walked Past</th>
                  <th className="py-2 pr-3 font-medium text-right">Stopped</th>
                  <th className="py-2 font-medium text-right">Conversion %</th>
                </tr>
              </thead>
              <tbody>
                {CONVERSION_TABLE.map((row) => {
                  const highlight =
                    row.pct >= 60
                      ? "border-l-4 border-l-success"
                      : row.pct < 30
                        ? "border-l-4 border-l-danger"
                        : "";
                  return (
                    <tr
                      key={row.zone}
                      className={`border-b border-border-soft/50 ${highlight}`}
                    >
                      <td className="py-2.5 pr-3 font-body text-text pl-2">
                        {row.zone}
                      </td>
                      <td className="py-2.5 pr-3 font-mono text-text-muted text-right">
                        {row.walkedPast}
                      </td>
                      <td className="py-2.5 pr-3 font-mono text-text-muted text-right">
                        {row.stopped}
                      </td>
                      <td className="py-2.5 font-mono font-semibold text-right text-text">
                        {row.pct}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 5: Zone Popularity Ranking
   ═══════════════════════════════════════════════════════════════ */

function PopularityRankingSection() {
  const maxVisits = Math.max(...POPULARITY_RANKING.map((z) => z.visits));

  return (
    <RetroWindow title="Zone Popularity Ranking">
      <div className="space-y-3">
        {POPULARITY_RANKING.map((z) => (
          <div
            key={z.rank}
            className="flex items-center gap-3 rounded-lg border border-border-soft/50 bg-surface px-4 py-3"
          >
            {/* Rank badge */}
            <Badge
              variant={z.rank <= 3 ? "accent" : "neutral"}
            >
              #{z.rank}
            </Badge>

            {/* Zone name + note */}
            <div className="flex-1 min-w-0">
              <p className="font-heading text-sm font-semibold text-text truncate">
                {z.zone}
              </p>
              {z.note && (
                <p className="text-[10px] text-text-muted italic mt-0.5">
                  {z.note}
                </p>
              )}
            </div>

            {/* Visit bar + count */}
            <div className="hidden sm:flex items-center gap-3 w-[180px]">
              <div className="flex-1 h-2 rounded-full bg-surface-alt overflow-hidden">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${(z.visits / maxVisits) * 100}%` }}
                />
              </div>
              <span className="font-mono text-xs text-text-muted w-10 text-right">
                {z.visits}
              </span>
            </div>

            {/* Mobile: just the count */}
            <span className="sm:hidden font-mono text-xs text-text-muted">
              {z.visits}
            </span>
          </div>
        ))}
      </div>
    </RetroWindow>
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
