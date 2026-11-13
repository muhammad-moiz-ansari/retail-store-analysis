"use client";

import type { ComponentProps, PointerEvent } from "react";
import Link from "next/link";

function move(event: PointerEvent<HTMLElement>) {
  if (event.pointerType !== "mouse" || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const element = event.currentTarget;
  const rect = element.getBoundingClientRect();
  const x = (event.clientX - rect.left) / rect.width - 0.5;
  const y = (event.clientY - rect.top) / rect.height - 0.5;
  element.style.setProperty("--pointer-x", String(x));
  element.style.setProperty("--pointer-y", String(y));
}

function reset(event: PointerEvent<HTMLElement>) {
  event.currentTarget.style.removeProperty("--pointer-x");
  event.currentTarget.style.removeProperty("--pointer-y");
}

export function HoloPreview(props: ComponentProps<"figure">) {
  return <figure {...props} onPointerMove={move} onPointerLeave={reset} />;
}

export function EffectLink(props: ComponentProps<typeof Link>) {
  return <Link {...props} onPointerMove={move} onPointerLeave={reset} />;
}

export function EffectAnchor(props: ComponentProps<"a">) {
  return <a {...props} onPointerMove={move} onPointerLeave={reset} />;
}
