"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";

export function EmployeeAccountMenu({ onLogout }: { onLogout: () => Promise<void> }) {
  const menu = useRef<HTMLDetailsElement>(null);

  useEffect(() => {
    function dismiss(event: PointerEvent) {
      if (event.target instanceof Node && !menu.current?.contains(event.target)) {
        menu.current?.removeAttribute("open");
      }
    }
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, []);

  return (
    <details ref={menu} className="relative" onKeyDown={event => {
      if (event.key === "Escape" && event.currentTarget.open) {
        event.currentTarget.open = false;
        event.currentTarget.querySelector("summary")?.focus();
      }
    }}>
      <summary aria-label="Account menu" className="employee-avatar grid size-11 cursor-pointer list-none place-items-center rounded-full [&::-webkit-details-marker]:hidden">
        <svg aria-hidden="true" viewBox="0 0 40 40" className="size-9 rounded-full bg-[#a8adaf] fill-[#f2f3f4]">
          <circle cx="20" cy="15" r="7" /><path d="M4 39a16 16 0 0 1 32 0Z" />
        </svg>
      </summary>
      <div className="employee-account-dropdown absolute right-0 top-full mt-2 grid w-44 gap-1 rounded-xl border border-white/25 bg-sidebar p-2 shadow-xl">
        <Link href="/profile" className="rounded-lg px-3 py-2 hover:bg-white/15">Profile</Link>
        <Link href="/about" className="rounded-lg px-3 py-2 hover:bg-white/15">About</Link>
        <button type="button" onClick={onLogout} className="rounded-lg px-3 py-2 text-left hover:bg-white/15">Log out</button>
      </div>
    </details>
  );
}
