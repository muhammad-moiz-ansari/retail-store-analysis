"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { Badge } from "./Badge";
import { RetroButton } from "./RetroButton";

interface NavbarProps {
  /** Show role badge and Log Out button (for authenticated pages like /dashboard) */
  authenticated?: boolean;
  /** User role — only used when authenticated */
  role?: "Manager" | "Employee";
}

const NAV_LINKS = [
  { label: "Home", href: "/dashboard" },
  { label: "Customer Info", href: "/customer-info" },
  { label: "Employee Info", href: "/employee-info" },
  { label: "Spatial Analytics", href: "/spatial-analytics" },
  { label: "Sales & Product Trends", href: "/sales-trends" },
  { label: "Reports & Exports", href: "/reports" },
  { label: "Store Settings", href: "/settings", managerOnly: true },
  { label: "About", href: "/about" },
];

export function Navbar({ authenticated = false, role = "Manager" }: NavbarProps) {
  const pathname = usePathname();

  return (
    <header
      className="sticky top-0 z-40 flex items-center justify-between bg-surface-alt px-4 py-2.5 md:px-6 border-b border-border-soft select-none"
    >
      {/* ── Left: Logo + Nav Links ── */}
      <div className="flex items-center gap-6">
        {/* Logo */}
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <NavLogo />
          <span className="font-heading text-xl font-bold tracking-tight text-text">
            Retail<span className="text-accent">Pulse</span>
          </span>
        </Link>

        {/* Nav Links */}
        <nav className="hidden sm:flex items-center gap-4">
          {NAV_LINKS
            .filter((link) => !link.managerOnly || role === "Manager")
            .map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={[
                    "text-sm font-body transition-colors duration-150",
                    isActive
                      ? "text-accent font-semibold underline underline-offset-4 decoration-2"
                      : "text-text hover:text-accent",
                  ].join(" ")}
                >
                  {link.label}
                </Link>
              );
            })}
        </nav>
      </div>

      {/* ── Right: Auth controls (only when authenticated) ── */}
      {authenticated && (
        <div className="flex items-center gap-3">
          <Badge variant={role === "Manager" ? "accent" : "neutral"}>
            {role}
          </Badge>
          <RetroButton variant="secondary" className="!px-3 !py-1.5 !text-xs">
            Log Out
          </RetroButton>
        </div>
      )}
    </header>
  );
}

/** Logo image with graceful fallback to SVG icon */
function NavLogo() {
  const [imgError, setImgError] = React.useState(false);

  if (imgError) {
    return <LogoFallbackSVG />;
  }

  return (
    <Image
      src="/logo.png"
      alt="RetailPulse logo"
      width={36}
      height={36}
      className="h-9 w-9 object-contain"
      onError={() => setImgError(true)}
      priority
    />
  );
}

/** Fallback SVG matching the original Logo component icon */
function LogoFallbackSVG() {
  return (
    <svg
      width={32}
      height={32}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M6 6h2l1 2h18l-3 10H11L8 8H6z"
        fill="var(--color-accent)"
        opacity="0.85"
      />
      <circle cx="12" cy="23" r="2" fill="var(--color-accent)" />
      <circle cx="22" cy="23" r="2" fill="var(--color-accent)" />
      <polyline
        points="4,15 10,15 12,10 14,19 16,13 18,16 20,14 22,15 28,15"
        stroke="var(--color-accent-soft)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}
