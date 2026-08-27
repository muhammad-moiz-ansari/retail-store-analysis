import React from "react";

/**
 * RetailPulse logo — shopping cart icon with a pulse/heartbeat line,
 * rendered as an inline SVG in --color-accent.
 */
export function Logo({ size = 32 }: { size?: number }) {
  return (
    <div className="flex items-center gap-2.5">
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Cart body */}
        <path
          d="M6 6h2l1 2h18l-3 10H11L8 8H6z"
          fill="var(--color-accent)"
          opacity="0.85"
        />
        {/* Cart wheels */}
        <circle cx="12" cy="23" r="2" fill="var(--color-accent)" />
        <circle cx="22" cy="23" r="2" fill="var(--color-accent)" />
        {/* Pulse/heartbeat line across the cart */}
        <polyline
          points="4,15 10,15 12,10 14,19 16,13 18,16 20,14 22,15 28,15"
          stroke="var(--color-accent-soft)"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
      </svg>
      <span className="font-heading text-xl font-bold tracking-tight text-text">
        Retail<span className="text-accent">Pulse</span>
      </span>
    </div>
  );
}
