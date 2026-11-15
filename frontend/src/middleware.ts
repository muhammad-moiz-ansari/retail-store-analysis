import { NextRequest, NextResponse } from "next/server";
import { resolveAuthConfig } from "./lib/auth-config";
import { SESSION_COOKIE, verifySession } from "./lib/session-auth";

export function middleware(request: NextRequest) {
  const session = resolveAuthConfig()
    ? verifySession(request.cookies.get(SESSION_COOKIE)?.value)
    : null;
  if (!session) return NextResponse.redirect(new URL("/login", request.url));

  const workspace = request.nextUrl.pathname.split("/")[1];
  if (workspace === "manager" && session.role !== "Manager") {
    return NextResponse.redirect(new URL("/employee/home", request.url));
  }
  if (workspace === "employee" && session.role !== "Employee") {
    return NextResponse.redirect(new URL("/manager/home", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/manager/:path*", "/employee/:path*", "/profile/:path*"],
  runtime: "nodejs",
};
