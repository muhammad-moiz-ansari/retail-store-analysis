/** Drop browser-supplied service/actor headers before forwarding verified session identity. */
export function backendHeaders(incoming: Headers, session: {
  role: string; email: string; userId?: string;
}, secret: string): Headers {
  const headers = new Headers(incoming);
  for (const key of Array.from(headers.keys())) {
    if (["host", "cookie", "authorization"].includes(key) || key.startsWith("x-retailpulse-")) headers.delete(key);
  }
  headers.set("x-retailpulse-internal-secret", secret);
  headers.set("x-retailpulse-role", session.role);
  headers.set("x-retailpulse-email", session.email);
  if (session.userId) headers.set("x-retailpulse-user-id", session.userId);
  return headers;
}

/** First path segments the FastAPI backend serves (app.py routes, the /agents, /analytics and /aisle-relay routers, the /camera mount). */
export const FORWARDABLE_ROOTS = new Set([
  "accounts", "agents", "aisle-relay", "alerts", "analytics", "analyze-frame", "auth", "camera", "compare-people",
  "interaction", "jobs", "orchestrator", "settings", "system-status", "tasks", "voice-agent",
]);

/** "bad" for dot or separator segments (path traversal), "unknown" for a root the backend doesn't serve. */
export function checkForwardablePath(path: string[]): "ok" | "bad" | "unknown" {
  if (!path.length || path.some((s) => !s || s === "." || s === ".." || /[\/\\]/.test(s))) return "bad";
  return FORWARDABLE_ROOTS.has(path[0]) ? "ok" : "unknown";
}
