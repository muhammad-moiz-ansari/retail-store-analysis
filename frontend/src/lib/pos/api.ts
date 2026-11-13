import type { PosAnalytics, PosQueryAnswer } from "./types";

export async function fetchPosAnalytics(params: { from?: string; to?: string; horizon?: 7 | 30 } = {}) {
  const url = new URL("/api/pos/analytics", window.location.origin);
  if (params.from) url.searchParams.set("from", params.from);
  if (params.to) url.searchParams.set("to", params.to);
  if (params.horizon) url.searchParams.set("horizon", String(params.horizon));
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).error || "Could not load POS analytics");
  return (await response.json()) as PosAnalytics;
}

export async function runPosAnalysis(params: { from: string; to: string; horizon: 7 | 30 }) {
  const response = await fetch("/api/pos/analysis", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).error || "Could not start POS analysis");
  return response.json();
}

export async function askPos(question: string, filters: { from?: string; to?: string; horizon?: 7 | 30; sku_ids?: string[] } = {}) {
  const response = await fetch("/api/pos/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, filters }),
  });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).error || "Could not query POS evidence");
  return (await response.json()) as PosQueryAnswer;
}
