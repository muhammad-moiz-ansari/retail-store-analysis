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
