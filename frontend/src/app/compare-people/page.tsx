"use client";

import { FormEvent, useMemo, useState } from "react";

type ComparisonResult = {
  video1: string;
  video2: string;
  frame_interval: number;
  num_samples: number;
  valid_samples: number;
  common_frames: number;
  totals: { video1: number; video2: number };
  averages: { video1: number; video2: number };
  samples: Array<{
    sample: number;
    frame: number;
    timestamp_s: number;
    v1_count: number;
    v2_count: number;
    diff: number;
    verdict: string;
  }>;
};

const defaultVideo1 = "/home/mosaq/HF_CAV_CV/ShopAssistant1cor.mp4";
const defaultVideo2 = "/home/mosaq/HF_CAV_CV/OneShopOneWait1cor.mp4";

export default function ComparePeoplePage() {
  const [video1, setVideo1] = useState(defaultVideo1);
  const [video2, setVideo2] = useState(defaultVideo2);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [outputLog, setOutputLog] = useState("");

  const summary = useMemo(() => {
    if (!result) return null;

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
    setOutputLog("");
    setResult(null);

    try {
      const response = await fetch("/api/compare-people", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video1, video2, frameInterval: 30 }),
      });

      if (!response.ok || !response.body) {
        const payload = await response.json().catch(() => ({}));
        const message = payload.error || "Comparison failed";
        setOutputLog(payload.output || message);
        throw new Error(message);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let partial = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        partial += decoder.decode(value, { stream: true });

        const chunks = partial.split("\n\n");
        partial = chunks.pop() ?? "";

        for (const chunk of chunks) {
          const lines = chunk.split("\n").filter(Boolean);
          const eventLine = lines.find((line) => line.startsWith("event:"));
          const dataLine = lines.find((line) => line.startsWith("data:"));

          if (!eventLine || !dataLine) continue;

          const event = eventLine.replace("event:", "").trim();
          const payload = JSON.parse(dataLine.replace("data:", "").trim()) as {
            text?: string;
            data?: ComparisonResult;
            message?: string;
            output?: string;
          };

          if (event === "log" && payload.text) {
            setOutputLog((prev) => `${prev}${payload.text}`);
          }

          if (event === "result" && payload.data) {
            setResult(payload.data);
          }

          if (event === "error") {
            setError(payload.message || "Comparison failed");
            setOutputLog((prev) => `${prev}${payload.output || payload.message || ""}`);
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 md:px-6">
      <div className="mb-8 space-y-3">
        <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-accent-soft">
          People count analyzer
        </p>
        <h1 className="font-heading text-3xl font-bold text-text">Compare people counts</h1>
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
        <div className="mt-6 rounded-md border border-danger/40 bg-danger/10 p-4 text-sm text-text">
          {error}
        </div>
      )}

      {outputLog && (
        <section className="mt-6 rounded-xl border border-border-soft bg-surface p-4">
          <h2 className="mb-3 font-heading text-lg font-bold text-text">Terminal output</h2>
          <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-6 text-text-muted">
            {outputLog}
          </pre>
        </section>
      )}

      {summary && (
        <section className="mt-8 space-y-6">
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

          <div className="rounded-xl border border-border-soft bg-surface p-4">
            <h2 className="mb-4 font-heading text-lg font-bold text-text">Comparison output</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-border-soft text-text-muted">
                    <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em]">Sample</th>
                    <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em]">Time (s)</th>
                    <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em]">V1</th>
                    <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em]">V2</th>
                    <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em]">Diff</th>
                    <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em]">Verdict</th>
                  </tr>
                </thead>
                <tbody>
                  {result?.samples.map((sample) => (
                    <tr key={sample.sample} className="border-b border-border-soft/70">
                      <td className="px-3 py-2 text-text">{sample.sample}</td>
                      <td className="px-3 py-2 text-text">{sample.timestamp_s.toFixed(1)}</td>
                      <td className="px-3 py-2 text-text">{sample.v1_count}</td>
                      <td className="px-3 py-2 text-text">{sample.v2_count}</td>
                      <td className={`px-3 py-2 font-semibold ${sample.diff > 0 ? "text-accent" : sample.diff < 0 ? "text-danger" : "text-text"}`}>
                        {sample.diff}
                      </td>
                      <td className="px-3 py-2 text-text-muted">{sample.verdict}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
