import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { createSession, SESSION_COOKIE, verifySession } from "@/lib/session-auth";
import { resolveAuthConfig } from "@/lib/auth-config";

const SERVICE_URL = process.env.RETAILPULSE_SERVICE_URL || "http://127.0.0.1:8011";

export async function GET() {
  const auth = resolveAuthConfig();
  if (!auth) {
    return NextResponse.json({ error: "RetailPulse authentication is not configured" }, { status: 503 });
  }
  const cookieStore = await cookies();
  const session = verifySession(cookieStore.get(SESSION_COOKIE)?.value);
  return NextResponse.json({
    authenticated: Boolean(session),
    role: session?.role ?? null,
    userId: session?.userId ?? null,
    email: session?.email ?? null,
    name: session?.name ?? null,
  });
}

// Per-address failed sign-ins (security review S3). Held in this server instance's memory, so on a platform that runs
// several instances it slows a single source down but is not a global limit; the backend's per-account lockout still applies.
const LOGIN_MAX_FAILURES = 20;
const LOGIN_WINDOW_MS = 15 * 60 * 1000;
const failedLogins = new Map<string, number[]>();

function recentFailures(address: string, now: number) {
  const recent = (failedLogins.get(address) ?? []).filter((stamp) => now - stamp < LOGIN_WINDOW_MS);
  if (recent.length) failedLogins.set(address, recent);
  else failedLogins.delete(address);
  return recent;
}

export async function POST(request: NextRequest) {
  const auth = resolveAuthConfig();
  if (!auth) {
    return NextResponse.json({ error: "RetailPulse authentication is not configured" }, { status: 503 });
  }
  // The platform proxy sets x-forwarded-for; its first entry is the client address.
  const address = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  const now = Date.now();
  if (recentFailures(address, now).length >= LOGIN_MAX_FAILURES) {
    return NextResponse.json({ error: "Too many failed sign-ins from this address; try again in 15 minutes" }, { status: 429, headers: { "Retry-After": "900" } });
  }
  const body = await request.json().catch(() => ({}));
  const email = String(body.email || "").trim();
  const password = String(body.password || "");
  const response = await fetch(`${SERVICE_URL.replace(/\/$/, "")}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-retailpulse-internal-secret": auth.internalSecret,
    },
    body: JSON.stringify({ email, password }),
    cache: "no-store",
  }).catch((error: Error) => error);
  if (response instanceof Error) {
    return NextResponse.json({ error: "RetailPulse backend is unavailable", detail: response.message }, { status: 503 });
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      if (failedLogins.size > 10000) failedLogins.clear();
      failedLogins.set(address, [...recentFailures(address, now), now]);
    }
    return NextResponse.json({ error: data.detail || "Sign-in failed" }, { status: response.status });
  }
  failedLogins.delete(address);
  const user = data.user;
  // The sign-in page asks which workspace to open. The account's stored role still decides access; a different
  // choice is refused before any session exists, so nobody lands in a workspace they did not pick.
  const chosen = body.role === "Manager" || body.role === "Employee" ? body.role : null;
  if (chosen && user.role !== chosen) {
    return NextResponse.json({ error: `This is ${user.role === "Employee" ? "an Employee" : "a Manager"} account. Choose ${user.role} to sign in.` }, { status: 403 });
  }
  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE, createSession({ role: user.role, userId: user.id, email: user.email, name: user.name }), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
  return NextResponse.json({ authenticated: true, role: user.role, userId: user.id, email: user.email, name: user.name });
}
