import React from "react";

interface RetroCardProps {
  /** Optional small monospace label tag in the top-left corner */
  label?: string;
  children: React.ReactNode;
  className?: string;
}

export function RetroCard({
  label,
  children,
  className = "",
}: RetroCardProps) {
  return (
    <div
      className={`relative rounded-lg border border-border-soft bg-surface p-5 ${className}`}
      style={{ boxShadow: "3px 3px 0px rgba(74, 46, 30, 0.12)" }}
    >
      {label && (
        <span className="absolute -top-2.5 left-3 inline-block bg-surface-alt px-2 py-0.5 rounded font-mono text-[10px] font-semibold tracking-[0.12em] text-text-muted uppercase border border-border-soft">
          {label}
        </span>
      )}
      {children}
    </div>
  );
}
