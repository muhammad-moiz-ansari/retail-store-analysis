"use client";

import React, { useState } from "react";
import { RetroWindow, RetroCard, RetroButton, Badge } from "@/components/ui";
import {
  LineChart,
  Line,
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
  Legend,
  BarChart,
  Bar,
} from "recharts";

/* ═══════════════════════════════════════════════════════════════
   Mock Data
   ═══════════════════════════════════════════════════════════════ */

const DAILY_TREND = [
  { time: "9 AM", revenue: 8420, footfall: 12 },
  { time: "10 AM", revenue: 14360, footfall: 28 },
  { time: "11 AM", revenue: 19780, footfall: 41 },
  { time: "12 PM", revenue: 22140, footfall: 52 },
  { time: "1 PM", revenue: 17930, footfall: 37 },
  { time: "2 PM", revenue: 21560, footfall: 34 },
  { time: "3 PM", revenue: 16240, footfall: 22 },
  { time: "4 PM", revenue: 12890, footfall: 18 },
  { time: "5 PM", revenue: 19470, footfall: 29 },
  { time: "6 PM", revenue: 28310, footfall: 38 },
  { time: "7 PM", revenue: 14820, footfall: 21 },
  { time: "8 PM", revenue: 8400, footfall: 14 },
];

const WEEKLY_TREND = [
  { time: "Mon", revenue: 142300, footfall: 187 },
  { time: "Tue", revenue: 128760, footfall: 174 },
  { time: "Wed", revenue: 156890, footfall: 213 },
  { time: "Thu", revenue: 134210, footfall: 191 },
  { time: "Fri", revenue: 178430, footfall: 256 },
  { time: "Sat", revenue: 204580, footfall: 312 },
  { time: "Sun", revenue: 167920, footfall: 247 },
];

const MONTHLY_TREND = [
  { time: "Week 1", revenue: 432100, footfall: 1124 },
  { time: "Week 2", revenue: 487350, footfall: 1267 },
  { time: "Week 3", revenue: 512800, footfall: 1340 },
  { time: "Week 4", revenue: 478920, footfall: 1198 },
];

const YEARLY_TREND = [
  { time: "Jan", revenue: 1420300, footfall: 4210 },
  { time: "Feb", revenue: 1387600, footfall: 3980 },
  { time: "Mar", revenue: 1564200, footfall: 4560 },
  { time: "Apr", revenue: 1498700, footfall: 4320 },
  { time: "May", revenue: 1623400, footfall: 4810 },
  { time: "Jun", revenue: 1712800, footfall: 5120 },
  { time: "Jul", revenue: 1845600, footfall: 5470 },
  { time: "Aug", revenue: 1784320, footfall: 5230 },
];

const TREND_DATA: Record<string, typeof DAILY_TREND> = {
  Day: DAILY_TREND,
  Week: WEEKLY_TREND,
  Month: MONTHLY_TREND,
  Year: YEARLY_TREND,
};

const KNORR_VS_MAGGI = {
  knorr: {
    name: "Knorr Noodles",
    unitsSold: 142,
    revenue: 28400,
    avgPrice: 200,
    trend: [
      { day: "Mon", units: 18 },
      { day: "Tue", units: 22 },
      { day: "Wed", units: 16 },
      { day: "Thu", units: 24 },
      { day: "Fri", units: 20 },
      { day: "Sat", units: 26 },
      { day: "Sun", units: 16 },
    ],
  },
  maggi: {
    name: "Maggi Noodles",
    unitsSold: 168,
    revenue: 30240,
    avgPrice: 180,
    trend: [
      { day: "Mon", units: 24 },
      { day: "Tue", units: 20 },
      { day: "Wed", units: 26 },
      { day: "Thu", units: 22 },
      { day: "Fri", units: 28 },
      { day: "Sat", units: 30 },
      { day: "Sun", units: 18 },
    ],
  },
};

const AB_CHART_DATA = KNORR_VS_MAGGI.knorr.trend.map((k, i) => ({
  day: k.day,
  knorr: k.units,
  maggi: KNORR_VS_MAGGI.maggi.trend[i].units,
}));

const TOP_SELLERS = [
  { rank: 1, name: "Maggi Noodles", category: "Snacks", units: 168 },
  { rank: 2, name: "Coca-Cola 500ml", category: "Beverages", units: 154 },
  { rank: 3, name: "Knorr Noodles", category: "Snacks", units: 142 },
  { rank: 4, name: "Lay's Classic", category: "Snacks", units: 139 },
  { rank: 5, name: "Nestlé Water 1.5L", category: "Beverages", units: 121 },
];

