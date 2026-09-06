import React from "react";

interface RetroWindowProps {
  title: string;
  children: React.ReactNode;
  /** When true, the close (red) button fires onClose */
  onClose?: () => void;
  className?: string;
  titleBarClassName?: string;
}

export function RetroWindow({
  title,
  children,
  onClose,
  className = "",
  titleBarClassName = "",
}: RetroWindowProps) {
  return (
    <div
      className={`rounded-lg overflow-hidden border-2 border-border ${className}`}
      style={{ boxShadow: "4px 4px 0px rgba(74, 46, 30, 0.25)" }}
    >
      {/* ── Title bar ── */}
      <div className={`flex items-center justify-between bg-surface-alt px-4 py-2 border-b-2 border-border select-none ${titleBarClassName}`}>
        <span className="font-heading text-sm font-semibold text-text tracking-wide">
          {title}
        </span>

        {/* Traffic-light buttons */}
        <div className="flex items-center gap-1.5">
          <span className="block w-3 h-3 rounded-full bg-accent-soft border border-border/40" />
          <span className="block w-3 h-3 rounded-full bg-accent border border-border/40" />
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="block w-3 h-3 rounded-full bg-danger border border-border/40 cursor-default hover:brightness-110 transition-[filter]"
          />
        </div>
      </div>

      {/* ── Content area ── */}
      <div className="bg-surface p-5">{children}</div>
    </div>
  );
}
