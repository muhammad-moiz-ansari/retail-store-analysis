"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { ManagerPage, ManagerHeader, ManagerPanel, ManagerCard, ManagerTable } from "@/components/ui/ManagerLayout";
import { Badge } from "@/components/ui";

/* ═══════════════════════════════════════════════════════════════
   Mock data
   ═══════════════════════════════════════════════════════════════ */

const HEATMAP_ZONES = [
  { id: "entrance",  name: "Entrance Lobby",       heat: 20, count: 4,  avgStay: "1.2 min" },
  { id: "aisle1",    name: "Aisle 1 - Snacks",     heat: 55, count: 9,  avgStay: "4.8 min" },
  { id: "aisle2",    name: "Aisle 2 - Beverages",  heat: 40, count: 6,  avgStay: "3.5 min" },
  { id: "aisle3",    name: "Aisle 3 - Household",  heat: 15, count: 2,  avgStay: "2.1 min" },
  { id: "promo",     name: "Promo Display",         heat: 70, count: 8,  avgStay: "6.3 min" },
  { id: "checkout",  name: "Checkout Counter",      heat: 95, count: 11, avgStay: "3.9 min" },
];

const ZONE_OCCUPANCY = [
  { zone: "Entrance Lobby",       count: 4,  capacityPct: 30,  status: "Normal" as const },
  { zone: "Aisle 1 - Snacks",     count: 9,  capacityPct: 65,  status: "Busy" as const },
  { zone: "Aisle 2 - Beverages",  count: 6,  capacityPct: 45,  status: "Normal" as const },
  { zone: "Aisle 3 - Household",  count: 2,  capacityPct: 15,  status: "Normal" as const },
  { zone: "Promo Display",         count: 8,  capacityPct: 80,  status: "Busy" as const },
  { zone: "Checkout Counter",      count: 11, capacityPct: 95,  status: "Crowded" as const },
];

