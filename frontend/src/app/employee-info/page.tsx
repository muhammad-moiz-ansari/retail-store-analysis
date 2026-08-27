"use client";

import React from "react";
import { RetroWindow, RetroCard } from "@/components/ui";

/* ═══════════════════════════════════════════════════════════════
   Mock data
   ═══════════════════════════════════════════════════════════════ */

const LEADERBOARD = [
  { rank: 1, id: "Staff 03", approach: 28, idle: 22, interaction: 37, total: 87 },
  { rank: 2, id: "Staff 01", approach: 26, idle: 20, interaction: 35, total: 81 },
  { rank: 3, id: "Staff 05", approach: 25, idle: 19, interaction: 33, total: 77 },
  { rank: 4, id: "Staff 02", approach: 22, idle: 17, interaction: 30, total: 69 },
  { rank: 5, id: "Staff 04", approach: 19, idle: 14, interaction: 27, total: 60 },
];

/* ═══════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════ */

function formatDate(): string {
  const d = new Date();
  return d.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/* ═══════════════════════════════════════════════════════════════
   Page
   ═══════════════════════════════════════════════════════════════ */

export default function EmployeeInfoPage() {
  return (
    <div className="bg-bg min-h-screen">
      <main className="w-full max-w-[1280px] mx-auto px-4 md:px-6 lg:px-8 py-10 md:py-16 space-y-12 md:space-y-16">
        {/* ── Page Header ── */}
        <PageHeader />

        {/* ── Section 1: Overall Staff Performance ── */}
        <OverallPerformanceSection />
      </main>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Page Header
   ═══════════════════════════════════════════════════════════════ */

function PageHeader() {
  return (
    <RetroWindow title="Employee Info — Staff Performance Today">
      <p className="font-mono text-xs text-text-muted mb-5 tracking-wide">
        {formatDate()}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatPill label="Staff on Shift" value="5" color="var(--color-accent)" />
        <StatPill label="Total Interactions" value="143" color="var(--color-accent-soft)" />
        <RetroCard className="text-center">
          <p className="font-mono text-3xl font-bold" style={{ color: "var(--color-success)" }}>
            84 / 100
          </p>
          <p className="text-xs text-text-muted mt-1">Store Score</p>
        </RetroCard>
      </div>
    </RetroWindow>
  );
}

function StatPill({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <RetroCard className="text-center">
      <p className="font-mono text-2xl font-bold" style={{ color }}>
        {value}
      </p>
      <p className="text-xs text-text-muted mt-1">{label}</p>
    </RetroCard>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 1: Overall Staff Performance
   ═══════════════════════════════════════════════════════════════ */

function OverallPerformanceSection() {
  return (
    <RetroWindow title="Overall Staff Performance">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* ── Store Performance Score Ring ── */}
        <RetroCard label="Store Performance Score" className="flex flex-col items-center justify-center py-6">
          <ScoreRing score={84} max={100} />
          <h3 className="font-heading text-sm font-bold text-text mt-4">
            Today&apos;s Store Score
          </h3>
          <p className="text-xs text-text-muted mt-1 text-center max-w-[260px]">
            Good — staff are engaging customers effectively.
          </p>
        </RetroCard>

        {/* ── Staff Leaderboard ── */}
        <RetroCard label="Staff Leaderboard">
          <div className="overflow-x-auto -mx-1">
            <table className="w-full text-xs min-w-[420px]">
              <thead>
                <tr className="bg-surface-alt border-b border-border-soft">
                  <th className="py-2 px-2 text-left font-mono uppercase text-text-muted tracking-wider">#</th>
                  <th className="py-2 px-2 text-left font-mono uppercase text-text-muted tracking-wider">Staff ID</th>
                  <th className="py-2 px-2 text-right font-mono uppercase text-text-muted tracking-wider">Approach</th>
                  <th className="py-2 px-2 text-right font-mono uppercase text-text-muted tracking-wider">Idle</th>
                  <th className="py-2 px-2 text-right font-mono uppercase text-text-muted tracking-wider">Interact.</th>
                  <th className="py-2 px-2 text-right font-mono uppercase text-text-muted tracking-wider">Total</th>
                </tr>
              </thead>
              <tbody>
                {LEADERBOARD.map((row, i) => (
                  <tr
                    key={row.id}
                    className={`border-b border-border-soft/40 ${
                      i % 2 === 0 ? "bg-surface" : "bg-bg"
                    } ${row.rank === 1 ? "border-l-3 border-l-accent-soft" : ""}`}
                  >
                    <td className="py-2 px-2 font-mono text-text-muted">{row.rank}</td>
                    <td className="py-2 px-2 font-mono text-text">{row.id}</td>
                    <td className="py-2 px-2 text-right font-mono text-text-muted">{row.approach}</td>
                    <td className="py-2 px-2 text-right font-mono text-text-muted">{row.idle}</td>
                    <td className="py-2 px-2 text-right font-mono text-text-muted">{row.interaction}</td>
                    <td className="py-2 px-2 text-right font-mono font-bold text-accent">{row.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[10px] text-text-muted mt-3 leading-relaxed">
            Scores are computed from: Approach Speed (30 pts max), Idle Time (25 pts max),
            Interaction Duration (45 pts max). Used as manager decision-support — not an
            automated verdict.
          </p>
        </RetroCard>
      </div>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Score Ring (SVG)
   ═══════════════════════════════════════════════════════════════ */

function ScoreRing({ score, max }: { score: number; max: number }) {
  const size = 160;
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = score / max;
  const dashOffset = circumference * (1 - pct);

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-border-soft)"
          strokeWidth={strokeWidth}
          strokeOpacity={0.3}
        />
        {/* Filled arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
        />
      </svg>
      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-4xl font-bold text-accent">{score}</span>
        <span className="font-mono text-sm text-text-muted">/ {max}</span>
      </div>
    </div>
  );
}
