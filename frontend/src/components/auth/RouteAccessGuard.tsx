"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";

const MANAGER_ROUTES = [
  "/dashboard",
  "/customer-info",
  "/employee-info",
  "/spatial-analytics",
  "/sales-trends",
  "/reports",
  "/settings",
];
const EMPLOYEE_ROUTES = ["/employee"];

function matchesRoute(pathname: string, routes: string[]) {
  return routes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

export function RouteAccessGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { ready, authenticated, role } = useAuth();
  const needsManager = matchesRoute(pathname, MANAGER_ROUTES);
  const needsEmployeeSession = matchesRoute(pathname, EMPLOYEE_ROUTES);
  const protectedRoute = needsManager || needsEmployeeSession;

  useEffect(() => {
    if (!ready || !protectedRoute) return;
    if (!authenticated) {
      router.replace("/login");
    } else if (needsManager && role !== "Manager") {
      router.replace("/employee");
    } else if (needsEmployeeSession && role !== "Employee") {
      router.replace("/dashboard");
    }
  }, [authenticated, needsEmployeeSession, needsManager, protectedRoute, ready, role, router]);

  const mayView =
    !protectedRoute ||
    (ready &&
      authenticated &&
      ((needsManager && role === "Manager") || (needsEmployeeSession && role === "Employee")));

  if (!mayView) {
    return <div className="flex-1 bg-bg" aria-live="polite" aria-label="Checking access" />;
  }

  return <>{children}</>;
}
