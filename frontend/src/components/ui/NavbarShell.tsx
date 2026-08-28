"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { Navbar } from "@/components/ui";

/** Routes where the user is considered authenticated (show role + Log Out) */
const AUTHENTICATED_ROUTES = ["/dashboard", "/customer-info", "/employee-info", "/spatial-analytics", "/sales-trends", "/settings"];

export function NavbarShell() {
  const pathname = usePathname();
  const authenticated = AUTHENTICATED_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route + "/")
  );

  return <Navbar authenticated={authenticated} role="Manager" />;
}
