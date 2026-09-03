"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { CRTFrame } from "@/components/ui/CRTFrame";

type Person = {
  bbox: [number, number, number, number];
  center: [number, number];
  confidence: number;
};

type InteractionAnalysis = {
  status: string;
  message: string;
  score: number;
  employee_count?: number;
  customer_count?: number;
  ratio?: number;
  interacting_count?: number;
};

type FrameResult = {
  aisle: string;
  total_people: number;
  employees: Person[];
  employee_count: number;
  customers: Person[];
  customer_count: number;
  interaction: InteractionAnalysis;
};

function computeRatio(emp: number, cust: number): string {
  if (cust === 0) return emp > 0 ? `${emp}:0 (idle)` : "0:0";
  const gcd = (a: number, b: number): number => (b === 0 ? a : gcd(b, a % b));
  const g = gcd(emp, cust);
  return `${emp / g}:${cust / g}`;
}

function InteractionBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    good: "bg-success/20 text-success border-success/40",
    partial: "bg-accent/20 text-accent border-accent/40",
    overwhelmed: "bg-danger/20 text-danger border-danger/40",
    not_interacting: "bg-danger/20 text-danger border-danger/40",
    idle: "bg-surface-alt text-text-muted border-border-soft",
    unattended: "bg-danger/20 text-danger border-danger/40",
    empty: "bg-surface-alt text-text-muted border-border-soft",
  };
  const labels: Record<string, string> = {
    good: "Active",
    partial: "Partial",
    overwhelmed: "Overwhelmed",
    not_interacting: "No Contact",
    idle: "Idle",
    unattended: "Unattended",
    empty: "Empty",
  };
  return (
    <span className={`inline-block rounded border px-2 py-0.5 font-mono text-[10px] font-semibold ${styles[status] || styles.empty}`}>
      {labels[status] || status}
    </span>
  );
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? "var(--color-success)" : score >= 40 ? "var(--color-accent)" : "var(--color-danger)";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 rounded-full bg-surface-alt border border-border-soft overflow-hidden">
        <div className="h-full rounded-full transition-all duration-300" style={{ width: `${score}%`, backgroundColor: color }} />
      </div>
      <span className="font-mono text-[10px] text-text-muted w-8 text-right">{score}%</span>
    </div>
  );
}

