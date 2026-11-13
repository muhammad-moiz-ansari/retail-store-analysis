import React from "react";

type ButtonVariant = "primary" | "secondary" | "danger";

interface RetroButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-on-accent border-border hover:bg-accent-hover",
  secondary:
    "bg-surface text-text border-border hover:bg-surface-alt",
  danger:
    "bg-danger text-on-danger border-border hover:brightness-110",
};

export function RetroButton({
  variant = "primary",
  children,
  className = "",
  ...props
}: RetroButtonProps) {
  return (
    <button
      {...props}
      className={[
        "inline-flex min-h-10 items-center justify-center gap-2 px-4 py-2",
        "rounded-lg border cursor-pointer select-none text-sm font-semibold",
        "motion-safe:transition-[background-color,color,box-shadow,translate] motion-safe:duration-150",
        "motion-safe:pointer-fine:hover:enabled:-translate-y-0.5 hover:enabled:shadow-sm",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        /* Variant */
        variantStyles[variant],
        className,
      ].join(" ")}
    >
      {children}
    </button>
  );
}
