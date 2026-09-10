import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { POS_SESSION_COOKIE, verifySession } from "@/lib/pos-auth";

const SERVICE_URL = process.env.RETAILPULSE_SERVICE_URL || "http://127.0.0.1:8011";
const INTERNAL_SECRET = process.env.RETAILPULSE_INTERNAL_SECRET || process.env.POS_INTERNAL_SECRET || "local-dev-pos-secret";

type Ctx = {
  params: Promise<{ path: string[] }>;
};

async function proxy(request: NextRequest, ctx: Ctx) {
  const cookieStore = await cookies();
  const session = verifySession(cookieStore.get(POS_SESSION_COOKIE)?.value);
  if (!session) {
    return NextResponse.json({ error: "RetailPulse session required" }, { status: 401 });
  }

  const { path } = await ctx.params;
  const targetUrl = new URL(`${SERVICE_URL.replace(/\/$/, "")}/${path.join("/")}`);
  const incomingUrl = new URL(request.url);
  incomingUrl.searchParams.forEach((value, key) => targetUrl.searchParams.set(key, value));
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("cookie");
  headers.set("x-retailpulse-internal-secret", INTERNAL_SECRET);
  headers.set("x-retailpulse-role", session.role);
  headers.set("x-retailpulse-email", session.email);
  if (session.userId) headers.set("x-retailpulse-user-id", session.userId);

  try {
    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer(),
      cache: "no-store",
    });
    const responseHeaders = new Headers(response.headers);
    responseHeaders.delete("content-encoding");
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "RetailPulse backend is unavailable",
        detail: error instanceof Error ? error.message : "Start the unified backend on localhost.",
      },
      { status: 503 }
    );
  }
}

export async function GET(request: NextRequest, ctx: Ctx) {
  return proxy(request, ctx);
}

export async function POST(request: NextRequest, ctx: Ctx) {
  return proxy(request, ctx);
}

export async function PATCH(request: NextRequest, ctx: Ctx) {
  return proxy(request, ctx);
}

export async function PUT(request: NextRequest, ctx: Ctx) {
  return proxy(request, ctx);
}

export async function DELETE(request: NextRequest, ctx: Ctx) {
  return proxy(request, ctx);
}