export default function ComparePeoplePage() {
  const [video1Src, setVideo1Src] = useState("");
  const [video2Src, setVideo2Src] = useState("");
  const [video1Name, setVideo1Name] = useState("Aisle 1");
  const [video2Name, setVideo2Name] = useState("Aisle 2");
  const [analyzing, setAnalyzing] = useState(false);
  const [aisle1, setAisle1] = useState<FrameResult | null>(null);
  const [aisle2, setAisle2] = useState<FrameResult | null>(null);
  const [lastUpdate, setLastUpdate] = useState("");
  const [error, setError] = useState("");

  const video1Ref = useRef<HTMLVideoElement | null>(null);
  const video2Ref = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>, side: "v1" | "v2") {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    if (side === "v1") {
      setVideo1Src(url);
      setVideo1Name(file.name.replace(/\.[^.]+$/, ""));
    } else {
      setVideo2Src(url);
      setVideo2Name(file.name.replace(/\.[^.]+$/, ""));
    }
  }

  // Find the actual <video> elements rendered by CRTFrame
  const findVideoElements = useCallback(() => {
    const videos = document.querySelectorAll("video");
    // CRTFrame renders video elements in order; we need the ones matching our sources
    let v1: HTMLVideoElement | null = null;
    let v2: HTMLVideoElement | null = null;
    videos.forEach((v) => {
      const src = v.querySelector("source")?.getAttribute("src") || v.src;
      if (src === video1Src) v1 = v;
      if (src === video2Src) v2 = v;
    });
    video1Ref.current = v1;
    video2Ref.current = v2;
  }, [video1Src, video2Src]);

  useEffect(() => {
    findVideoElements();
  }, [findVideoElements, video1Src, video2Src]);

  async function captureFrame(video: HTMLVideoElement): Promise<string | null> {
    const canvas = canvasRef.current;
    if (!canvas || video.readyState < 2) return null;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 360;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.6).split(",")[1];
  }

  async function analyzeBoth() {
    const v1 = video1Ref.current;
    const v2 = video2Ref.current;
    if (!v1 || !v2) return;

    const [frame1, frame2] = await Promise.all([captureFrame(v1), captureFrame(v2)]);
    if (!frame1 && !frame2) return;

    const requests: Promise<{ aisle: string; data: FrameResult }>[] = [];
    if (frame1) {
      requests.push(
        fetch("/api/analyze-frame", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ frame: frame1, aisle: "aisle1" }),
        }).then((r) => r.json()).then((data) => ({ aisle: "aisle1", data }))
      );
    }
    if (frame2) {
      requests.push(
        fetch("/api/analyze-frame", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ frame: frame2, aisle: "aisle2" }),
        }).then((r) => r.json()).then((data) => ({ aisle: "aisle2", data }))
      );
    }

    const results = await Promise.all(requests);
    for (const { aisle, data } of results) {
      if ("error" in data) {
        setError((data as { error: string }).error);
        continue;
      }
      if (aisle === "aisle1") setAisle1(data as FrameResult);
      else setAisle2(data as FrameResult);
    }

    const now = new Date();
    setLastUpdate(`${now.getHours()}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`);
  }

  function toggleAnalysis() {
    if (analyzing) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = null;
      setAnalyzing(false);
    } else {
      setAnalyzing(true);
      analyzeBoth(); // immediate first run
      intervalRef.current = setInterval(analyzeBoth, 500);
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  // Compute combined stats
  const v1Emp = aisle1?.employee_count ?? 0;
  const v1Cust = aisle1?.customer_count ?? 0;
  const v2Emp = aisle2?.employee_count ?? 0;
  const v2Cust = aisle2?.customer_count ?? 0;
  const needsMovement = v1Emp > 0 && v1Cust === 0 && v2Cust > v2Emp;
  const movementVerdict = needsMovement
    ? `Move 1 employee from Aisle 1 to Aisle 2 (Aisle 2 has ${v2Cust} customers, only ${v2Emp} staff)`
    : v2Emp > 0 && v2Cust === 0 && v1Cust > v1Emp
    ? `Move 1 employee from Aisle 2 to Aisle 1 (Aisle 1 has ${v1Cust} customers, only ${v1Emp} staff)`
    : "Staffing looks balanced";

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 md:px-6">
      <canvas ref={canvasRef} className="hidden" />

      <div className="mb-8 space-y-3">
        <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-accent-soft">
          Real-time staff analysis
        </p>
        <h1 className="font-heading text-3xl font-bold text-text">Live Aisle Comparison</h1>
        <p className="text-sm text-text-muted">
          Select two videos, then start analysis. Frames are captured every 500ms and analyzed with YOLO.
        </p>
      </div>

      {/* File inputs */}
      <div className="rounded-xl border border-border-soft bg-surface p-5 shadow-[4px_4px_0_rgba(74,46,30,0.15)]">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <span className="mb-2 block font-mono text-[11px] uppercase tracking-[0.2em] text-text-muted">
              Aisle 1 video
            </span>
            <input
              type="file"
              accept="video/*"
              onChange={(e) => handleFileSelect(e, "v1")}
              className="w-full rounded-md border border-border-soft bg-bg px-3 py-2 font-mono text-sm text-text file:mr-3 file:rounded file:border-0 file:bg-accent file:px-3 file:py-1 file:text-surface file:font-heading file:text-xs file:cursor-pointer"
            />
            {video1Src && <p className="mt-1 font-mono text-[10px] text-accent">Loaded: {video1Name}</p>}
          </div>
          <div>
            <span className="mb-2 block font-mono text-[11px] uppercase tracking-[0.2em] text-text-muted">
              Aisle 2 video
            </span>
            <input
              type="file"
              accept="video/*"
              onChange={(e) => handleFileSelect(e, "v2")}
              className="w-full rounded-md border border-border-soft bg-bg px-3 py-2 font-mono text-sm text-text file:mr-3 file:rounded file:border-0 file:bg-accent file:px-3 file:py-1 file:text-surface file:font-heading file:text-xs file:cursor-pointer"
            />
            {video2Src && <p className="mt-1 font-mono text-[10px] text-accent">Loaded: {video2Name}</p>}
          </div>
        </div>

        <div className="mt-5 flex items-center gap-3">
          <button
            onClick={toggleAnalysis}
            disabled={!video1Src || !video2Src}
            className={`rounded-md px-5 py-2.5 font-heading text-sm font-semibold text-surface disabled:cursor-not-allowed disabled:opacity-60 ${
              analyzing ? "bg-danger hover:bg-danger/80" : "bg-accent hover:bg-accent-hover"
            }`}
          >
            {analyzing ? "Stop Analysis" : "Start Analysis"}
          </button>
          {analyzing && (
            <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-accent-soft">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
              </span>
              Live — updating every 500ms
            </span>
          )}
          {lastUpdate && (
            <span className="ml-auto font-mono text-[10px] text-text-muted">Last: {lastUpdate}</span>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-md border border-danger/40 bg-danger/10 p-3 text-sm text-text">
          {error}
        </div>
      )}

      {/* Video feeds with live overlay */}
      <section className="mt-8 space-y-6">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <CRTFrame
              label={`AISLE 1 — ${video1Name}`}
              videoSrc={video1Src || undefined}
              signal={!!video1Src}
              live={analyzing}
            />
            {aisle1 && (
              <div className="mt-2 rounded-lg border border-border-soft bg-surface p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-xs font-bold text-text">Aisle 1</span>
                  <InteractionBadge status={aisle1.interaction.status} />
                </div>
                <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
                  <div>
                    <span className="text-accent">Employees:</span>{" "}
                    <span className="font-bold text-text">{aisle1.employee_count}</span>
                  </div>
                  <div>
                    <span className="text-accent-soft">Customers:</span>{" "}
                    <span className="font-bold text-text">{aisle1.customer_count}</span>
                  </div>
                </div>
                <p className="mt-1 font-mono text-[10px] text-text-muted">{aisle1.interaction.message}</p>
                <div className="mt-2">
                  <ScoreBar score={aisle1.interaction.score} />
                </div>
              </div>
            )}
          </div>
          <div>
            <CRTFrame
              label={`AISLE 2 — ${video2Name}`}
              videoSrc={video2Src || undefined}
              signal={!!video2Src}
              live={analyzing}
            />
            {aisle2 && (
              <div className="mt-2 rounded-lg border border-border-soft bg-surface p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-xs font-bold text-text">Aisle 2</span>
                  <InteractionBadge status={aisle2.interaction.status} />
                </div>
                <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
                  <div>
                    <span className="text-accent">Employees:</span>{" "}
                    <span className="font-bold text-text">{aisle2.employee_count}</span>
                  </div>
                  <div>
                    <span className="text-accent-soft">Customers:</span>{" "}
                    <span className="font-bold text-text">{aisle2.customer_count}</span>
                  </div>
                </div>
                <p className="mt-1 font-mono text-[10px] text-text-muted">{aisle2.interaction.message}</p>
                <div className="mt-2">
                  <ScoreBar score={aisle2.interaction.score} />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Ratio comparison */}
        {(aisle1 || aisle2) && (
          <div className="rounded-xl border border-border-soft bg-surface p-5">
            <h2 className="mb-4 font-heading text-lg font-bold text-text">Ratio Comparison</h2>
            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-1">
                <div className="flex justify-between items-baseline">
                  <span className="font-mono text-xs text-text font-semibold">Aisle 1</span>
                  <span className="font-mono text-[10px] text-text-muted">{computeRatio(v1Emp, v1Cust)}</span>
                </div>
                <div className="h-4 rounded-sm bg-surface-alt border border-border-soft overflow-hidden flex">
                  <div className="h-full transition-all duration-300" style={{ width: v1Emp + v1Cust > 0 ? `${(v1Emp / (v1Emp + v1Cust)) * 100}%` : "0%", backgroundColor: "var(--color-accent)" }} />
                  <div className="h-full transition-all duration-300" style={{ width: v1Emp + v1Cust > 0 ? `${(v1Cust / (v1Emp + v1Cust)) * 100}%` : "0%", backgroundColor: "var(--color-accent-soft)" }} />
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between items-baseline">
                  <span className="font-mono text-xs text-text font-semibold">Aisle 2</span>
                  <span className="font-mono text-[10px] text-text-muted">{computeRatio(v2Emp, v2Cust)}</span>
                </div>
                <div className="h-4 rounded-sm bg-surface-alt border border-border-soft overflow-hidden flex">
                  <div className="h-full transition-all duration-300" style={{ width: v2Emp + v2Cust > 0 ? `${(v2Emp / (v2Emp + v2Cust)) * 100}%` : "0%", backgroundColor: "var(--color-accent)" }} />
                  <div className="h-full transition-all duration-300" style={{ width: v2Emp + v2Cust > 0 ? `${(v2Cust / (v2Emp + v2Cust)) * 100}%` : "0%", backgroundColor: "var(--color-accent-soft)" }} />
                </div>
              </div>
            </div>
            <div className="mt-4 rounded-md bg-surface-alt border border-border-soft p-3">
              <p className="font-mono text-xs text-text">
                <span className="text-accent font-bold">Movement verdict:</span> {movementVerdict}
              </p>
            </div>
          </div>
        )}

        {/* Interaction Analysis panel */}
        {(aisle1 || aisle2) && (
          <div className="rounded-xl border border-border-soft bg-surface p-5">
            <h2 className="mb-4 font-heading text-lg font-bold text-text">Interaction Analysis</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {aisle1 && (
                <div className="rounded-lg bg-surface-alt border border-border-soft p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-text">Aisle 1</span>
                    <InteractionBadge status={aisle1.interaction.status} />
                  </div>
                  <ScoreBar score={aisle1.interaction.score} />
                  <div className="space-y-1 font-mono text-[11px]">
                    <div className="flex justify-between">
                      <span className="text-text-muted">Employees present</span>
                      <span className="text-accent font-bold">{aisle1.employee_count}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Customers present</span>
                      <span className="text-accent-soft font-bold">{aisle1.customer_count}</span>
                    </div>
                    {aisle1.interaction.ratio !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-text-muted">Customer:Employee ratio</span>
                        <span className="text-text font-bold">{aisle1.interaction.ratio}:1</span>
                      </div>
                    )}
                    {aisle1.interaction.interacting_count !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-text-muted">Employees near customers</span>
                        <span className="text-text font-bold">{aisle1.interaction.interacting_count}/{aisle1.employee_count}</span>
                      </div>
                    )}
                  </div>
                  <p className="font-mono text-[10px] text-text-muted leading-relaxed">{aisle1.interaction.message}</p>
                </div>
              )}
              {aisle2 && (
                <div className="rounded-lg bg-surface-alt border border-border-soft p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-text">Aisle 2</span>
                    <InteractionBadge status={aisle2.interaction.status} />
                  </div>
                  <ScoreBar score={aisle2.interaction.score} />
                  <div className="space-y-1 font-mono text-[11px]">
                    <div className="flex justify-between">
                      <span className="text-text-muted">Employees present</span>
                      <span className="text-accent font-bold">{aisle2.employee_count}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Customers present</span>
                      <span className="text-accent-soft font-bold">{aisle2.customer_count}</span>
                    </div>
                    {aisle2.interaction.ratio !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-text-muted">Customer:Employee ratio</span>
                        <span className="text-text font-bold">{aisle2.interaction.ratio}:1</span>
                      </div>
                    )}
                    {aisle2.interaction.interacting_count !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-text-muted">Employees near customers</span>
                        <span className="text-text font-bold">{aisle2.interaction.interacting_count}/{aisle2.employee_count}</span>
                      </div>
                    )}
                  </div>
                  <p className="font-mono text-[10px] text-text-muted leading-relaxed">{aisle2.interaction.message}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
