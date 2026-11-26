"use client";

import { FormEvent, useMemo, useState } from "react";
import { runBackendJob } from "@/lib/backend-job";
import { ManagerHeader, ManagerPage, ManagerPanel, ManagerTable } from "@/components/ui/ManagerLayout";

type ComparisonResult = {
  video1: string;
  video2: string;
  frame_interval: number;
  num_samples: number;
  valid_samples: number;
  common_frames: number;
  count_mode?: string;
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

const defaultVideo1 = "backend/videos/cam1.mp4";
const defaultVideo2 = "backend/videos/cam2.mp4";

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
      const job = await runBackendJob<ComparisonResult>(
        "compare-people",
        "jobs",
        { video1, video2, frame_interval: 30 },
        (update) => setOutputLog(update.logs.join("\n")),
      );
      setResult(job.result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <ManagerPage>
      <ManagerHeader title="Compare people counts">
        <p>Compare counts from two recordings at matching sampled times.</p>
      </ManagerHeader>

      <ManagerPanel title="Video sources">
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="mb-2 block font-mono text-[11px] uppercase tracking-[0.2em] text-text-muted">
                Video 1 path
              </span>
              <input
                value={video1}
                onChange={(e) => setVideo1(e.target.value)}
                className="min-h-11 w-full rounded-lg border border-border-soft bg-surface px-3 py-2 font-mono text-sm"
              />
            </label>

            <label className="block">
              <span className="mb-2 block font-mono text-[11px] uppercase tracking-[0.2em] text-text-muted">
                Video 2 path
              </span>
              <input
                value={video2}
                onChange={(e) => setVideo2(e.target.value)}
                className="min-h-11 w-full rounded-lg border border-border-soft bg-surface px-3 py-2 font-mono text-sm"
              />
            </label>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={loading}
              className="min-h-11 rounded-lg bg-accent px-5 py-2.5 font-heading text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Processing..." : "Compare videos"}
            </button>
            <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">
              Sampling every 30 frames
            </span>
          </div>
        </form>
      </ManagerPanel>

      {error && (
        <div role="alert" className="rounded-lg border border-danger/40 bg-danger/10 p-4 text-sm text-danger">
          {error}
        </div>
      )}

      {outputLog && (
        <ManagerPanel title="Terminal output">
          <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-6 text-text-muted">
            {outputLog}
          </pre>
        </ManagerPanel>
      )}

      {summary && (
        <section aria-label="Comparison results" className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <div className="workspace-card rounded-lg border border-border-soft bg-surface p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">Mode</div>
              <div className="mt-2 text-xl font-bold [overflow-wrap:anywhere]">{result?.count_mode ?? "ratio_verdict"}</div>
            </div>
            <div className="workspace-card rounded-lg border border-border-soft bg-surface p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">Valid samples</div>
              <div className="mt-2 text-2xl font-bold text-text">{summary.validSamples}</div>
            </div>
            <div className="workspace-card rounded-lg border border-border-soft bg-surface p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">Video 1 total</div>
              <div className="mt-2 text-2xl font-bold text-text">{summary.totalVideo1}</div>
            </div>
            <div className="workspace-card rounded-lg border border-border-soft bg-surface p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">Video 2 total</div>
              <div className="mt-2 text-2xl font-bold text-text">{summary.totalVideo2}</div>
            </div>
            <div className="workspace-card rounded-lg border border-border-soft bg-surface p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted">Common frames</div>
              <div className="mt-2 text-2xl font-bold text-text">{summary.commonFrames}</div>
            </div>
          </div>

          <ManagerPanel title="Comparison output">
            <ManagerTable label="Sample-by-sample results">
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
            </ManagerTable>
          </ManagerPanel>
        </section>
      )}
    </ManagerPage>
  );
}
