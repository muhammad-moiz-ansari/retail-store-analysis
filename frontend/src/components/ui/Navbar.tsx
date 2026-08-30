"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { Badge } from "./Badge";
import { RetroButton } from "./RetroButton";
import { useAuth } from "@/components/auth/AuthProvider";

interface NavbarProps {
  /** Show role badge and Log Out button (for authenticated pages like /dashboard) */
  authenticated?: boolean;
  /** User role - only used when authenticated */
  role?: "Manager" | "Employee";
}

type NavLink = {
  label: string;
  href: string;
  managerOnly?: boolean;
  employeeOnly?: boolean;
};

// Unauthenticated (public) nav links
const PUBLIC_NAV_LINKS: NavLink[] = [
  { label: "Home", href: "/" },
  { label: "About", href: "/about" },
];

// Authenticated (dashboard) nav links
const AUTHENTICATED_NAV_LINKS: NavLink[] = [
  { label: "Home", href: "/dashboard" },
  { label: "Customer Info", href: "/customer-info" },
  { label: "Employee Info", href: "/employee-info" },
  { label: "Spatial Analytics", href: "/spatial-analytics" },
  { label: "Sales & Product Trends", href: "/sales-trends" },
  { label: "Reports & Exports", href: "/reports" },
  { label: "Store Settings", href: "/settings", managerOnly: true },
  { label: "About", href: "/about" },
];

const EMPLOYEE_NAV_LINKS: NavLink[] = [
  { label: "My Workspace", href: "/employee", employeeOnly: true },
  { label: "About", href: "/about" },
];

