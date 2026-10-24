import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { createSession, POS_SESSION_COOKIE, verifySession } from "@/lib/pos-auth";

const SERVICE_URL = process.env.RETAILPULSE_SERVICE_URL || "http://127.0.0.1:8011";
const INTERNAL_SECRET = process.env.RETAILPULSE_INTERNAL_SECRET || process.env.POS_INTERNAL_SECRET || "local-dev-pos-secret";

export async function GET() {
  const cookieStore = await cookies();
  const session = verifySession(cookieStore.get(POS_SESSION_COOKIE)?.value);
  return NextResponse.json({
    authenticated: Boolean(session),
    role: session?.role ?? null,
    userId: session?.userId ?? null,
    email: session?.email ?? null,
    name: session?.name ?? null,
  });
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  const email = String(body.email || "").trim();
  const password = String(body.password || "");
  const role = body.role === "Employee" ? "Employee" : "Manager";
  const response = await fetch(`${SERVICE_URL.replace(/\/$/, "")}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-retailpulse-internal-secret": INTERNAL_SECRET,
    },
    body: JSON.stringify({ email, password, role }),
    cache: "no-store",
  }).catch((error: Error) => error);
  if (response instanceof Error) {
    return NextResponse.json({ error: "RetailPulse backend is unavailable", detail: response.message }, { status: 503 });
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    return NextResponse.json({ error: data.detail || "Sign-in failed" }, { status: response.status });
  }
  const user = data.user;
  const cookieStore = await cookies();
  cookieStore.set(POS_SESSION_COOKIE, createSession({ role: user.role, userId: user.id, email: user.email, name: user.name }), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
  return NextResponse.json({ authenticated: true, role: user.role, userId: user.id, email: user.email, name: user.name });
}
