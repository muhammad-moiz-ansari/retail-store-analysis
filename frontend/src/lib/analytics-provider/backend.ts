import { type AnalyticsProvider, type AnalyticsRequest } from "./contracts";
import { validateRequest } from "./provider";

/** Same-origin session proxy only; no browser credentials, database paths or actor headers. */
export function createBackendProvider(fetcher: typeof fetch = fetch): AnalyticsProvider {
  return {
    mode: "backend",
    async load(request, signal) {
      validateRequest(request);
      const response = await fetcher("/api/backend/analytics/dashboard", {
        method: "POST", credentials: "same-origin", cache: "no-store", signal,
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(request),
      });
      if (!response.ok) throw new Error("Backend analytics unavailable");
      return response.json(); // loadDashboard performs scope/metric/evidence validation.
    },
  };
}

export async function loadBackendSelection(signal?: AbortSignal, fetcher: typeof fetch = fetch): Promise<AnalyticsRequest> {
  const response = await fetcher("/api/backend/analytics/dashboard/context", {
    credentials: "same-origin", cache: "no-store", signal,
  });
  if (!response.ok) throw new Error("Backend selection unavailable");
  const body: unknown = await response.json();
  if (!body || typeof body !== "object" || !("request" in body)) throw new Error("Invalid backend selection");
  validateRequest(body.request);
  return body.request;
}
