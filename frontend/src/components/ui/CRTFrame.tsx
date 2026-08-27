"use client";

import React, { useRef, useEffect } from "react";

interface CRTFrameProps {
  /** Camera / source label shown on the bottom plaque */
  label?: string;
  /** Show blinking red REC dot */
  live?: boolean;
  /** Path to a video file to play inside the frame (loops, muted, autoplay) */
  videoSrc?: string;
  /** Whether the camera has a signal — false shows a retro "NO SIGNAL" screen (default true) */
  signal?: boolean;
  children?: React.ReactNode;
  className?: string;
}

/** Retro-styled "NO SIGNAL" placeholder */
function NoSignalScreen() {
  return (
    <div className="w-full aspect-video flex items-center justify-center min-h-[160px] bg-gradient-to-br from-neutral-700 to-neutral-800">
      <span className="font-mono text-s tracking-[0.3em] text-neutral-500 uppercase select-none">
        NO SIGNAL
      </span>
    </div>
  );
}

/** Autoplay-safe video player — works around React's muted attribute bug */
function AutoplayVideo({ src, className }: { src: string; className?: string }) {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // Explicitly set muted as a DOM property before trying to play.
    el.defaultMuted = true;
    el.muted = true;

    // Some browsers need a slight delay or a distinct user interaction.
    // Try to play immediately.
    const attemptPlay = () => {
      el.play().catch(error => {
        console.warn("Video autoplay blocked:", error);
      });
    };

    attemptPlay();
  }, []);

  return (
    <video
      ref={ref}
      autoPlay
      loop
      muted
      playsInline
      controls={false}
      preload="auto"
      className={className}
      suppressHydrationWarning
    >
      <source src={src} type="video/mp4" />
    </video>
  );
}

export function CRTFrame({
  label = "CAM 01",
  live = false,
  videoSrc,
  signal = true,
  children,
  className = "",
}: CRTFrameProps) {
  /* Determine what to render inside the screen area */
  const screenContent = !signal ? (
    <NoSignalScreen />
  ) : videoSrc ? (
    <AutoplayVideo src={videoSrc} className="w-full aspect-video object-cover min-h-[160px]" />
  ) : (
    children
  );

  return (
    <div
      className={`relative inline-block rounded-xl bg-border p-3 md:p-4 ${className}`}
      style={{ boxShadow: "4px 4px 0px rgba(74, 46, 30, 0.3)" }}
    >
      {/* ── REC indicator (only when signal is present and live) ── */}
      {signal && live && (
        <div className="absolute top-5 left-5 md:top-6 md:left-6 z-10 flex items-center gap-1.5">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-danger opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-danger" />
          </span>
          <span className="font-mono text-[10px] font-bold tracking-widest text-danger uppercase">
            REC
          </span>
        </div>
      )}

      {/* ── Screen area ── */}
      <div
        className="relative overflow-hidden rounded-md bg-black"
        style={{
          boxShadow:
            "inset 0 2px 8px rgba(0, 0, 0, 0.6), inset 0 0 20px rgba(0, 0, 0, 0.3)",
        }}
      >
        {/* Video / content */}
        <div className="relative z-0">{screenContent}</div>

        {/* Scanline overlay */}
        {!signal && (
          <div className="scanlines absolute inset-0 z-10" />
        )}
      </div>

      {/* ── Bottom label plaque ── */}
      {label && (
        <div className="mt-2 flex justify-center">
          <span
            className="inline-block bg-surface-alt px-3 py-0.5 rounded font-mono text-[11px] tracking-[0.15em] text-text-muted uppercase border border-border-soft"
          >
            {label}
          </span>
        </div>
      )}
    </div>
  );
}
