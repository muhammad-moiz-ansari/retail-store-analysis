"use client";

import { FormEvent, useState } from "react";
import { RetroButton, RetroCard, RetroInput, RetroWindow } from "@/components/ui";

type Handoff = {
  status: "confirmed" | "uncertain" | "unmatched";
  master_id: string | null;
  source_event_id: string | null;
  target_event_id: string | null;
  source_track_id: string | null;
  target_track_id: string | null;
  score: number;
  evidence: { appearance_similarity?: number; time_compatibility?: number; gap_seconds?: number };
};

type Result = { handoffs: Handoff[]; processing?: { elapsed_seconds: number; appearance_method: string }; cameras?: { camera_id: string; events: unknown[]; tracks: unknown[] }[] };

const defaults = { cam1: "backend/videos/cam1.mp4", cam2: "backend/videos/cam2.mp4", sampleEvery: "5", minGap: "1", maxGap: "45", cam1Boundary: "0.85", cam2Boundary: "0.15" };

export default function CameraHandoffPage() {
  const [form, setForm] = useState(defaults);
  const [logs, setLogs] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setLogs(""); setResult(null);
    try {
      const response = await fetch("/api/camera-handoff", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
      if (!response.ok || !response.body) throw new Error((await response.json()).error || "Unable to start processing.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        const messages = buffer.split("\n\n"); buffer = messages.pop() || "";
        for (const message of messages) {
          const eventName = message.match(/^event: (.+)$/m)?.[1];
          const data = message.match(/^data: (.+)$/m)?.[1];
          if (!eventName || !data) continue;
          const payload = JSON.parse(data);
          if (eventName === "log") setLogs((current) => current + payload.text);
          if (eventName === "result") setResult(payload.data);
          if (eventName === "error") setError(payload.message);
        }
      }
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Processing failed."); }
    finally { setBusy(false); }
  }

  const handoffs = result?.handoffs ?? [];
  const count = (status: Handoff["status"]) => handoffs.filter((item) => item.status === status).length;

  return <main className="mx-auto w-full max-w-6xl px-4 py-8 md:px-8">
    <p className="font-mono text-xs uppercase tracking-[0.18em] text-accent">Identity Association</p>
    <h1 className="mt-2 font-heading text-3xl font-bold text-text">Camera Handoff</h1>
    <p className="mt-2 max-w-2xl text-sm text-text-muted">Offline directional matching for the configured transition: Camera 1 right exit to Camera 2 left entry.</p>
    <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.7fr)]">
      <RetroWindow title="Processing Configuration">
        <form onSubmit={run} className="space-y-4">
          <RetroInput label="Camera 1 video" value={form.cam1} onChange={(event) => setForm({ ...form, cam1: event.target.value })} />
          <RetroInput label="Camera 2 video" value={form.cam2} onChange={(event) => setForm({ ...form, cam2: event.target.value })} />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {(["sampleEvery", "minGap", "maxGap", "cam1Boundary", "cam2Boundary"] as const).map((key) => <RetroInput key={key} label={key} value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} />)}
          </div>
          <RetroButton type="submit" disabled={busy}>{busy ? "Processing..." : "Run Handoff Analysis"}</RetroButton>
        </form>
      </RetroWindow>
      <RetroWindow title="Association Status">
        <div className="grid grid-cols-3 gap-2 text-center">
          {(["confirmed", "uncertain", "unmatched"] as const).map((status) => <div key={status} className="border border-border-soft bg-surface-alt p-3"><p className="font-mono text-2xl font-bold text-text">{count(status)}</p><p className="font-mono text-[10px] uppercase tracking-wider text-text-muted">{status}</p></div>)}
        </div>
        {result?.processing && <p className="mt-4 text-xs text-text-muted">Completed in {result.processing.elapsed_seconds}s using {result.processing.appearance_method}.</p>}
        {error && <p className="mt-4 border border-danger bg-surface-alt p-3 text-sm text-danger">{error}</p>}
      </RetroWindow>
    </div>
    <RetroWindow title="Handoff Evidence" className="mt-6">
      {handoffs.length === 0 ? <p className="text-sm text-text-muted">Run an analysis to view directional events and identity decisions.</p> : <div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead><tr className="border-b border-border-soft font-mono uppercase tracking-wider text-text-muted"><th className="p-2">Status</th><th className="p-2">Master ID</th><th className="p-2">Tracks</th><th className="p-2">Score</th><th className="p-2">Evidence</th></tr></thead><tbody>{handoffs.map((item, index) => <tr key={`${item.source_event_id}-${item.target_event_id}-${index}`} className="border-b border-border-soft/50"><td className="p-2 font-semibold text-text">{item.status}</td><td className="p-2 font-mono text-accent">{item.master_id || "-"}</td><td className="p-2 font-mono">{item.source_track_id || "-"} → {item.target_track_id || "-"}</td><td className="p-2 font-mono">{item.score.toFixed(2)}</td><td className="p-2 text-text-muted">appearance {item.evidence.appearance_similarity?.toFixed(2) || "-"}, gap {item.evidence.gap_seconds?.toFixed(1) || "-"}s</td></tr>)}</tbody></table></div>}
    </RetroWindow>
    <RetroWindow title="Processing Log" className="mt-6"><pre className="max-h-56 overflow-auto whitespace-pre-wrap font-mono text-xs text-text-muted">{logs || "No run yet."}</pre></RetroWindow>
  </main>;
}