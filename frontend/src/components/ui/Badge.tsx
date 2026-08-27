import React from "react";

type BadgeVariant = "accent" | "success" | "danger" | "neutral";

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  accent: "bg-accent-soft/80 text-text border-accent-soft",
  success: "bg-success/15 text-success border-success/40",
  danger: "bg-danger/15 text-danger border-danger/40",
  neutral: "bg-surface-alt text-text-muted border-border-soft",
};

export function Badge({
  variant = "neutral",
  children,
  className = "",
}: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 px-2.5 py-0.5",
        "rounded-full border text-[11px] font-semibold font-mono tracking-wide uppercase",
        variantStyles[variant],
        className,
      ].join(" ")}
    >
      {children}
    </span>
  );
}