export function Navbar({ authenticated = false, role = "Manager" }: NavbarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { signOut } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [indicatorStyle, setIndicatorStyle] = useState({ left: 0, width: 0 });
  const [showTransition, setShowTransition] = useState(false);
  const linkRefs = useRef<(HTMLAnchorElement | null)[]>([]);
  const navbarRef = useRef<HTMLElement>(null);

  // Select link set based on auth state
  const navLinks = !authenticated
    ? PUBLIC_NAV_LINKS
    : role === "Employee"
      ? EMPLOYEE_NAV_LINKS
      : AUTHENTICATED_NAV_LINKS;
  const visibleLinks = navLinks.filter(
    (link) =>
      (!link.managerOnly || role === "Manager") &&
      (!link.employeeOnly || role === "Employee")
  );

  function handleSignOut() {
    signOut();
    setMobileMenuOpen(false);
    router.push("/");
  }

  // Update sliding indicator position
  useEffect(() => {
    const activeIndex = visibleLinks.findIndex((link) => pathname === link.href);
    if (activeIndex !== -1 && linkRefs.current[activeIndex]) {
      const activeLink = linkRefs.current[activeIndex];
      if (activeLink) {
        const newLeft = activeLink.offsetLeft;
        const newWidth = activeLink.offsetWidth;
        setIndicatorStyle((prev) => {
          if (prev.left === newLeft && prev.width === newWidth) return prev;
          return { left: newLeft, width: newWidth };
        });
        // Enable transition after first render
        const timer = setTimeout(() => setShowTransition(true), 50);
        return () => clearTimeout(timer);
      }
    }
  }, [pathname, visibleLinks]);

  // Close mobile menu on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        navbarRef.current &&
        !navbarRef.current.contains(event.target as Node) &&
        mobileMenuOpen
      ) {
        setMobileMenuOpen(false);
      }
    };

    if (mobileMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [mobileMenuOpen]);

  return (
    <header
      ref={navbarRef}
      className="sticky top-0 z-50 bg-surface-alt border-b border-border-soft select-none"
      style={{ borderBottomWidth: "1.5px" }}
    >
      {/* ── Desktop & Mobile Container ── */}
      <div className="h-[52px] px-4 md:px-6 flex items-center justify-between">
        {/* ── Left: Logo + Wordmark ── */}
        <Link
          href={authenticated ? (role === "Employee" ? "/employee" : "/dashboard") : "/"}
          className="flex items-center gap-2.5 xl:w-[180px] w-auto shrink-0"
        >
          <NavLogo />
          {/* Wordmark: visible on mobile, hidden on tablet/1024px laptop, visible on large desktop */}
          <span className="min-[1090px]:hidden min-[1280px]:inline font-heading text-lg font-bold tracking-tight text-text">
            Retail<span className="text-accent">Pulse</span>
          </span>
        </Link>

        {/* ── Center: Nav Links (desktop only) ── */}
        <nav className="hidden min-[1090px]:flex items-center justify-center flex-1 relative">
          <div className="flex items-center gap-3 min-[1120px]:gap-4 min-[1292px]:gap-5 relative">
            {visibleLinks.map((link, index) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  ref={(el) => {
                    linkRefs.current[index] = el;
                  }}
                  className={[
                    "text-[13.5px] font-medium transition-all duration-150 relative py-1",
                    isActive
                      ? "text-accent opacity-100 font-medium"
                      : "text-text opacity-75 hover:opacity-100",
                  ].join(" ")}
                >
                  {link.label}
                </Link>
              );
            })}

            {/* Sliding Indicator Bar */}
            <div
              className="absolute bottom-0 h-[2.5px] bg-accent rounded-sm"
              style={{
                left: `${indicatorStyle.left}px`,
                width: `${indicatorStyle.width}px`,
                transition: showTransition
                  ? "left 300ms cubic-bezier(0.4, 0, 0.2, 1), width 300ms cubic-bezier(0.4, 0, 0.2, 1)"
                  : "none",
              }}
            />
          </div>
        </nav>

        {/* ── Right: Auth Controls ── */}
        {authenticated ? (
          // Authenticated: Role Badge + Log Out
          <div className="hidden min-[1090px]:flex items-center gap-3 xl:w-[200px] w-auto justify-end shrink-0">
            <Badge variant={role === "Manager" ? "accent" : "neutral"}>
              {role}
            </Badge>
            <RetroButton onClick={handleSignOut} variant="secondary" className="!px-3 !py-1.5 !text-xs">
              Log Out
            </RetroButton>
          </div>
        ) : (
          // Not authenticated: Sign In + Get Started
          <div className="hidden min-[1090px]:flex items-center gap-3 xl:w-[200px] w-auto justify-end shrink-0">
            <Link href="/login">
              <RetroButton variant="secondary" className="!px-3 !py-1.5 !text-xs">
                Sign In
              </RetroButton>
            </Link>
            <Link href="/signup">
              <RetroButton variant="primary" className="!px-3 !py-1.5 !text-xs">
                Get Started
              </RetroButton>
            </Link>
          </div>
        )}

        {/* ── Right: Hamburger (mobile only) ── */}
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="min-[1090px]:hidden w-[38px] h-[38px] flex flex-col items-center justify-center gap-[4px] border border-border bg-surface rounded"
          style={{ borderWidth: "1.5px" }}
          aria-label="Toggle menu"
        >
          <span
            className={[
              "block w-[18px] h-[2px] bg-text transition-all duration-300 ease-in-out",
              mobileMenuOpen
                ? "rotate-45 translate-y-[6px]"
                : "rotate-0 translate-y-0",
            ].join(" ")}
          />
          <span
            className={[
              "block w-[18px] h-[2px] bg-text transition-all duration-300 ease-in-out",
              mobileMenuOpen ? "opacity-0" : "opacity-100",
            ].join(" ")}
          />
          <span
            className={[
              "block w-[18px] h-[2px] bg-text transition-all duration-300 ease-in-out",
              mobileMenuOpen
                ? "-rotate-45 -translate-y-[6px]"
                : "rotate-0 translate-y-0",
            ].join(" ")}
          />
        </button>
      </div>

      {/* ── Mobile Dropdown Menu ── */}
      <div
        className={[
          "min-[1090px]:hidden overflow-hidden transition-all duration-350 ease-in-out bg-surface-alt border-t border-border-soft",
          mobileMenuOpen ? "max-h-[500px]" : "max-h-0",
        ].join(" ")}
        style={{
          borderBottomWidth: mobileMenuOpen ? "2px" : "0",
          borderBottomColor: "var(--color-border)",
        }}
      >
        {/* Nav Links */}
        {visibleLinks.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setMobileMenuOpen(false)}
              className={[
                "block py-3 px-5 text-sm font-medium border-b border-border-soft transition-colors",
                isActive
                  ? "bg-surface text-accent border-l-[3px] border-l-accent"
                  : "text-text hover:bg-surface",
              ].join(" ")}
            >
              {link.label}
            </Link>
          );
        })}

        {/* Auth Controls (mobile) */}
        {authenticated ? (
          <div className="py-3 px-5 border-t border-border-soft flex items-center justify-between gap-3">
            <Badge variant={role === "Manager" ? "accent" : "neutral"}>
              {role}
            </Badge>
            <RetroButton onClick={handleSignOut} variant="secondary" className="!px-3 !py-1.5 !text-xs">
              Log Out
            </RetroButton>
          </div>
        ) : (
          <div className="py-3 px-5 border-t border-border-soft flex flex-col gap-2">
            <Link href="/login" className="w-full">
              <RetroButton variant="secondary" className="!w-full !text-xs">
                Sign In
              </RetroButton>
            </Link>
            <Link href="/signup" className="w-full">
              <RetroButton variant="primary" className="!w-full !text-xs">
                Get Started
              </RetroButton>
            </Link>
          </div>
        )}
      </div>
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
      width={34}
      height={34}
      className="h-[34px] w-[34px] object-contain"
      onError={() => setImgError(true)}
      priority
    />
  );
}

/** Fallback SVG matching the original Logo component icon */
function LogoFallbackSVG() {
  return (
    <svg
      width={34}
      height={34}
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