const HIGHEST_GROSSING = [
  { rank: 1, name: "Maggi Noodles", category: "Snacks", revenue: 30240 },
  { rank: 2, name: "Knorr Noodles", category: "Snacks", revenue: 28400 },
  { rank: 3, name: "Surf Excel 1kg", category: "Household", revenue: 21840 },
  { rank: 4, name: "Nestlé Water 1.5L", category: "Beverages", revenue: 18150 },
  { rank: 5, name: "Coca-Cola 500ml", category: "Beverages", revenue: 15400 },
];

const CATEGORY_REVENUE = [
  { name: "Snacks", value: 38, color: "var(--color-accent)" },
  { name: "Beverages", value: 34, color: "var(--color-accent-soft)" },
  { name: "Household", value: 28, color: "var(--color-success)" },
];

const FUNNEL_STAGES = [
  { label: "Entered Store", value: 247, pct: 100, width: 100 },
  { label: "Engaged with Products", value: 201, pct: 81, width: 75 },
  { label: "Completed a Purchase", value: 168, pct: 68, width: 50 },
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

function fmtPKR(n: number): string {
  return `Rs. ${n.toLocaleString("en-PK")}`;
}

/* ═══════════════════════════════════════════════════════════════
   Page
   ═══════════════════════════════════════════════════════════════ */

export default function SalesTrendsPage() {
  return (
    <div className="bg-bg min-h-screen">
      <main className="w-full max-w-[1280px] mx-auto px-4 md:px-6 lg:px-8 py-10 md:py-16 space-y-12 md:space-y-16">
        {/* ── Page Header ── */}
        <PageHeader />

        {/* ── Section 1: Sales Trend Timelines ── */}
        <SalesTrendSection />

        {/* ── Section 2: A/B Product Comparison ── */}
        <ProductComparisonSection />

        {/* ── Section 3: Top Sellers vs Highest Grossing ── */}
        <LeaderboardSection />

        {/* ── Category Revenue Breakdown ── */}
        <CategoryBreakdownSection />

        {/* ── Section 4: Footfall-to-Purchase Conversion ── */}
        <ConversionFunnelSection />

        {/* ── Section 5: Additional Insights ── */}
        <AdditionalInsightsSection />
      </main>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Page Header
   ═══════════════════════════════════════════════════════════════ */

function PageHeader() {
  return (
    <RetroWindow title="Sales & Product Trends - POS Analytics">
      <p className="font-mono text-xs text-text-muted mb-5 tracking-wide">
        {formatDate()}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatPill label="Revenue" value={fmtPKR(184320)} color="var(--color-accent)" />
        <StatPill label="Transactions" value="168" color="var(--color-accent-soft)" />
        <StatPill label="Avg. Basket" value={fmtPKR(1097)} color="var(--color-success)" />
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
   Section 1: Sales Trend Timelines
   ═══════════════════════════════════════════════════════════════ */

function SalesTrendSection() {
  const [granularity, setGranularity] = useState<string>("Day");
  const data = TREND_DATA[granularity];

  return (
    <RetroWindow title="Sales Trend Timelines">
      {/* Granularity toggle */}
      <div className="flex items-center gap-2 mb-6 flex-wrap">
        {Object.keys(TREND_DATA).map((key) => (
          <RetroButton
            key={key}
            variant={granularity === key ? "primary" : "secondary"}
            className="!px-3 !py-1.5 !text-xs"
            onClick={() => setGranularity(key)}
          >
            {key}
          </RetroButton>
        ))}
      </div>

      <RetroCard label="Revenue vs Footfall">
        <div className="h-[340px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-soft)" opacity={0.4} />
              <XAxis
                dataKey="time"
                tick={{ fill: "var(--color-text-muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}
                axisLine={{ stroke: "var(--color-border-soft)" }}
                tickLine={false}
              />
              <YAxis
                yAxisId="revenue"
                tick={{ fill: "var(--color-text-muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              />
              <YAxis
                yAxisId="footfall"
                orientation="right"
                tick={{ fill: "var(--color-text-muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--color-surface)",
                  border: "1px solid var(--color-border-soft)",
                  borderRadius: 6,
                  fontFamily: "var(--font-mono)",
                  fontSize: 12,
                }}
                formatter={(value, name) => [
                  name === "revenue" ? fmtPKR(value as number) : `${value} visitors`,
                  name === "revenue" ? "Revenue" : "Footfall",
                ]}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, fontFamily: "var(--font-mono)" }}
              />
              <Line
                yAxisId="revenue"
                type="monotone"
                dataKey="revenue"
                name="Revenue"
                stroke="var(--color-accent)"
                strokeWidth={2.5}
                dot={{ r: 3, fill: "var(--color-accent)" }}
                activeDot={{ r: 5 }}
              />
              <Line
                yAxisId="footfall"
                type="monotone"
                dataKey="footfall"
                name="Footfall"
                stroke="var(--color-accent-soft)"
                strokeWidth={2}
                strokeDasharray="5 3"
                dot={{ r: 3, fill: "var(--color-accent-soft)" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="text-[10px] text-text-muted mt-3 leading-relaxed">
          Dual-axis overlay - left axis shows revenue (Rs.), right axis shows
          customer footfall count. Use the granularity toggle above to switch
          between Day / Week / Month / Year views.
        </p>
      </RetroCard>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 2: A/B Product Comparison
   ═══════════════════════════════════════════════════════════════ */

function ProductComparisonSection() {
  const k = KNORR_VS_MAGGI.knorr;
  const m = KNORR_VS_MAGGI.maggi;

  return (
    <RetroWindow title="A/B Product Comparison">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Stat cards */}
        <div className="grid grid-cols-2 gap-4">
          {/* Knorr */}
          <RetroCard label="Knorr Noodles">
            <div className="space-y-3">
              <div>
                <p className="font-mono text-lg font-bold text-accent">{k.unitsSold}</p>
                <p className="text-[10px] text-text-muted">Units Sold</p>
              </div>
              <div>
                <p className="font-mono text-lg font-bold text-accent">{fmtPKR(k.revenue)}</p>
                <p className="text-[10px] text-text-muted">Revenue</p>
              </div>
              <div>
                <p className="font-mono text-sm font-semibold text-text">{fmtPKR(k.avgPrice)}</p>
                <p className="text-[10px] text-text-muted">Avg. Price</p>
              </div>
            </div>
          </RetroCard>

          {/* Maggi */}
          <RetroCard label="Maggi Noodles">
            <div className="space-y-3">
              <div>
                <p className="font-mono text-lg font-bold text-accent-soft">{m.unitsSold}</p>
                <p className="text-[10px] text-text-muted">Units Sold</p>
              </div>
              <div>
                <p className="font-mono text-lg font-bold text-accent-soft">{fmtPKR(m.revenue)}</p>
                <p className="text-[10px] text-text-muted">Revenue</p>
              </div>
              <div>
                <p className="font-mono text-sm font-semibold text-text">{fmtPKR(m.avgPrice)}</p>
                <p className="text-[10px] text-text-muted">Avg. Price</p>
              </div>
            </div>
          </RetroCard>
        </div>

        {/* Weekly comparison chart */}
        <RetroCard label="Weekly Unit Sales">
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={AB_CHART_DATA} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-soft)" opacity={0.4} />
                <XAxis
                  dataKey="day"
                  tick={{ fill: "var(--color-text-muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}
                  axisLine={{ stroke: "var(--color-border-soft)" }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "var(--color-text-muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--color-surface)",
                    border: "1px solid var(--color-border-soft)",
                    borderRadius: 6,
                    fontFamily: "var(--font-mono)",
                    fontSize: 12,
                  }}
                  formatter={(value) => [`${value} units`]}
                />
                <Legend wrapperStyle={{ fontSize: 11, fontFamily: "var(--font-mono)" }} />
                <Bar dataKey="knorr" name="Knorr" fill="var(--color-accent)" radius={[3, 3, 0, 0]} />
                <Bar dataKey="maggi" name="Maggi" fill="var(--color-accent-soft)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </RetroCard>
      </div>

      <div className="mt-4 flex items-center gap-3 flex-wrap">
        <Badge variant="accent">Winner: Revenue</Badge>
        <span className="text-xs text-text-muted">
          Maggi leads in both units sold ({m.unitsSold} vs {k.unitsSold}) and
          revenue ({fmtPKR(m.revenue)} vs {fmtPKR(k.revenue)}), but Knorr
          commands a higher avg. price ({fmtPKR(k.avgPrice)} vs{" "}
          {fmtPKR(m.avgPrice)}).
        </span>
      </div>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 3: Top Sellers vs Highest Grossing
   ═══════════════════════════════════════════════════════════════ */

function LeaderboardSection() {
  return (
    <RetroWindow title="Top Sellers vs Highest Grossing">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Top sellers by units */}
        <RetroCard label="Most Units Sold">
          <div className="overflow-x-auto -mx-1">
            <table className="w-full text-xs min-w-[320px]">
              <thead>
                <tr className="bg-surface-alt border-b border-border-soft">
                  <th className="py-2 px-2 text-left font-mono uppercase text-text-muted tracking-wider">#</th>
                  <th className="py-2 px-2 text-left font-mono uppercase text-text-muted tracking-wider">Product</th>
                  <th className="py-2 px-2 text-left font-mono uppercase text-text-muted tracking-wider">Category</th>
                  <th className="py-2 px-2 text-right font-mono uppercase text-text-muted tracking-wider">Units</th>
                </tr>
              </thead>
              <tbody>
                {TOP_SELLERS.map((row, i) => (
                  <tr
                    key={row.name}
                    className={`border-b border-border-soft/40 ${
                      i % 2 === 0 ? "bg-surface" : "bg-bg"
                    } ${row.rank === 1 ? "border-l-3 border-l-accent-soft" : ""}`}
                  >
                    <td className="py-2 px-2 font-mono text-text-muted">{row.rank}</td>
                    <td className="py-2 px-2 font-mono text-text">{row.name}</td>
                    <td className="py-2 px-2 font-mono text-text-muted">{row.category}</td>
                    <td className="py-2 px-2 text-right font-mono font-bold text-accent">{row.units}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </RetroCard>

        {/* Highest grossing by revenue */}
        <RetroCard label="Highest Revenue">
          <div className="overflow-x-auto -mx-1">
            <table className="w-full text-xs min-w-[320px]">
              <thead>
                <tr className="bg-surface-alt border-b border-border-soft">
                  <th className="py-2 px-2 text-left font-mono uppercase text-text-muted tracking-wider">#</th>
                  <th className="py-2 px-2 text-left font-mono uppercase text-text-muted tracking-wider">Product</th>
                  <th className="py-2 px-2 text-left font-mono uppercase text-text-muted tracking-wider">Category</th>
                  <th className="py-2 px-2 text-right font-mono uppercase text-text-muted tracking-wider">Revenue</th>
                </tr>
              </thead>
              <tbody>
                {HIGHEST_GROSSING.map((row, i) => (
                  <tr
                    key={row.name}
                    className={`border-b border-border-soft/40 ${
                      i % 2 === 0 ? "bg-surface" : "bg-bg"
                    } ${row.rank === 1 ? "border-l-3 border-l-accent-soft" : ""}`}
                  >
                    <td className="py-2 px-2 font-mono text-text-muted">{row.rank}</td>
                    <td className="py-2 px-2 font-mono text-text">{row.name}</td>
                    <td className="py-2 px-2 font-mono text-text-muted">{row.category}</td>
                    <td className="py-2 px-2 text-right font-mono font-bold text-accent">{fmtPKR(row.revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </RetroCard>
      </div>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Category Revenue Breakdown (Bonus Section)
   ═══════════════════════════════════════════════════════════════ */

function CategoryBreakdownSection() {
  return (
    <RetroWindow title="Category Revenue Breakdown">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
        {/* Donut chart */}
        <RetroCard label="Revenue by Category">
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={CATEGORY_REVENUE}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={4}
                  dataKey="value"
                  stroke="none"
                >
                  {CATEGORY_REVENUE.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--color-surface)",
                    border: "1px solid var(--color-border-soft)",
                    borderRadius: 6,
                    fontFamily: "var(--font-mono)",
                    fontSize: 12,
                  }}
                  formatter={(value) => [`${value}%`]}
                />
                <Legend
                  wrapperStyle={{ fontSize: 11, fontFamily: "var(--font-mono)" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </RetroCard>

        {/* Breakdown list */}
        <RetroCard label="Share Details">
          <div className="space-y-4">
            {CATEGORY_REVENUE.map((cat) => (
              <div key={cat.name}>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-sm text-text">{cat.name}</span>
                  <span className="font-mono text-sm font-bold" style={{ color: cat.color }}>
                    {cat.value}%
                  </span>
                </div>
                <div className="w-full h-2.5 bg-surface-alt rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${cat.value}%`, backgroundColor: cat.color }}
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-text-muted mt-4 leading-relaxed">
            Revenue split across major store categories. Snacks leads at 38%,
            closely followed by Beverages at 34%.
          </p>
        </RetroCard>
      </div>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 4: Footfall-to-Purchase Conversion Funnel
   ═══════════════════════════════════════════════════════════════ */

function ConversionFunnelSection() {
  return (
    <RetroWindow title="Footfall-to-Purchase Conversion">
      <RetroCard label="Conversion Funnel">
        <div className="flex flex-col items-center gap-3 py-4">
          {FUNNEL_STAGES.map((stage, i) => (
            <div key={stage.label} className="w-full flex flex-col items-center">
              <div
                className="rounded-lg flex items-center justify-between px-5 py-3.5 transition-all duration-300"
                style={{
                  width: `${stage.width}%`,
                  minWidth: 220,
                  backgroundColor:
                    i === 0
                      ? "var(--color-accent)"
                      : i === 1
                        ? "var(--color-accent-soft)"
                        : "var(--color-success)",
                  color: i === 0 ? "var(--color-surface)" : "var(--color-text)",
                }}
              >
                <span className="font-mono text-sm font-semibold">{stage.label}</span>
                <span className="font-mono text-lg font-bold">{stage.value}</span>
              </div>
              {i < FUNNEL_STAGES.length - 1 && (
                <div className="flex items-center gap-2 my-1.5">
                  <svg width="12" height="16" viewBox="0 0 12 16" fill="none">
                    <path d="M6 0v12M2 8l4 4 4-4" stroke="var(--color-text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span className="font-mono text-[11px] text-text-muted">
                    {FUNNEL_STAGES[i + 1].pct}% of total
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
          <div className="text-center p-3 bg-surface-alt rounded-md">
            <p className="font-mono text-lg font-bold text-accent">81%</p>
            <p className="text-[10px] text-text-muted mt-0.5">Engagement Rate</p>
          </div>
          <div className="text-center p-3 bg-surface-alt rounded-md">
            <p className="font-mono text-lg font-bold text-accent-soft">84%</p>
            <p className="text-[10px] text-text-muted mt-0.5">Engaged → Purchase</p>
          </div>
          <div className="text-center p-3 bg-surface-alt rounded-md">
            <p className="font-mono text-lg font-bold text-success">68%</p>
            <p className="text-[10px] text-text-muted mt-0.5">Overall Conversion</p>
          </div>
        </div>

        <p className="text-[10px] text-text-muted mt-3 leading-relaxed">
          Of the 247 visitors who entered the store, 201 (81%) engaged with
          products and 168 (68%) completed a purchase. The 84% engagement-to-purchase
          rate indicates strong intent among browsing customers.
        </p>
      </RetroCard>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 5: Additional Insights
   ═══════════════════════════════════════════════════════════════ */

function AdditionalInsightsSection() {
  return (
    <RetroWindow title="Additional Insights">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Revenue per Visitor */}
        <RetroCard label="Revenue per Visitor">
          <div className="flex flex-col items-center py-6">
            <p className="font-mono text-4xl font-bold text-accent">{fmtPKR(746)}</p>
            <p className="text-xs text-text-muted mt-2">Average spend per visitor</p>
            <div className="mt-4 space-y-2 w-full">
              <div className="flex justify-between text-xs">
                <span className="text-text-muted">Total Revenue</span>
                <span className="font-mono text-text">{fmtPKR(184320)}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-text-muted">Total Visitors</span>
                <span className="font-mono text-text">247</span>
              </div>
              <div className="flex justify-between text-xs border-t border-border-soft pt-2">
                <span className="text-text-muted font-semibold">Revenue ÷ Visitors</span>
                <span className="font-mono font-bold text-accent">{fmtPKR(746)}</span>
              </div>
            </div>
          </div>
        </RetroCard>

        {/* Peak Mismatch */}
        <RetroCard label="Peak Mismatch Analysis">
          <div className="space-y-4 py-2">
            <div className="flex items-start gap-3 p-3 bg-surface-alt rounded-md">
              <div className="shrink-0 mt-0.5">
                <Badge variant="accent">Footfall Peak</Badge>
              </div>
              <div>
                <p className="font-mono text-sm font-bold text-text">12:00 PM</p>
                <p className="text-[10px] text-text-muted mt-0.5">
                  52 visitors - highest foot traffic recorded at noon
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 bg-surface-alt rounded-md">
              <div className="shrink-0 mt-0.5">
                <Badge variant="success">Sales Peak</Badge>
              </div>
              <div>
                <p className="font-mono text-sm font-bold text-text">6:00 PM</p>
                <p className="text-[10px] text-text-muted mt-0.5">
                  {fmtPKR(28310)} - highest hourly revenue in the evening rush
                </p>
              </div>
            </div>

            <div className="p-3 bg-danger/10 border border-danger/20 rounded-md">
              <p className="text-xs text-text leading-relaxed">
                <span className="font-semibold">6-hour gap</span> between peak
                footfall (12 PM) and peak sales (6 PM). Noon crowds browse but
                don&apos;t convert - consider lunchtime promotions or checkout
                speed improvements to capture this traffic.
              </p>
            </div>
          </div>
        </RetroCard>
      </div>
    </RetroWindow>
  );
}
