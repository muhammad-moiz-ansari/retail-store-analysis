"use client";

import { FormEvent, useMemo, useState } from "react";
import { CRTFrame } from "@/components/ui/CRTFrame";

type AisleData = {
  aisle: number;
  employees: number;
  customers: number;
  ratio?: number;
};

type Redistribution = {
  aisles: AisleData[];
  moves: Array<{
    from_aisle: number;
    to_aisle: number;
    count: number;
    reason: string;
  }>;
  summary: string;
};

type Sample = {
  sample: number;
  frame: number;
  timestamp_s: number;
  v1_count: number;
  v2_count: number;
  v1_aisles: AisleData[];
  v2_aisles: AisleData[];
  v1_redistribution: Redistribution;
  v2_redistribution: Redistribution;
};

type ComparisonResult = {
  video1: string;
  video2: string;
  frame_interval: number;
  num_samples: number;
  valid_samples: number;
  common_frames: number;
  totals: { video1: number; video2: number };
  averages: { video1: number; video2: number };
  final_aisles: { video1: AisleData[]; video2: AisleData[] };
  final_redistribution: { video1: Redistribution; video2: Redistribution };
  samples: Sample[];
};

const defaultVideo1 = "Camera A - Floor View";
const defaultVideo2 = "Camera B - Checkout View";

