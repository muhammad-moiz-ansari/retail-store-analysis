import React from "react";

type ButtonVariant = "primary" | "secondary" | "danger";

interface RetroButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-surface border-border hover:bg-accent-hover",
  secondary:
    "bg-surface text-text border-border hover:bg-surface-alt",
  danger:
    "bg-danger text-surface border-border hover:brightness-110",
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
        /* Base */
        "inline-flex items-center justify-center gap-2 px-4 py-2",
        "font-heading text-sm font-semibold tracking-wide",
        "rounded-md border-2 cursor-pointer select-none",
        "transition-all duration-100",
        /* Shadow & active press */
        "shadow-[2px_2px_0px_rgba(74,46,30,0.25)]",
        "active:shadow-none active:translate-x-[2px] active:translate-y-[2px]",
        /* Disabled */
        "disabled:opacity-50 disabled:cursor-not-allowed disabled:active:shadow-[2px_2px_0px_rgba(74,46,30,0.25)] disabled:active:translate-x-0 disabled:active:translate-y-0",
        /* Variant */
        variantStyles[variant],
        className,
      ].join(" ")}
    >
      {children}
    </button>
  );
}
