import type { AnalyticsRequest } from "./contracts";

const statuses = ["ok", "partial", "insufficient_evidence", "refused", "unavailable"] as const;

type Citation = { source: string; ids: string[]; matched_count: number; truncated: boolean };
type AskStatus = typeof statuses[number];
export type AskAnswer = {
  status: AskStatus;
  response: string;
  citations: Citation[];
  limitations: string[];
  synthetic: boolean;
  retainedRunId?: string;
};

function isCitation(value: unknown): value is Citation {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<Citation>;
  return typeof item.source === "string" && Array.isArray(item.ids) &&
    item.ids.every((id) => typeof id === "string") && typeof item.matched_count === "number" &&
    Number.isSafeInteger(item.matched_count) && item.matched_count >= item.ids.length &&
    item.truncated === (item.matched_count > item.ids.length);
}

export async function askDashboard(question: string, selection: AnalyticsRequest, signal: AbortSignal, fetcher = fetch): Promise<AskAnswer> {
  const { runId, cameraId, zoneId } = selection.filters;
  const response = await fetcher("/api/backend/agents/ask", {
    method: "POST", credentials: "same-origin", cache: "no-store", signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: question.trim(), window: selection.window,
      filters: { run_id: runId, camera_id: cameraId, zone_id: zoneId } }),
  });
  if (!response.ok) {
    const messages: Record<number, string> = {
      401: "Your session expired. Sign in again to ask a question.",
      403: "Ask access or the configured selection changed. Reload the dashboard and try again.",
      429: "Too many questions. Wait a minute, then try again.",
      503: "Ask RetailPulse is unavailable. Check that the backend is connected and Ask is enabled.",
    };
    throw new Error(messages[response.status] ?? "Ask RetailPulse could not answer this request.");
  }
  const source = response.headers.get("X-RetailPulse-Analytics-Source");
  const body = await response.json().catch(() => null);
  if (!body || !statuses.includes(body.status) || typeof body.response !== "string" ||
    !Array.isArray(body.citations) || !body.citations.every(isCitation) ||
    !Array.isArray(body.limitations) || !body.limitations.every((item: unknown) => typeof item === "string") ||
    (source !== "synthetic" && source !== "recorded")) {
    throw new Error("Ask RetailPulse returned an invalid answer.");
  }
  return { status: body.status, response: body.response, citations: body.citations,
    limitations: body.limitations, synthetic: source === "synthetic",
    ...(body.trace_retained === true && typeof body.run_id === "string" ? { retainedRunId: body.run_id } : {}) };
}


export async function loadAskSummary(runId: string, signal: AbortSignal): Promise<{ text: string; citations: Citation[] }[]> {
  const response = await fetch("/api/backend/agents/runs/" + encodeURIComponent(runId) + "/summary", {
    credentials: "same-origin", cache: "no-store", signal,
  });
  if (!response.ok) throw new Error("Cited summary unavailable.");
  const data = await response.json();
  if (!Array.isArray(data?.sentences) || data.sentences.length > 5 || !data.sentences.every(
    (sentence: { text?: unknown; citations?: unknown }) => sentence && typeof sentence.text === "string" &&
      Array.isArray(sentence.citations) && sentence.citations.every(isCitation),
  )) throw new Error("Invalid cited summary.");
  return data.sentences;
}
