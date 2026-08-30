"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";

type NavLink = {
  label: string;
  href: string;
  managerOnly?: boolean;
};

// Unauthenticated (public) quick links
const PUBLIC_QUICK_LINKS: NavLink[] = [
  { label: "Home", href: "/" },
  { label: "About", href: "/about" },
];

// Authenticated (dashboard) quick links
const AUTHENTICATED_QUICK_LINKS: NavLink[] = [
  { label: "Home", href: "/dashboard" },
  { label: "Customer Info", href: "/customer-info" },
  { label: "Employee Info", href: "/employee-info" },
  { label: "Spatial Analytics", href: "/spatial-analytics" },
  { label: "Sales & Product Trends", href: "/sales-trends" },
  { label: "Reports & Exports", href: "/reports" },
  { label: "Store Settings", href: "/settings", managerOnly: true },
  { label: "About", href: "/about" },
];

/** Routes where the user is considered authenticated */
const AUTHENTICATED_ROUTES = [
  "/dashboard",
  "/customer-info",
  "/employee-info",
  "/spatial-analytics",
  "/sales-trends",
  "/reports",
  "/settings",
];

export function Footer() {
  const pathname = usePathname();

  // Determine if user is authenticated based on current route
  const authenticated = AUTHENTICATED_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route + "/")
  );

  // Select quick links based on auth state
  // Note: For authenticated users, we're assuming Manager role for footer links
  // since we don't have access to the actual role prop here
  const quickLinks = authenticated ? AUTHENTICATED_QUICK_LINKS : PUBLIC_QUICK_LINKS;

  return (
    <footer className="bg-surface-alt border-t border-border-soft mt-auto">
      {/* ── Three-column content ── */}
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Column 1: Brand */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <FooterLogo />
              <span className="font-heading text-base font-bold tracking-tight text-text">
                Retail<span className="text-accent">Pulse</span>
              </span>
            </div>
            <p className="text-sm text-text-muted leading-relaxed">
              Turning retail cameras into customer care insight.
            </p>
          </div>

          {/* Column 2: Quick Links */}
          <div>
            <h4 className="font-heading text-xs font-semibold uppercase tracking-wider text-text-muted mb-3">
              Quick Links
            </h4>
            <ul className="space-y-2">
              {quickLinks.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-text hover:text-accent transition-colors duration-150"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Column 3: Contact */}
          <div>
            <h4 className="font-heading text-xs font-semibold uppercase tracking-wider text-text-muted mb-3">
              Contact
            </h4>
            <ul className="space-y-2 text-sm text-text">
              <li className="flex items-center gap-2">
                <PhoneIcon />
                <span>0300-1234567</span>
              </li>
              <li className="flex items-center gap-2">
                <MailIcon />
                <a
                  href="mailto:retailpulse@gmail.com"
                  className="hover:text-accent transition-colors duration-150"
                >
                  retailpulse@gmail.com
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* ── Bottom bar ── */}
      <div className="border-t border-border-soft">
        <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-4">
          <p className="text-center text-xs text-text-muted">
            © 2026 RetailPulse. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}

/** Footer-sized logo with graceful fallback */
function FooterLogo() {
  const [imgError, setImgError] = React.useState(false);

  if (imgError) {
    return <FooterLogoFallback />;
  }

  return (
    <Image
      src="/logo.png"
      alt="RetailPulse logo"
      width={24}
      height={24}
      className="h-6 w-6 object-contain"
      onError={() => setImgError(true)}
    />
  );
}

/** SVG fallback for footer logo */
function FooterLogoFallback() {
  return (
    <svg
      width={24}
      height={24}
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

function PhoneIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-text-muted shrink-0"
    >
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  );
}

function MailIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-text-muted shrink-0"
    >
      <rect width="20" height="16" x="2" y="4" rx="2" />
      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
    </svg>
  );
}
