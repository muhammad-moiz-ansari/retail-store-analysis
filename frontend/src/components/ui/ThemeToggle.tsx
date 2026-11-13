"use client";

import { storageKey } from "./theme";

function switchTheme() {
  const root = document.documentElement;
  const theme = root.dataset.theme === "dark" ? "light" : "dark";
  root.dataset.themeOverride = "";
  root.dataset.theme = theme;
  try { localStorage.setItem(storageKey, theme); } catch {}
}

export function ThemeToggle() {
  return (
    <button type="button" className="theme-toggle" onClick={switchTheme}>
      <span className="theme-toggle-light">
        <span className="sr-only">Switch to dark mode</span>
        <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M20.9 13.35A9 9 0 0 1 10.65 3.1 9 9 0 1 0 20.9 13.35Z" /></svg>
      </span>
      <span className="theme-toggle-dark">
        <span className="sr-only">Switch to light mode</span>
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4m0-14.2-1.4 1.4M6.3 17.7l-1.4 1.4" />
        </svg>
      </span>
    </button>
  );
}