const sampleResult: ComparisonResult = {
  video1: defaultVideo1,
  video2: defaultVideo2,
  frame_interval: 30,
  num_samples: 10,
  valid_samples: 10,
  common_frames: 300,
  totals: { video1: 42, video2: 38 },
  averages: { video1: 4.2, video2: 3.8 },
  final_aisles: {
    video1: [
      { aisle: 1, employees: 12, customers: 15, ratio: 1.25 },
      { aisle: 2, employees: 8, customers: 10, ratio: 1.25 },
      { aisle: 3, employees: 10, customers: 8, ratio: 0.8 },
      { aisle: 4, employees: 6, customers: 9, ratio: 1.5 },
    ],
    video2: [
      { aisle: 1, employees: 9, customers: 12, ratio: 1.33 },
      { aisle: 2, employees: 11, customers: 9, ratio: 0.82 },
      { aisle: 3, employees: 7, customers: 11, ratio: 1.57 },
      { aisle: 4, employees: 11, customers: 6, ratio: 0.55 },
    ],
  },
  final_redistribution: {
    video1: {
      aisles: [
        { aisle: 1, employees: 12, customers: 15, ratio: 1.25 },
        { aisle: 2, employees: 8, customers: 10, ratio: 1.25 },
        { aisle: 3, employees: 11, customers: 8, ratio: 0.73 },
        { aisle: 4, employees: 5, customers: 9, ratio: 1.8 },
      ],
      moves: [
        { from_aisle: 3, to_aisle: 4, count: 1, reason: "Aisle 4 ratio (1.5) > Aisle 3 ratio (0.8)" },
      ],
      summary: "Move 1 employee from Aisle 3 to Aisle 4",
    },
    video2: {
      aisles: [
        { aisle: 1, employees: 9, customers: 12, ratio: 1.33 },
        { aisle: 2, employees: 12, customers: 9, ratio: 0.75 },
        { aisle: 3, employees: 6, customers: 11, ratio: 1.83 },
        { aisle: 4, employees: 11, customers: 6, ratio: 0.55 },
      ],
      moves: [
        { from_aisle: 4, to_aisle: 3, count: 1, reason: "Aisle 3 ratio (1.57) > Aisle 4 ratio (0.55)" },
        { from_aisle: 2, to_aisle: 1, count: 1, reason: "Aisle 1 ratio (1.33) > Aisle 2 ratio (0.82)" },
      ],
      summary: "Move 1 employee from Aisle 4 to Aisle 3, 1 from Aisle 2 to Aisle 1",
    },
  },
  samples: [
    {
      sample: 1,
      frame: 0,
      timestamp_s: 0.0,
      v1_count: 3,
      v2_count: 4,
      v1_aisles: [
        { aisle: 1, employees: 1, customers: 1 },
        { aisle: 2, employees: 0, customers: 1 },
        { aisle: 3, employees: 0, customers: 0 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v2_aisles: [
        { aisle: 1, employees: 1, customers: 2 },
        { aisle: 2, employees: 0, customers: 1 },
        { aisle: 3, employees: 0, customers: 0 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v1_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
      v2_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
    },
    {
      sample: 2,
      frame: 30,
      timestamp_s: 1.2,
      v1_count: 5,
      v2_count: 3,
      v1_aisles: [
        { aisle: 1, employees: 2, customers: 2 },
        { aisle: 2, employees: 0, customers: 1 },
        { aisle: 3, employees: 0, customers: 0 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v2_aisles: [
        { aisle: 1, employees: 1, customers: 1 },
        { aisle: 2, employees: 0, customers: 1 },
        { aisle: 3, employees: 0, customers: 0 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v1_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
      v2_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
    },
    {
      sample: 3,
      frame: 60,
      timestamp_s: 2.4,
      v1_count: 4,
      v2_count: 5,
      v1_aisles: [
        { aisle: 1, employees: 1, customers: 1 },
        { aisle: 2, employees: 0, customers: 1 },
        { aisle: 3, employees: 0, customers: 1 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v2_aisles: [
        { aisle: 1, employees: 1, customers: 2 },
        { aisle: 2, employees: 1, customers: 1 },
        { aisle: 3, employees: 0, customers: 0 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v1_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
      v2_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
    },
    {
      sample: 4,
      frame: 90,
      timestamp_s: 3.6,
      v1_count: 6,
      v2_count: 4,
      v1_aisles: [
        { aisle: 1, employees: 1, customers: 2 },
        { aisle: 2, employees: 1, customers: 1 },
        { aisle: 3, employees: 0, customers: 1 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v2_aisles: [
        { aisle: 1, employees: 1, customers: 1 },
        { aisle: 2, employees: 0, customers: 1 },
        { aisle: 3, employees: 0, customers: 1 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v1_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
      v2_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
    },
    {
      sample: 5,
      frame: 120,
      timestamp_s: 4.8,
      v1_count: 4,
      v2_count: 5,
      v1_aisles: [
        { aisle: 1, employees: 1, customers: 2 },
        { aisle: 2, employees: 0, customers: 1 },
        { aisle: 3, employees: 0, customers: 0 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v2_aisles: [
        { aisle: 1, employees: 1, customers: 1 },
        { aisle: 2, employees: 1, customers: 1 },
        { aisle: 3, employees: 0, customers: 1 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v1_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
      v2_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
    },
    {
      sample: 6,
      frame: 150,
      timestamp_s: 6.0,
      v1_count: 5,
      v2_count: 3,
      v1_aisles: [
        { aisle: 1, employees: 1, customers: 2 },
        { aisle: 2, employees: 1, customers: 0 },
        { aisle: 3, employees: 0, customers: 1 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v2_aisles: [
        { aisle: 1, employees: 1, customers: 1 },
        { aisle: 2, employees: 0, customers: 1 },
        { aisle: 3, employees: 0, customers: 0 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v1_redistribution: {
        aisles: [
          { aisle: 1, employees: 1, customers: 2, ratio: 2.0 },
          { aisle: 2, employees: 1, customers: 0, ratio: 0.0 },
          { aisle: 3, employees: 0, customers: 1, ratio: 1.0 },
          { aisle: 4, employees: 0, customers: 0, ratio: 0.0 },
        ],
        moves: [{ from_aisle: 2, to_aisle: 1, count: 1, reason: "Aisle 1 ratio (2.0) > Aisle 2 ratio (0.0)" }],
        summary: "Move 1 employee from Aisle 2 to Aisle 1",
      },
      v2_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
    },
    {
      sample: 7,
      frame: 180,
      timestamp_s: 7.2,
      v1_count: 3,
      v2_count: 6,
      v1_aisles: [
        { aisle: 1, employees: 1, customers: 1 },
        { aisle: 2, employees: 0, customers: 1 },
        { aisle: 3, employees: 0, customers: 0 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v2_aisles: [
        { aisle: 1, employees: 1, customers: 2 },
        { aisle: 2, employees: 1, customers: 1 },
        { aisle: 3, employees: 0, customers: 1 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v1_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
      v2_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
    },
    {
      sample: 8,
      frame: 210,
      timestamp_s: 8.4,
      v1_count: 6,
      v2_count: 4,
      v1_aisles: [
        { aisle: 1, employees: 1, customers: 2 },
        { aisle: 2, employees: 1, customers: 1 },
        { aisle: 3, employees: 0, customers: 1 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v2_aisles: [
        { aisle: 1, employees: 1, customers: 1 },
        { aisle: 2, employees: 0, customers: 1 },
        { aisle: 3, employees: 0, customers: 1 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v1_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
      v2_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
    },
    {
      sample: 9,
      frame: 240,
      timestamp_s: 9.6,
      v1_count: 3,
      v2_count: 2,
      v1_aisles: [
        { aisle: 1, employees: 1, customers: 1 },
        { aisle: 2, employees: 0, customers: 1 },
        { aisle: 3, employees: 0, customers: 0 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v2_aisles: [
        { aisle: 1, employees: 1, customers: 1 },
        { aisle: 2, employees: 0, customers: 0 },
        { aisle: 3, employees: 0, customers: 0 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v1_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
      v2_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
    },
    {
      sample: 10,
      frame: 270,
      timestamp_s: 10.8,
      v1_count: 3,
      v2_count: 2,
      v1_aisles: [
        { aisle: 1, employees: 1, customers: 1 },
        { aisle: 2, employees: 0, customers: 1 },
        { aisle: 3, employees: 0, customers: 0 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v2_aisles: [
        { aisle: 1, employees: 1, customers: 1 },
        { aisle: 2, employees: 0, customers: 0 },
        { aisle: 3, employees: 0, customers: 0 },
        { aisle: 4, employees: 0, customers: 0 },
      ],
      v1_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
      v2_redistribution: { aisles: [], moves: [], summary: "No redistribution needed" },
    },
  ],
};

function RatioBar({ ratio, maxRatio }: { ratio: number; maxRatio: number }) {
  const pct = maxRatio > 0 ? (ratio / maxRatio) * 100 : 0;
  const color = ratio >= 1.5 ? "bg-danger" : ratio >= 1.0 ? "bg-warning" : "bg-accent";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-16 overflow-hidden rounded-full bg-border-soft">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs text-text-muted">{ratio.toFixed(2)}</span>
    </div>
  );
}

function MoveBadge({ move }: { move: { from_aisle: number; to_aisle: number; count: number } }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-accent/30 bg-accent/10 px-2 py-1 font-mono text-[11px] text-accent">
      A{move.from_aisle} <span className="text-text-muted">&rarr;</span> A{move.to_aisle}
      <span className="ml-1 rounded bg-accent/20 px-1 font-bold">+{move.count}</span>
    </span>
  );
}

export default function ComparePeoplePage() {
  const [video1, setVideo1] = useState(defaultVideo1);
  const [video2, setVideo2] = useState(defaultVideo2);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ComparisonResult>(sampleResult);
  const [activeTab, setActiveTab] = useState<"overview" | "samples">("overview");
  const [logs, setLogs] = useState<string[]>([]);

  const summary = useMemo(() => {
    return {
      totalVideo1: result.totals.video1,
      totalVideo2: result.totals.video2,
      avgVideo1: result.averages.video1,
      avgVideo2: result.averages.video2,
      validSamples: result.valid_samples,
      commonFrames: result.common_frames,
    };
  }, [result]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setLogs([]);

    try {
      const res = await fetch("/api/compare-people", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video1, video2, frameInterval: 30 }),
      });

      if (!res.ok) {
        const json = await res.json().catch(() => null);
        throw new Error(json?.error || `Request failed (${res.status})`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let eventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const payload = JSON.parse(line.slice(6));
            if (eventType === "log") {
              setLogs((prev) => [...prev, payload.text]);
            } else if (eventType === "result") {
              setResult(payload.data);
            } else if (eventType === "error") {
              throw new Error(payload.message);
            }
          }
        }
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function renderAisleTable(aisles: AisleData[], label: string) {
    const maxRatio = Math.max(...aisles.map((a) => a.ratio ?? 0), 1);
    return (
      <div className="rounded-lg border border-border-soft bg-bg p-4">
        <h3 className="mb-3 font-heading text-sm font-semibold text-text">{label}</h3>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border-soft text-text-muted">
              <th className="pb-2 font-mono text-[10px] uppercase tracking-[0.2em]">Aisle</th>
              <th className="pb-2 font-mono text-[10px] uppercase tracking-[0.2em]">Employees</th>
              <th className="pb-2 font-mono text-[10px] uppercase tracking-[0.2em]">Customers</th>
              <th className="pb-2 font-mono text-[10px] uppercase tracking-[0.2em]">Ratio (C/E)</th>
            </tr>
          </thead>
          <tbody>
            {aisles.map((a) => (
              <tr key={a.aisle} className="border-b border-border-soft/50">
                <td className="py-2 font-semibold text-text">Aisle {a.aisle}</td>
                <td className="py-2 text-text">{a.employees}</td>
                <td className="py-2 text-text">{a.customers}</td>
                <td className="py-2">
                  <RatioBar ratio={a.ratio ?? 0} maxRatio={maxRatio} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 md:px-6">
      <div className="mb-8 space-y-3">
        <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-accent-soft">
          Staff redistribution analyzer
        </p>
        <h1 className="font-heading text-3xl font-bold text-text">Compare people counts</h1>
        <p className="max-w-2xl text-sm text-text-muted">
          Analyzes employee-to-customer ratios across aisles and recommends staff redistribution to balance coverage.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="rounded-xl border border-border-soft bg-surface p-5 shadow-[4px_4px_0_rgba(74,46,30,0.15)]">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block">
            <span className="mb-2 block font-mono text-[11px] uppercase tracking-[0.2em] text-text-muted">
              Video 1 path
            </span>
            <input
              value={video1}
              onChange={(e) => setVideo1(e.target.value)}
              className="w-full rounded-md border border-border-soft bg-bg px-3 py-2 font-mono text-sm text-text outline-none focus:border-accent"
            />
          </label>
          <label className="block">
            <span className="mb-2 block font-mono text-[11px] uppercase tracking-[0.2em] text-text-muted">
              Video 2 path
            </span>
            <input
              value={video2}
              onChange={(e) => setVideo2(e.target.value)}
              className="w-full rounded-md border border-border-soft bg-bg px-3 py-2 font-mono text-sm text-text outline-none focus:border-accent"
            />
          </label>
        </div>
        <div className="mt-5 flex items-center gap-3">
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-accent px-5 py-2.5 font-heading text-sm font-semibold text-surface disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Processing..." : "Compare videos"}
          </button>
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">
            Sampling every 30 frames
          </span>
        </div>
      </form>

      {error && (
        <div className="mt-6 rounded-md border border-danger/40 bg-danger/10 p-4 text-sm text-text">{error}</div>
      )}

      {logs.length > 0 && (
        <div className="mt-6 rounded-lg border border-border-soft bg-bg p-4">
          <h3 className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">Processing log</h3>
          <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap font-mono text-xs text-text-muted">
            {logs.join("")}
          </pre>
        </div>
      )}

      <section className="mt-8 space-y-6">
        {/* Video feeds */}
        <div className="grid gap-4 md:grid-cols-2">
          <CRTFrame label={result.video1} videoSrc="/videos/cam1.mp4" signal />
          <CRTFrame label={result.video2} videoSrc="/videos/cam2.mp4" signal />
        </div>

        {/* Tabs */}
        <div className="flex gap-1 rounded-lg border border-border-soft bg-surface p-1">
          {(["overview", "samples"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 rounded-md px-4 py-2 font-mono text-[11px] uppercase tracking-[0.2em] transition-colors ${
                activeTab === tab
                  ? "bg-accent text-surface"
                  : "text-text-muted hover:text-text"
              }`}
            >
              {tab === "overview" ? "Staff Overview" : "Sample Breakdown"}
            </button>
          ))}
        </div>

        {activeTab === "overview" && (
          <>
            {/* Summary cards */}
            <div className="grid gap-4 md:grid-cols-4">
              <div className="rounded-lg border border-border-soft bg-surface p-4">
                <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">Valid samples</div>
                <div className="mt-2 text-2xl font-bold text-text">{summary.validSamples}</div>
              </div>
              <div className="rounded-lg border border-border-soft bg-surface p-4">
                <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">Video 1 total</div>
                <div className="mt-2 text-2xl font-bold text-text">{summary.totalVideo1}</div>
              </div>
              <div className="rounded-lg border border-border-soft bg-surface p-4">
                <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">Video 2 total</div>
                <div className="mt-2 text-2xl font-bold text-text">{summary.totalVideo2}</div>
              </div>
              <div className="rounded-lg border border-border-soft bg-surface p-4">
                <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">Common frames</div>
                <div className="mt-2 text-2xl font-bold text-text">{summary.commonFrames}</div>
              </div>
            </div>

            {/* Aisle breakdown side by side */}
            <div className="grid gap-4 md:grid-cols-2">
              {renderAisleTable(result.final_aisles.video1, result.video1)}
              {renderAisleTable(result.final_aisles.video2, result.video2)}
            </div>

            {/* Redistribution verdicts */}
            <div className="grid gap-4 md:grid-cols-2">
              {(["video1", "video2"] as const).map((v) => {
                const redist = result.final_redistribution[v];
                const label = v === "video1" ? result.video1 : result.video2;
                return (
                  <div key={v} className="rounded-xl border border-border-soft bg-surface p-5">
                    <h3 className="mb-3 font-heading text-sm font-semibold text-text">
                      Redistribution &mdash; {label}
                    </h3>
                    {redist.moves.length === 0 ? (
                      <p className="rounded-md border border-accent/30 bg-accent/10 p-3 font-mono text-sm text-accent">
                        No redistribution needed
                      </p>
                    ) : (
                      <div className="space-y-3">
                        <div className="flex flex-wrap gap-2">
                          {redist.moves.map((m, i) => (
                            <MoveBadge key={i} move={m} />
                          ))}
                        </div>
                        <div className="rounded-md border border-border-soft bg-bg p-3 font-mono text-xs text-text-muted">
                          {redist.summary}
                        </div>
                        <div className="space-y-2">
                          {redist.moves.map((m, i) => (
                            <div key={i} className="flex items-start gap-2 text-xs text-text-muted">
                              <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                              {m.reason}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}

        {activeTab === "samples" && (
          <div className="rounded-xl border border-border-soft bg-surface p-4">
            <h2 className="mb-4 font-heading text-lg font-bold text-text">Per-sample breakdown</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-border-soft text-text-muted">
                    <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em]">#</th>
                    <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em]">Time</th>
                    <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em]">V1 Aisles (E/C)</th>
                    <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em]">V2 Aisles (E/C)</th>
                    <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em]">V1 Verdict</th>
                    <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em]">V2 Verdict</th>
                  </tr>
                </thead>
                <tbody>
                  {result.samples.map((s) => (
                    <tr key={s.sample} className="border-b border-border-soft/70">
                      <td className="px-3 py-2 text-text">{s.sample}</td>
                      <td className="px-3 py-2 text-text">{s.timestamp_s.toFixed(1)}s</td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {s.v1_aisles.filter((a) => a.employees + a.customers > 0).map((a) => (
                            <span key={a.aisle} className="inline-flex gap-0.5 rounded bg-border-soft/50 px-1.5 py-0.5 font-mono text-[10px] text-text-muted">
                              A{a.aisle}:<span className="text-accent">{a.employees}e</span>/<span className="text-text">{a.customers}c</span>
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {s.v2_aisles.filter((a) => a.employees + a.customers > 0).map((a) => (
                            <span key={a.aisle} className="inline-flex gap-0.5 rounded bg-border-soft/50 px-1.5 py-0.5 font-mono text-[10px] text-text-muted">
                              A{a.aisle}:<span className="text-accent">{a.employees}e</span>/<span className="text-text">{a.customers}c</span>
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        {s.v1_redistribution.moves.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {s.v1_redistribution.moves.map((m, i) => (
                              <MoveBadge key={i} move={m} />
                            ))}
                          </div>
                        ) : (
                          <span className="font-mono text-[11px] text-accent">Balanced</span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        {s.v2_redistribution.moves.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {s.v2_redistribution.moves.map((m, i) => (
                              <MoveBadge key={i} move={m} />
                            ))}
                          </div>
                        ) : (
                          <span className="font-mono text-[11px] text-accent">Balanced</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
