import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { acceptsDemoCredential, createManagerSession, POS_SESSION_COOKIE, verifyManagerSession } from "@/lib/pos-auth";

export async function GET() {
  const cookieStore = await cookies();
  const session = verifyManagerSession(cookieStore.get(POS_SESSION_COOKIE)?.value);
  return NextResponse.json({
    authenticated: Boolean(session),
    role: session?.role ?? null,
    email: session?.email ?? null,
  });
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  const email = String(body.email || "").trim();
  const password = String(body.password || "");
  if (!acceptsDemoCredential(email, password)) {
    return NextResponse.json({ error: "Enter a valid email and a password with at least 6 characters" }, { status: 401 });
  }
  const cookieStore = await cookies();
  cookieStore.set(POS_SESSION_COOKIE, createManagerSession(email), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
  return NextResponse.json({ authenticated: true, role: "Manager", email });
}
