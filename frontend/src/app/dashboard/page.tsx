"use client";

import React, { useEffect, useState, FormEvent } from "react";
import {
  RetroWindow,
  CRTFrame,
  RetroButton,
  RetroInput,
  RetroCard,
} from "@/components/ui";
import { defaultDashboardData } from "@/lib/dashboard-data";
import { fetchPosAnalytics } from "@/lib/pos/api";
import type { PosAnalytics } from "@/lib/pos/types";

type FlaggedEvent = {
  label: string;
  time: string;
  severity: "danger" | "accent";
};

const { summary, floorAInteractions, floorBInteractions, flaggedEvents } = defaultDashboardData as typeof defaultDashboardData & {
  flaggedEvents: FlaggedEvent[];
};

/* ═══════════════════════════════════════════════════════════════
   Inline SVG icons (no external deps)
   ═══════════════════════════════════════════════════════════════ */

function ChatBubblesIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      <path d="M13 8H7" opacity="0.5" />
      <path d="M17 12H7" opacity="0.5" />
    </svg>
  );
}

function FunnelIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />
    </svg>
  );
}

function MapPinIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function SparkleIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" opacity="0.7">
      <path d="M12 2L14 9L21 9L15.5 13.5L17.5 21L12 16.5L6.5 21L8.5 13.5L3 9L10 9L12 2Z" />
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Sub-components
   ═══════════════════════════════════════════════════════════════ */

/** Footfall stats card (under entrance camera) */
function FootfallCard({
  inCount,
  outCount,
  netInside,
}: {
  inCount: number;
  outCount: number;
  netInside: number;
}) {
  return (
    <RetroCard label="Today's Footfall" className="mt-6">
      <p className="font-mono text-lg font-bold text-text mt-1 tracking-wide">
        IN: <span className="text-success">{inCount}</span> · OUT:{" "}
        <span className="text-accent">{outCount}</span>
      </p>
      <p className="font-mono text-[10px] text-text-muted mt-0.5 tracking-wider uppercase">
        Net inside: {netInside}
      </p>
    </RetroCard>
  );
}

/** Engagement interaction list card (under floor cameras) */
function EngagementCard({
  interactions,
}: {
  interactions: Array<{
    employee: string;
    customer: string;
    duration: string;
    zone: string;
    time: string;
  }>;
}) {
  return (
    <RetroCard label="Recent Interactions" className="mt-6">
      <div className="space-y-1.5 mt-1">
        {interactions.map((i, idx) => (
          <p
            key={idx}
            className="font-mono text-[11px] text-text leading-relaxed"
          >
            <span className="text-accent font-semibold">{i.employee}</span>
            {" ↔ "}
            <span className="text-text-muted">{i.customer}</span>
            {" - "}
            <span className="font-bold">{i.duration}</span>
            <span className="text-text-muted ml-2 text-[10px]">
              {i.zone} · {i.time}
            </span>
          </p>
        ))}
      </div>
    </RetroCard>
  );
}

function PosDashboardPanel() {
  const [analytics, setAnalytics] = useState<PosAnalytics | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchPosAnalytics()
      .then(setAnalytics)
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "POS analytics unavailable"));
  }, []);

  if (!analytics || analytics.products.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-text-muted">
          <FunnelIcon />
          <span className="font-heading text-xs font-semibold uppercase tracking-wider">Live POS</span>
        </div>
        <p className="text-sm leading-relaxed text-text-muted">
          {error || "Import POS data to show revenue, conversion, and product recommendations here."}
        </p>
        <RetroButton variant="secondary" className="w-full !text-xs !py-1.5">View Sales Trends</RetroButton>
      </div>
    );
  }

  const conversion = analytics.conversion.conversion === null ? "NA" : `${(analytics.conversion.conversion * 100).toFixed(1)}%`;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-text-muted">
        <FunnelIcon />
        <span className="font-heading text-xs font-semibold uppercase tracking-wider">Live POS</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-md border border-border-soft bg-surface-alt px-3 py-2">
          <p className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Net revenue</p>
          <p className="font-mono text-lg font-bold text-text">Rs. {Math.round(analytics.kpis.net_revenue).toLocaleString("en-PK")}</p>
        </div>
        <div className="rounded-md border border-border-soft bg-surface-alt px-3 py-2">
          <p className="font-mono text-[10px] uppercase tracking-wider text-text-muted">Conversion</p>
          <p className="font-mono text-lg font-bold text-text">{conversion}</p>
        </div>
      </div>
      <div>
        <p className="mb-2 font-heading text-[10px] font-semibold uppercase tracking-wider text-text-muted">Top products</p>
        <div className="space-y-1.5">
          {analytics.products.slice(0, 3).map((item, i) => (
            <div key={item.sku_id} className="flex items-center justify-between font-mono text-[11px]">
              <span className="text-text"><span className="mr-1.5 font-bold text-accent-soft">#{i + 1}</span>{item.sku_name}</span>
              <span className="text-text-muted">{item.gross_units} units</span>
            </div>
          ))}
        </div>
      </div>
      <p className="font-mono text-[10px] uppercase tracking-wider text-text-muted">
        Run: {analytics.period.from} to {analytics.period.to}
      </p>
    </div>
  );
}