const ALERTS = [
  {
    severity: "High" as const,
    headline: "Checkout congestion spilling into Aisle 3",
    description:
      "Checkout queue has extended into Aisle 3 - Household, blocking normal aisle traffic.",
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
  { zone: "Aisle 1 - Snacks",    walkedPast: 180, stopped: 97,  pct: 54 },
  { zone: "Aisle 2 - Beverages", walkedPast: 150, stopped: 62,  pct: 41 },
  { zone: "Aisle 3 - Household", walkedPast: 90,  stopped: 21,  pct: 23 },
  { zone: "Promo Display",        walkedPast: 210, stopped: 148, pct: 70 },
  { zone: "Checkout Counter",     walkedPast: 140, stopped: 140, pct: 100 },
];

const CONVERSION_TABLE = [...CONVERSION_DATA].sort((a, b) => b.pct - a.pct);

const POPULARITY_RANKING = [
  { rank: 1, zone: "Checkout Counter",      visits: 312, note: "" },
  { rank: 2, zone: "Promo Display",          visits: 210, note: "" },
  { rank: 3, zone: "Aisle 1 - Snacks",      visits: 180, note: "" },
  { rank: 4, zone: "Aisle 2 - Beverages",   visits: 150, note: "" },
  { rank: 5, zone: "Aisle 3 - Household",   visits: 90,  note: "" },
  { rank: 6, zone: "Entrance Lobby",         visits: 64,  note: "pass-through only, not a stop zone" },
];

/* ═══════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════ */

function heatColor(heat: number) {
  if (heat <= 45) {
    return `color-mix(in srgb, var(--color-heat-mid) ${heat / 45 * 100}%, var(--color-heat-low))`;
  }
  return `color-mix(in srgb, var(--color-heat-high) ${(heat - 45) / 55 * 100}%, var(--color-heat-mid))`;
}

/* ═══════════════════════════════════════════════════════════════
   Page
   ═══════════════════════════════════════════════════════════════ */

export default function SpatialAnalyticsPage() {
  return (
    <ManagerPage>
      {/* ── Page Header ── */}
      <ManagerHeader title="Spatial analytics">
        <p>Sample data · Illustrative zone counts and activity. Live role occupancy requires a registered map and camera observations.</p>
      </ManagerHeader>
      <SummaryMetrics />

      {/* ── Section 1: Interactive Heatmap ── */}
      <HeatmapSection />

      {/* ── Section 2: Sample zone occupancy ── */}
      <SampleOccupancySection />

      {/* ── Section 3: Bottleneck & Crowd Density Alerts ── */}
      <BottleneckAlertsSection />

      {/* ── Section 4: Zone Conversion Rate ── */}
      <ConversionRateSection />

      {/* ── Section 5: Zone Popularity Ranking ── */}
      <PopularityRankingSection />
    </ManagerPage>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Page Header
   ═══════════════════════════════════════════════════════════════ */

function SummaryMetrics() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <ManagerCard className="text-center">
        <p className="font-heading text-3xl font-bold tabular-nums tracking-tight text-accent">34</p>
        <p className="text-xs text-text-muted mt-1">Total In Store</p>
      </ManagerCard>

      <ManagerCard className="text-center">
        <p className="font-mono text-lg font-bold text-danger">Checkout Counter</p>
        <p className="text-xs text-text-muted mt-1">Busiest Zone</p>
      </ManagerCard>

      <ManagerCard className="text-center">
        <p className="font-heading text-3xl font-bold tabular-nums tracking-tight text-danger">2</p>
        <p className="text-xs text-text-muted mt-1">Active Alerts</p>
      </ManagerCard>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 1: Interactive Heatmap
   ═══════════════════════════════════════════════════════════════ */

function HeatmapSection() {
  return (
    <ManagerPanel title="Sample store heatmap">
      <div className="space-y-5">
        <p className="text-sm text-text-muted">Color shows the sample activity score from 0 to 100. Each tile lists the example headcount and average stay.</p>
        {/* Heatmap grid - 3 cols on md+, 2 cols on small */}
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
              background: "linear-gradient(to right, var(--color-heat-low), var(--color-heat-mid) 45%, var(--color-heat-high))",
            }}
          />
          <div className="flex justify-between w-full max-w-[320px] text-[10px] font-mono text-text-muted">
            <span>0 · Low</span>
            <span>50</span>
            <span>100 · High</span>
          </div>
        </div>
      </div>
    </ManagerPanel>
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

  return (
    <div
      className={`flex min-w-0 flex-col justify-between gap-2 rounded-lg border border-border-soft p-2 sm:p-3 ${className}`}
      style={{ backgroundColor: bg, color: zone.heat >= 50 ? "var(--color-on-heat-high)" : "var(--color-on-heat-low)" }}
    >
      <h3 className="text-sm font-semibold leading-tight">{zone.name}</h3>
      <p><strong className="font-heading text-2xl tabular-nums">{zone.count}</strong> <span className="text-xs">people</span></p>
      <p className="text-xs">{zone.avgStay} avg stay · Score {zone.heat}</p>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 2: Sample zone occupancy
   ═══════════════════════════════════════════════════════════════ */

function SampleOccupancySection() {
  return (
    <ManagerPanel title="Sample zone occupancy">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {ZONE_OCCUPANCY.map((z) => (
          <OccupancyCard key={z.zone} zone={z} />
        ))}
      </div>
    </ManagerPanel>
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
    <ManagerCard label={zone.zone}>
      <div className="flex items-baseline justify-between mb-3">
        <span className="font-heading text-3xl font-bold tabular-nums tracking-tight text-text">
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
    </ManagerCard>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 3: Bottleneck & Crowd Density Alerts
   ═══════════════════════════════════════════════════════════════ */

function BottleneckAlertsSection() {
  const hasAlerts = ALERTS.length > 0;

  return (
    <ManagerPanel title="Bottleneck & Crowd Density Alerts">
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
            No active bottlenecks - floor traffic is flowing normally.
          </p>
        </div>
      )}
    </ManagerPanel>
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

type ConversionTooltipProps = {
  active?: boolean;
  label?: string;
  payload?: Array<{
    name: string;
    value: number | string;
    color: string;
  }>;
};

/** Recharts tooltip matched to the design system */
function ConversionTooltip({ active, payload, label }: ConversionTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border-soft bg-surface px-3 py-2 shadow-lg text-xs">
      <p className="font-heading font-semibold text-text mb-1">{label}</p>
      {payload.map((entry) => (
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
    <ManagerPanel title="Zone conversion rate">
      <div className="space-y-8">
        {/* Horizontal grouped bar chart */}
        <div>
          <p className="text-xs text-text-muted mb-4 font-body">
            People who walked past or stopped in each zone in the sample period
          </p>
          <div className="w-full h-[280px] md:h-[320px]">
            <ResponsiveContainer minWidth={0} width="100%" height="100%">
              <BarChart accessibilityLayer
                data={CONVERSION_DATA}
                layout="vertical"
                margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
              >
                <XAxis type="number" tick={{ fontSize: 11, fill: "var(--color-text-muted)" }} />
                <YAxis
                  type="category"
                  dataKey="zone"
                  width={140}
                  tick={{ fontSize: 11, fill: "var(--color-text)" }}
                />
                <Tooltip content={<ConversionTooltip />} />
                <Legend
                  iconSize={10}
                  wrapperStyle={{ fontSize: 11, fontFamily: "var(--font-jetbrains-mono)" }}
                />
                <Bar isAnimationActive={false} dataKey="walkedPast" name="Walked past" fill="var(--color-accent-soft)" radius={[0, 4, 4, 0]} />
                <Bar isAnimationActive={false} dataKey="stopped" name="Stopped" fill="var(--color-coral)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Conversion table - sorted by pct descending */}
        <div>
          <h3 className="font-heading text-sm font-semibold text-text mb-3">
            Conversion Table
          </h3>
          <ManagerTable label="Zone stopping and pass-through counts">
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
          </ManagerTable>
        </div>
      </div>
    </ManagerPanel>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 5: Zone Popularity Ranking
   ═══════════════════════════════════════════════════════════════ */

function PopularityRankingSection() {
  const maxVisits = Math.max(...POPULARITY_RANKING.map((z) => z.visits));

  return (
    <ManagerPanel title="Zone Popularity Ranking">
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
    </ManagerPanel>
  );
}
