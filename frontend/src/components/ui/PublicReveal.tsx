"use client";

import { useEffect, useRef, type ReactNode } from "react";

export function PublicReveal({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = ref.current;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!element?.animate || motion.matches || !("IntersectionObserver" in window)) return;

    let animation: Animation | undefined;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      observer.disconnect();

      const target = document.querySelector(":target");
      if (motion.matches || target?.contains(element) || element.contains(target) ||
          element.contains(document.activeElement)) return;

      animation = element.animate(
        [{ opacity: 0.55, transform: "translateY(14px)" }, { opacity: 1, transform: "translateY(0)" }],
        { duration: 340, easing: "ease-out" },
      );
    });

    function cancelAnimation() {
      animation?.cancel();
    }

    observer.observe(element);
    motion.addEventListener("change", cancelAnimation);
    element.addEventListener("focusin", cancelAnimation);
    return () => {
      observer.disconnect();
      cancelAnimation();
      motion.removeEventListener("change", cancelAnimation);
      element.removeEventListener("focusin", cancelAnimation);
    };
  }, []);

  return <div ref={ref}>{children}</div>;
}
