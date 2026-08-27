import React from "react";

interface RetroInputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Render a leading icon (e.g. a search SVG) */
  leadingIcon?: React.ReactNode;
  /** Show danger-colored border and helper text */
  error?: boolean;
  /** Helper / error message displayed below the input */
  helperText?: string;
  /** Visible label above the input */
  label?: string;
}

export function RetroInput({
  leadingIcon,
  error = false,
  helperText,
  label,
  className = "",
  id,
  ...props
}: RetroInputProps) {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

  return (
    <div className="w-full">
      {label && (
        <label
          htmlFor={inputId}
          className="block mb-1.5 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase"
        >
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {leadingIcon && (
          <span className="absolute left-3 text-text-muted pointer-events-none">
            {leadingIcon}
          </span>
        )}
        <input
          id={inputId}
          {...props}
          className={[
            "w-full rounded-md border-2 bg-surface px-3 py-2",
            "font-body text-sm text-text placeholder:text-text-muted/60",
            "focus:outline-none focus:ring-1 transition-colors",
            /* Inset look */
            "shadow-[inset_1px_2px_4px_rgba(74,46,30,0.15)]",
            /* Error vs normal border */
            error
              ? "border-danger focus:border-danger focus:ring-danger/30"
              : "border-border-soft focus:border-accent focus:ring-accent/30",
            leadingIcon ? "pl-9" : "",
            className,
          ].join(" ")}
        />
      </div>
      {helperText && (
        <p
          className={`mt-1 text-xs ${
            error ? "text-danger" : "text-text-muted"
          }`}
        >
          {helperText}
        </p>
      )}
    </div>
  );
}
