"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AnalyticsSnapshot } from "../../lib/analytics-provider/contracts";

const directions = [
  { key: "entries", label: "Entries", color: "var(--color-accent-soft)" },
  { key: "exits", label: "Exits", color: "var(--color-coral)" },
] as const;

export function FootfallChart({ metrics }: { metrics: AnalyticsSnapshot["metrics"] }) {
  const counts = directions.map(({ key, label, color }) => ({
    label, color, value: metrics[key].value,
  }));
  const hasCounts = counts.some(({ value }) => value !== null);

  return (
    <section className="min-w-0 rounded-2xl border border-border-soft bg-surface p-4 sm:p-6" aria-labelledby="footfall-title">
      <h3 id="footfall-title" className="text-xl font-bold tracking-tight">Recorded footfall</h3>
      <p className="mt-1 text-sm text-text-muted">Crossing counts by direction for the selected observation window.</p>
      {hasCounts ? (
        <div className="mt-4 h-56 min-w-0 sm:h-64">
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <BarChart data={counts} accessibilityLayer margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--color-border-soft)" />
              <XAxis dataKey="label" tick={{ fill: "var(--color-text-muted)", fontSize: 12 }} tickLine={false} />
              <YAxis allowDecimals={false} domain={[0, (maximum: number) => Math.max(1, maximum)]}
                width={55} tick={{ fill: "var(--color-text-muted)", fontSize: 12 }} tickLine={false} />
              <Tooltip cursor={{ fill: "var(--color-surface-alt)" }} />
              <Bar dataKey="value" name="Recorded crossings" radius={[4, 4, 0, 0]} maxBarSize={84} isAnimationActive={false}>
                {counts.map(({ label, color }) => <Cell key={label} fill={color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : <p className="mt-5 rounded-lg bg-surface-alt p-4 text-sm text-text-muted">Crossing counts are unavailable for this selection.</p>}
      <table className="mt-4 w-full text-left text-sm">
        <caption className="sr-only">Recorded crossing counts</caption>
        <thead className="text-text-muted">
          <tr><th scope="col" className="pb-2 font-medium">Direction</th><th scope="col" className="pb-2 text-right font-medium">Count</th></tr>
        </thead>
        <tbody>
          {counts.map(({ label, color, value }) => (
            <tr key={label} className="border-t border-border-soft">
              <th scope="row" className="py-2 font-medium"><span aria-hidden="true" className="mr-2 inline-block size-2 rounded-full" style={{ backgroundColor: color }} />{label}</th>
              <td className="py-2 text-right tabular-nums">{value === null ? "Unavailable" : value.toLocaleString("en-US")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
