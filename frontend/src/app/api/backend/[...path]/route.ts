import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE, verifySession } from "@/lib/session-auth";
import { resolveAuthConfig } from "@/lib/auth-config";
import { backendHeaders, checkForwardablePath } from "@/lib/backend-identity";

const SERVICE_URL = process.env.RETAILPULSE_SERVICE_URL || "http://127.0.0.1:8011";

type Ctx = {
  params: Promise<{ path: string[] }>;
};

async function proxy(request: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  const pathCheck = checkForwardablePath(path);
  if (pathCheck !== "ok") {
    return NextResponse.json({ error: "Unknown backend route" }, { status: pathCheck === "bad" ? 400 : 404 });
  }
  const protectedAnalytics = path[0] === "analytics" || path[0] === "agents";
  const auth = resolveAuthConfig(process.env, protectedAnalytics);
  if (!auth) {
    return NextResponse.json({ error: "RetailPulse authentication is not configured" }, { status: 503 });
  }
  const cookieStore = await cookies();
  const session = verifySession(cookieStore.get(SESSION_COOKIE)?.value);
  if (!session) {
    return NextResponse.json({ error: "RetailPulse session required" }, { status: 401 });
  }

  if (protectedAnalytics && (session.role !== "Manager" || !session.userId)) {
    return NextResponse.json({ error: "Manager account identity required" }, { status: 403 });
  }
  const targetUrl = new URL(`${SERVICE_URL.replace(/\/$/, "")}/${path.join("/")}`);
  const incomingUrl = new URL(request.url);
  incomingUrl.searchParams.forEach((value, key) => targetUrl.searchParams.set(key, value));
  const headers = backendHeaders(request.headers, session, auth.internalSecret);

  try {
    const response = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer(),
      cache: "no-store",
      signal: protectedAnalytics ? AbortSignal.any([request.signal, AbortSignal.timeout(30000)]) : undefined,
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
