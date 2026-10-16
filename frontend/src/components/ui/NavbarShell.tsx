"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { Navbar } from "@/components/ui";
import { useAuth } from "@/components/auth/AuthProvider";

/** Routes where the user is considered authenticated (show role + Log Out) */
const AUTHENTICATED_ROUTES = ["/dashboard", "/customer-info", "/employee-info", "/spatial-analytics", "/settings", "/alerts", "/profile", "/employee", "/employee-home", "/my-performance"];

export function NavbarShell() {
  const pathname = usePathname();
  const { authenticated, role } = useAuth();
  const protectedRoute = AUTHENTICATED_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route + "/")
  );

  return <Navbar authenticated={authenticated && protectedRoute} role={role ?? "Employee"} />;
}
