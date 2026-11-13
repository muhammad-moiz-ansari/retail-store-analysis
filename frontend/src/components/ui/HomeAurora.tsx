"use client";

import { useEffect, useState } from "react";
import Aurora from "./Aurora";

const colors = ["#6335D4", "#7779CD", "#007F9E"];

export function HomeAurora({ interactive = false }: { interactive?: boolean }) {
  const [moving, setMoving] = useState(false);

  useEffect(() => {
    const motion = matchMedia("(prefers-reduced-motion: reduce)");
    if (motion.matches) return;
    const stop = () => setMoving(false);
    setMoving(true);
    const timer = interactive ? undefined : window.setTimeout(stop, 4500);
    motion.addEventListener("change", stop);
    return () => {
      clearTimeout(timer);
      motion.removeEventListener("change", stop);
    };
  }, [interactive]);

  return <Aurora colorStops={colors} paused={!moving} intro={false}
    mouseInteraction={interactive && moving} speed={0.65} dpr={1} height={0.48} />;
}
