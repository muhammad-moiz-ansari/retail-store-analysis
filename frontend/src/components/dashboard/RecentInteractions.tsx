"use client";

import { useEffect, useState } from "react";
import type { AnalyticsRequest } from "../../lib/analytics-provider/contracts";
import { validateRequest } from "../../lib/analytics-provider/provider";
import { ManagerPanel } from "../ui/ManagerLayout";

type InteractionEvent = {
  id: string;
  cameraId: string;
  zoneId: string;
  startedAt: string;
  endedAt: string;
  verdict: "interaction" | "unverified";
};

type RecentEvents = { events: InteractionEvent[]; synthetic: boolean; truncated: boolean };

function isEvent(value: unknown): value is InteractionEvent {
  if (!value || typeof value !== "object") return false;
  const row = value as Partial<InteractionEvent>;
  return typeof row.id === "string" && typeof row.cameraId === "string" && typeof row.zoneId === "string" &&
    typeof row.startedAt === "string" && typeof row.endedAt === "string" &&
    Number.isFinite(Date.parse(row.startedAt)) && Date.parse(row.startedAt) <= Date.parse(row.endedAt) &&
    (row.verdict === "interaction" || row.verdict === "unverified");
}

function parseRecentEvents(body: unknown, selection: AnalyticsRequest): RecentEvents {
  if (!body || typeof body !== "object" || !("request" in body)) throw new Error("Invalid recent interactions");
  validateRequest(body.request);
  const request = body.request;
  const data = body as Partial<RecentEvents>;
  if (request.storeId !== selection.storeId || request.window.start !== selection.window.start ||
      request.window.end !== selection.window.end || request.filters.runId !== selection.filters.runId ||
      request.filters.cameraId !== selection.filters.cameraId || request.filters.zoneId !== selection.filters.zoneId ||
      typeof data.synthetic !== "boolean" || typeof data.truncated !== "boolean" ||
      !Array.isArray(data.events) || data.events.length > 10 || !data.events.every(isEvent)) {
    throw new Error("Invalid recent interactions");
  }
  return { events: data.events, synthetic: data.synthetic, truncated: data.truncated };
}

export function RecentInteractions({ selection }: { selection?: AnalyticsRequest }) {
  const [result, setResult] = useState<RecentEvents | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!selection) return;
    const controller = new AbortController();
    fetch("/api/backend/analytics/dashboard/interactions", {
      credentials: "same-origin", cache: "no-store", signal: controller.signal,
    }).then(async (response) => {
      if (!response.ok) throw new Error("Recent interactions unavailable");
      return parseRecentEvents(await response.json(), selection);
    }).then((data) => {
      if (!controller.signal.aborted) setResult(data);
    }).catch(() => {
      if (!controller.signal.aborted) setFailed(true);
    });
    return () => controller.abort();
  }, [selection]);

  return (
    <ManagerPanel title="Recent interactions">
      {!selection ? <p className="text-sm text-text-muted">Recorded interaction rows require a configured backend selection.</p>
        : failed ? <p role="status" className="text-sm text-text-muted">Recorded interaction rows unavailable.</p>
        : !result ? <p role="status" className="text-sm text-text-muted">Loading recorded interactions…</p>
        : <>
          {result.synthetic && <p className="mb-2 text-sm font-semibold">Synthetic backend data</p>}
          {result.events.length === 0 ? <p className="text-sm text-text-muted">No confirmed or unverified interactions were recorded in this selection.</p>
            : <ul className="divide-y divide-border-soft">
              {result.events.map((row) => <li key={row.id} className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 py-2 text-sm">
                <span className="font-semibold">{row.verdict === "interaction" ? "Confirmed" : "Unverified"}</span>
                <time dateTime={row.startedAt}>{new Date(row.startedAt).toLocaleString()}</time>
                <span className="text-text-muted">{row.cameraId} · {row.zoneId}</span>
              </li>)}
            </ul>}
          {result.truncated && <p className="mt-2 text-xs text-text-muted">Showing the 10 most recent recorded interactions.</p>}
        </>}
    </ManagerPanel>
  );
}
