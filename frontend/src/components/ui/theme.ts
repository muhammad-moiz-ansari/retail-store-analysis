export const storageKey = "retailpulse-theme";

// Runs in the document head, before the page or its controls are painted.
export const themeBootstrap = `(() => {
  const root = document.documentElement;
  const system = matchMedia("(prefers-color-scheme: dark)");
  function apply() {
    let saved;
    try { saved = localStorage.getItem("${storageKey}"); } catch {}
    root.dataset.theme = saved === "dark" || saved === "light" ? saved : system.matches ? "dark" : "light";
  }
  apply();
  system.addEventListener("change", () => { if (!root.hasAttribute("data-theme-override")) apply(); });
  addEventListener("storage", event => {
    if (event.key !== "${storageKey}" && event.key !== null) return;
    root.removeAttribute("data-theme-override");
    apply();
  });
})();`;
