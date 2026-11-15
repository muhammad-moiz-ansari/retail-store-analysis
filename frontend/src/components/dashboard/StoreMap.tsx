"use client";

import { useId, useState } from "react";
import type { AnalyticsSnapshot } from "../../lib/analytics-provider/contracts";
import { ManagerPanel } from "../ui/ManagerLayout";

const categories = {
  customer: { label: "Customer", color: "var(--color-cyan)" },
  employee: { label: "Employee", color: "var(--color-accent)" },
  customer_employee: { label: "Customer–employee both", color: "var(--color-coral)" },
  no_one: { label: "No one", color: "var(--color-lime)" },
} as const;

const layers = {
  customer_presence: "Customer presence (seconds)",
  employee_presence: "Employee presence (seconds)",
  confirmed_interactions: "Confirmed interactions (count)",
  unverified_interactions: "Unverified interactions (count)",
} as const;

type Category = keyof typeof categories;
type Layer = keyof typeof layers;
type Point = [number, number];
type MapCell = {
  id: string;
  polygon: Point[];
  category: Category | null;
  quality: "ok" | "unmapped" | "insufficient_coverage" | "unknown_role";
  values: Partial<Record<Layer, number | null>>;
};
type MapData = { version: string; cells: MapCell[] };

const layerNames = Object.keys(layers) as Layer[];

function isMapCell(value: unknown): value is MapCell {
  if (!value || typeof value !== "object") return false;
  const cell = value as Partial<MapCell>;
  return typeof cell.id === "string" && cell.id.length > 0 && cell.id.length <= 200 &&
    Array.isArray(cell.polygon) && cell.polygon.length >= 3 && cell.polygon.length <= 64 &&
    cell.polygon.every((point) => Array.isArray(point) && point.length === 2 &&
      point.every((coordinate) => typeof coordinate === "number" && coordinate >= 0 && coordinate <= 1)) &&
    (cell.quality === "ok" ? typeof cell.category === "string" && Object.prototype.hasOwnProperty.call(categories, cell.category)
      : cell.category === null && ["unmapped", "insufficient_coverage", "unknown_role"].includes(String(cell.quality))) &&
    Boolean(cell.values && typeof cell.values === "object" && !Array.isArray(cell.values) &&
      Object.entries(cell.values).every(([key, amount]) => Object.prototype.hasOwnProperty.call(layers, key) &&
        (amount === null || (typeof amount === "number" && Number.isFinite(amount) && amount >= 0 &&
          (!key.endsWith("interactions") || Number.isInteger(amount))))) &&
    (cell.quality !== "unmapped" || Object.values(cell.values ?? {}).every((amount) => amount === null));
}

function parseMap(snapshot?: AnalyticsSnapshot): MapData | null {
  const raw = snapshot?.spatial;
  if (!snapshot || !raw || typeof raw !== "object") return null;
  const data = raw as Partial<MapData> & { window?: AnalyticsSnapshot["request"]["window"] };
  if (typeof data.version !== "string" || !data.version.trim() || data.version.length > 200 ||
    data.window?.start !== snapshot.request.window.start || data.window?.end !== snapshot.request.window.end ||
    !Array.isArray(data.cells) || data.cells.length === 0 || data.cells.length > 500 ||
    !data.cells.every(isMapCell) || new Set(data.cells.map((cell) => cell.id)).size !== data.cells.length) return null;
  return { version: data.version, cells: data.cells };
}

const qualityLabels = {
  unmapped: "Unmapped",
  insufficient_coverage: "Insufficient coverage",
  unknown_role: "Unknown role",
} as const;

export function StoreMap({ snapshot, stale }: { snapshot?: AnalyticsSnapshot; stale?: boolean }) {
  const [mode, setMode] = useState<"category" | Layer>("category");
  const selectorId = useId();
  const map = parseMap(snapshot);
  if (!map) return (
    <ManagerPanel title="Store map and heatmaps">
      <p className="text-sm text-text-muted">Map analytics are unavailable for this selection.</p>
    </ManagerPanel>
  );
  const max = mode === "category" ? 0 : Math.max(0, ...map.cells.map((cell) => cell.values[mode] ?? 0));
  function label(cell: MapCell) {
    if (mode === "category") return cell.category ? categories[cell.category].label : qualityLabels[cell.quality as keyof typeof qualityLabels];
    return cell.values[mode]?.toLocaleString() ?? "Unavailable";
  }

  return (
    <ManagerPanel title="Store map and heatmaps">
      {snapshot?.provenance.synthetic && <p className="mb-2 text-sm font-semibold">Synthetic backend data</p>}
      {stale && <p className="mb-2 text-sm text-text-muted" role="status">Showing stale map data.</p>}
      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
        <label htmlFor={selectorId} className="font-semibold">Map layer</label>
        <select id={selectorId} className="rounded-md border border-border-soft bg-surface px-2 py-1"
          value={mode} onChange={(event) => setMode(event.target.value as "category" | Layer)}>
          <option value="category">Occupancy category</option>
          {layerNames.map((layer) => <option value={layer} key={layer}>{layers[layer]}</option>)}
        </select>
      </div>
      <svg className="mx-auto max-h-96 w-full rounded-md bg-surface-alt" viewBox="0 0 100 100"
        role="img" aria-label={mode === "category" ? "Store map by occupancy category" : layers[mode]}>
        {map.cells.map((cell) => {
          const amount = mode === "category" ? null : cell.values[mode];
          const fill = mode === "category" && cell.category ? categories[cell.category].color
            : mode !== "category" && amount != null ? "var(--color-accent)" : "var(--color-surface)";
          return <polygon key={cell.id} points={cell.polygon.map(([x, y]) => [x * 100, y * 100].join(",")).join(" ")}
            fill={fill} fillOpacity={amount != null && max > 0 ? 0.15 + 0.85 * amount / max : 1}
            stroke="var(--color-text-muted)" strokeWidth="0.3">
            <title>{cell.id} · {label(cell)}</title>
          </polygon>;
        })}
      </svg>
      {mode === "category" && <ul className="mt-3 flex flex-wrap gap-3 text-xs">
        {Object.values(categories).map(({ label: name, color }) => <li key={name} className="flex items-center gap-1">
          <span aria-hidden="true" className="inline-block size-3 rounded-sm" style={{ backgroundColor: color }} />{name}
        </li>)}
      </ul>}
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer font-semibold">Cell values</summary>
        <dl className="mt-2 max-h-56 space-y-1 overflow-auto">
          {map.cells.map((cell) => <div key={cell.id} className="flex justify-between gap-3">
            <dt>{cell.id}</dt><dd>{label(cell)}</dd>
          </div>)}
        </dl>
      </details>
    </ManagerPanel>
  );
}