/** Heatmap placeholder SVG */
function HeatmapPlaceholder() {
  return (
    <div className="relative w-full h-32 rounded-md bg-surface-alt border border-border-soft overflow-hidden">
      {/* Store outline */}
      <svg
        className="absolute inset-0 w-full h-full"
        viewBox="0 0 200 100"
        preserveAspectRatio="none"
      >
        <defs>
          <radialGradient id="hot1" cx="35%" cy="40%" r="30%">
            <stop offset="0%" stopColor="var(--color-danger)" stopOpacity="0.6" />
            <stop offset="100%" stopColor="var(--color-danger)" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="hot2" cx="70%" cy="55%" r="25%">
            <stop offset="0%" stopColor="var(--color-accent)" stopOpacity="0.5" />
            <stop offset="100%" stopColor="var(--color-accent)" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="warm1" cx="50%" cy="25%" r="20%">
            <stop offset="0%" stopColor="var(--color-accent-soft)" stopOpacity="0.45" />
            <stop offset="100%" stopColor="var(--color-accent-soft)" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="cool1" cx="15%" cy="75%" r="18%">
            <stop offset="0%" stopColor="var(--color-success)" stopOpacity="0.3" />
            <stop offset="100%" stopColor="var(--color-success)" stopOpacity="0" />
          </radialGradient>
        </defs>
        {/* Grid lines for store layout feel */}
        <line x1="0" y1="50" x2="200" y2="50" stroke="var(--color-border-soft)" strokeWidth="0.3" strokeDasharray="4 3" />
        <line x1="100" y1="0" x2="100" y2="100" stroke="var(--color-border-soft)" strokeWidth="0.3" strokeDasharray="4 3" />
        <line x1="66" y1="0" x2="66" y2="100" stroke="var(--color-border-soft)" strokeWidth="0.2" strokeDasharray="2 4" />
        <line x1="133" y1="0" x2="133" y2="100" stroke="var(--color-border-soft)" strokeWidth="0.2" strokeDasharray="2 4" />
        {/* Heat blobs */}
        <rect width="200" height="100" fill="url(#hot1)" />
        <rect width="200" height="100" fill="url(#hot2)" />
        <rect width="200" height="100" fill="url(#warm1)" />
        <rect width="200" height="100" fill="url(#cool1)" />
      </svg>
      {/* Zone labels */}
      <span className="absolute top-1 left-2 font-mono text-[8px] text-text-muted/60 uppercase">
        Entrance
      </span>
      <span className="absolute top-1 right-2 font-mono text-[8px] text-text-muted/60 uppercase">
        Checkout
      </span>
      <span className="absolute bottom-1 left-1/2 -translate-x-1/2 font-mono text-[8px] text-text-muted/60 uppercase">
        Floor Center
      </span>
    </div>
  );
}

