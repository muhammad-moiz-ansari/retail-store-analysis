"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";

const MANAGER_ROUTES = [
  "/dashboard",
  "/customer-info",
  "/pos-info",
  "/employee-info",
  "/spatial-analytics",
  "/sales-trends",
  "/reports",
  "/settings",
  "/alerts",
  "/voice-agent",
];
const EMPLOYEE_ROUTES = ["/employee-home", "/my-performance", "/employee"];
const SHARED_AUTHENTICATED_ROUTES = ["/profile"];

function matchesRoute(pathname: string, routes: string[]) {
  return routes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

export function RouteAccessGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { ready, authenticated, role } = useAuth();
  const needsManager = matchesRoute(pathname, MANAGER_ROUTES);
  const needsEmployeeSession = matchesRoute(pathname, EMPLOYEE_ROUTES);
  const needsAuthenticatedSession = matchesRoute(pathname, SHARED_AUTHENTICATED_ROUTES);
  const protectedRoute = needsManager || needsEmployeeSession || needsAuthenticatedSession;

  useEffect(() => {
    if (!ready || !protectedRoute) return;
    if (!authenticated) {
      router.replace("/login");
    } else if (needsManager && role !== "Manager") {
      router.replace("/employee-home");
    } else if (needsEmployeeSession && role !== "Employee") {
      router.replace("/dashboard");
    }
  }, [authenticated, needsEmployeeSession, needsManager, protectedRoute, ready, role, router]);

  const mayView =
    !protectedRoute ||
    (authenticated &&
      (needsAuthenticatedSession ||
        (needsManager && role === "Manager") ||
        (needsEmployeeSession && role === "Employee")));

  if (!mayView) {
    return <div className="flex-1 bg-bg" aria-live="polite" aria-label="Checking access" />;
  }

  return <>{children}</>;
}
