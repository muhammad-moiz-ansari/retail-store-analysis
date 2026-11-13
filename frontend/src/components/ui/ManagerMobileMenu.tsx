"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

export function ManagerMobileMenu({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function dismiss(event: PointerEvent) {
      if (event.target instanceof Node && !menu.current?.contains(event.target)) setOpen(false);
    }
    function escape(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      setOpen(false);
      button.current?.focus();
    }
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  return (
    <div ref={menu} className="manager-mobile-menu relative" data-open={open}>
      <button ref={button} type="button" aria-label={open ? "Close manager menu" : "Open manager menu"}
        aria-expanded={open} aria-controls="manager-mobile-navigation" onClick={() => setOpen(value => !value)}
        className="grid size-11 cursor-pointer place-items-center rounded-lg hover:bg-white/15">
        <svg viewBox="0 0 24 24" aria-hidden="true" className="size-6 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round">
          <path d="M4 6h16" /><path d="M4 12h16" /><path d="M4 18h16" />
        </svg>
      </button>
      <div id="manager-mobile-navigation" inert={!open} aria-hidden={!open}
        className="manager-mobile-dropdown absolute right-0 top-full mt-2 grid max-h-[70dvh] w-[min(16rem,80vw)] gap-2 overflow-y-auto rounded-xl border border-white/25 bg-sidebar p-2 shadow-lg">
        {children}
      </div>
    </div>
  );
}