/* Chat message bubble */
function ChatBubble({
  text,
  isUser,
}: {
  text: string;
  isUser: boolean;
}) {
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={[
          "max-w-[85%] px-3 py-2 rounded-lg border text-sm",
          isUser
            ? "bg-accent/10 border-accent/30 text-text rounded-br-sm"
            : "bg-surface border-border-soft text-text-muted rounded-bl-sm",
        ].join(" ")}
      >
        {!isUser && (
          <span className="flex items-center gap-1 text-[10px] font-mono text-accent-soft uppercase font-bold mb-1">
            <SparkleIcon /> RetailPulse AI
          </span>
        )}
        <p className="font-body leading-relaxed">{text}</p>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   AI Agent Search Bar (sticky bottom)
   ═══════════════════════════════════════════════════════════════ */

function AIAgentBar() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<
    { text: string; isUser: boolean }[]
  >([]);
  const [expanded, setExpanded] = useState(false);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    const userMsg = query.trim();
    setMessages((prev) => [
      ...prev,
      { text: userMsg, isUser: true },
      { text: "Analyzing store data…", isUser: false },
    ]);
    setQuery("");
    setExpanded(true);
  }

  return (
    <div className="sticky bottom-0 z-30 bg-bg/80 backdrop-blur-sm border-t-2 border-border">
      {/* Expandable chat area */}
      {expanded && messages.length > 0 && (
        <div className="max-w-5xl mx-auto px-4 md:px-6">
          <div className="bg-surface border border-border-soft border-b-0 rounded-t-lg px-4 py-3 max-h-52 overflow-y-auto space-y-2">
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono text-[10px] text-text-muted uppercase tracking-widest">
                AI Assistant
              </span>
              <button
                onClick={() => setExpanded(false)}
                className="font-mono text-[10px] text-text-muted hover:text-text cursor-pointer"
              >
                ▾ Collapse
              </button>
            </div>
            {messages.map((m, i) => (
              <ChatBubble key={i} text={m.text} isUser={m.isUser} />
            ))}
          </div>
        </div>
      )}

      {/* Input bar */}
      <form onSubmit={handleSubmit} className="max-w-5xl mx-auto px-4 md:px-6 py-3">
        <div className="flex items-center gap-2">
          <RetroInput
            placeholder="Ask about today's store performance..."
            leadingIcon={<SearchIcon />}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1"
          />
          <RetroButton type="submit" variant="primary" className="shrink-0">
            Ask
          </RetroButton>
        </div>
      </form>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Dashboard Page
   ═══════════════════════════════════════════════════════════════ */

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-bg flex flex-col">
      {/* ── Main content (scrollable, padded for sticky bar) ── */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-6 md:py-8 space-y-8 md:space-y-10 pb-28">
        {/* ── Section: Camera Feeds ── */}
        <section>
          <h2 className="font-heading text-lg font-bold text-text mb-4 flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-danger opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-danger" />
            </span>
            Live Camera Feeds
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* CAM 01 - Entrance */}
            <div>
              <CRTFrame label="CAM 01 - ENTRANCE" live signal={false} className="w-full" />
              <FootfallCard inCount={summary.footfallIn} outCount={summary.footfallOut} netInside={summary.netInside} />
            </div>

            {/* CAM 02 - Floor A */}
            <div>
              <CRTFrame label="CAM 02 - FLOOR A" live videoSrc="/videos/cam1.mp4" className="w-full" />
              <EngagementCard interactions={floorAInteractions} />
            </div>

            {/* CAM 03 - Floor B */}
            <div>
              <CRTFrame label="CAM 03 - FLOOR B" live signal={false} className="w-full" />
              <EngagementCard interactions={floorBInteractions} />
            </div>
          </div>
        </section>

        {/* ── Section: Analytics Panels ── */}
        <section>
          <h2 className="font-heading text-lg font-bold text-text mb-4">
            Analytics
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Panel 1: Engagement Tracking */}
            <RetroWindow title="Engagement Tracking" className="relative">
              {/* Accent stripe */}
              <div
                className="absolute left-0 top-0 bottom-0 w-1 rounded-l-lg"
                style={{ backgroundColor: "var(--color-accent)" }}
              />

              <div className="space-y-4">
                {/* Icon + heading */}
                <div className="flex items-center gap-2 text-text-muted">
                  <ChatBubblesIcon />
                  <span className="font-heading text-xs font-semibold uppercase tracking-wider">
                    Summary
                  </span>
                </div>

                {/* Stat grid */}
                <div className="grid grid-cols-3 gap-2">
                  <div className="text-center">
                    <p className="font-mono text-xl font-bold text-text">
                      {summary.employees?.aisle1 ?? 0}
                    </p>
                    <p className="text-[10px] text-text-muted">Aisle 1 Staff</p>
                  </div>
                  <div className="text-center">
                    <p className="font-mono text-xl font-bold text-text">
                      {summary.employees?.aisle2 ?? 0}
                    </p>
                    <p className="text-[10px] text-text-muted">Aisle 2 Staff</p>
                  </div>
                  <div className="text-center">
                    <p className="font-mono text-xl font-bold text-danger">{summary.movementEvents ?? 0}</p>
                    <p className="text-[10px] text-text-muted">Movements</p>
                  </div>
                </div>

                {/* Flagged events */}
                <div>
                  <p className="font-heading text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">
                    Flagged Events
                  </p>
                  <div className="space-y-1.5 max-h-28 overflow-y-auto pr-1">
                    {flaggedEvents.map((evt: FlaggedEvent, i: number) => (
                      <div
                        key={`${evt.label}-${i}`}
                        className="flex items-start gap-2 text-[11px] font-mono"
                      >
                        <span
                          className={`shrink-0 mt-1 w-1.5 h-1.5 rounded-full ${
                            evt.severity === "danger"
                              ? "bg-danger"
                              : evt.severity === "accent"
                              ? "bg-accent"
                              : "bg-text-muted"
                          }`}
                        />
                        <span className="text-text leading-tight">
                          {evt.label}
                        </span>
                        <span className="ml-auto text-text-muted shrink-0">
                          {evt.time}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <RetroButton variant="secondary" className="w-full !text-xs !py-1.5">
                  View Details
                </RetroButton>
              </div>
            </RetroWindow>

            {/* Panel 2: Product & POS Funnel */}
            <RetroWindow title="Product & POS Funnel" className="relative">
              {/* Accent stripe */}
              <div
                className="absolute left-0 top-0 bottom-0 w-1 rounded-l-lg"
                style={{ backgroundColor: "var(--color-accent-soft)" }}
              />

              <PosDashboardPanel />
            </RetroWindow>

            {/* Panel 3: Trajectory & Heatmaps */}
            <RetroWindow title="Trajectory & Heatmaps" className="relative">
              {/* Accent stripe */}
              <div
                className="absolute left-0 top-0 bottom-0 w-1 rounded-l-lg"
                style={{ backgroundColor: "var(--color-success)" }}
              />

              <div className="space-y-4">
                {/* Icon + heading */}
                <div className="flex items-center gap-2 text-text-muted">
                  <MapPinIcon />
                  <span className="font-heading text-xs font-semibold uppercase tracking-wider">
                    Store Layout
                  </span>
                </div>

                {/* Heatmap placeholder */}
                <HeatmapPlaceholder />

                {/* Peak hour callout */}
                <div className="flex items-center gap-3 bg-surface-alt rounded-md px-3 py-2 border border-border-soft">
                  <div>
                    <p className="font-mono text-[10px] text-text-muted uppercase tracking-wider">
                      Peak Hour
                    </p>
                    <p className="font-mono text-lg font-bold text-text">
                      {summary.peakHour}
                    </p>
                  </div>
                  <div className="ml-auto text-right">
                    <p className="font-mono text-[10px] text-text-muted uppercase tracking-wider">
                      Density
                    </p>
                    <p className="font-mono text-lg font-bold text-danger">
                      {summary.density}
                    </p>
                  </div>
                </div>

                <RetroButton variant="secondary" className="w-full !text-xs !py-1.5">
                  View Details
                </RetroButton>
              </div>
            </RetroWindow>
          </div>

          <RetroCard className="mt-6 border-l-4 border-l-accent">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-heading text-sm font-semibold text-text">Compare aisle ratios</p>
                <p className="mt-1 text-sm text-text-muted">Analyze employee-to-customer ratios and optimize staff allocation.</p>
                <div className="mt-2 flex gap-4 font-mono text-[10px] text-text-muted">
                  <span>Aisle 1: {summary.employees?.aisle1 ?? 0} emp / {summary.customers?.aisle1 ?? 0} cust</span>
                  <span>Aisle 2: {summary.employees?.aisle2 ?? 0} emp / {summary.customers?.aisle2 ?? 0} cust</span>
                </div>
              </div>
              <a
                href="/compare-people"
                className="ml-4 shrink-0 rounded-md bg-accent px-4 py-2 font-heading text-sm font-semibold text-surface hover:bg-accent-hover transition-colors"
              >
                Analyze
              </a>
            </div>
          </RetroCard>
        </section>
      </main>

      {/* ── AI Agent Bar (sticky bottom) ── */}
      <AIAgentBar />
    </div>
  );
}
