"use client";

import { ChangeEvent, FormEvent, useState } from "react";
import { RetroButton, RetroInput, RetroWindow } from "@/components/ui";
import { runBackendJob } from "@/lib/backend-job";

type Interaction = {
  employee_track_id: number;
  customer_track_id: number;
  started_at: number;
  last_seen_at: number;
  duration_seconds: number;
  distance_body_heights: number;
  verdict?: string;
};

type Person = { track_id: number; role: "employee" | "customer"; first_seen: number; last_seen: number; frames_observed: number; employee_score: number };

type Result = { video: string; output: string; interactions: Interaction[]; people: Person[] };

type FrameCheck = { total_people: number; employee_count: number; customer_count: number; interaction: { status: string; message: string; score: number } };

const defaults = { video: "backend/videos/ShopAssistant1cor.mp4", judge: "pose", every: "1", trackEvery: "1" };

export default function InteractionsPage() {
  const [form, setForm] = useState(defaults);
  const [logs, setLogs] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [frame, setFrame] = useState<FrameCheck | null>(null);
  const [frameError, setFrameError] = useState("");
  const [frameBusy, setFrameBusy] = useState(false);

  async function checkFrame(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setFrameBusy(true); setFrameError(""); setFrame(null);
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = () => reject(new Error("Could not read the image."));
        reader.readAsDataURL(file);
      });
      const response = await fetch("/api/backend/analyze-frame", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64: dataUrl.split(",")[1], aisle: file.name }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || data.error || "Frame analysis failed.");
      setFrame(data);
    } catch (caught) { setFrameError(caught instanceof Error ? caught.message : "Frame analysis failed."); }
    finally { setFrameBusy(false); event.target.value = ""; }
  }

  async function run(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setLogs(""); setResult(null);
    try {
      const body = { video: form.video, judge: form.judge, every: Number(form.every), track_every: Number(form.trackEvery) };
      const job = await runBackendJob<Result>("interaction/runs", "jobs", body, (update) => setLogs(update.logs.join("\n")));
      setResult(job.result);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Processing failed."); }
    finally { setBusy(false); }
  }

  const people = result?.people ?? [];
  const interactions = result?.interactions ?? [];
  const count = (role: Person["role"]) => people.filter((person) => person.role === role).length;

  return <main className="mx-auto w-full max-w-6xl px-4 py-8 md:px-8">
    <p className="font-mono text-xs uppercase tracking-[0.18em] text-accent">Engagement Tracking</p>
    <h1 className="mt-2 font-heading text-3xl font-bold text-text">Interactions</h1>
    <p className="mt-2 max-w-2xl text-sm text-text-muted">Detect, track and classify people in a recording, then find employee-customer interactions confirmed by the pose judge.</p>
    <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.7fr)]">
      <RetroWindow title="Processing Configuration">
        <form onSubmit={run} className="space-y-4">
          <RetroInput label="Video (inside the project)" value={form.video} onChange={(event) => setForm({ ...form, video: event.target.value })} />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <label className="flex flex-col gap-1 text-sm font-medium text-text">
              Judge
              <select value={form.judge} onChange={(event) => setForm({ ...form, judge: event.target.value })} className="border border-border-soft bg-surface px-3 py-2 text-sm text-text">
                <option value="pose">pose</option>
                <option value="off">off</option>
              </select>
            </label>
            <RetroInput label="Score every Nth frame" value={form.every} onChange={(event) => setForm({ ...form, every: event.target.value })} />
            <RetroInput label="Track every Nth frame" value={form.trackEvery} onChange={(event) => setForm({ ...form, trackEvery: event.target.value })} />
          </div>
          <RetroButton type="submit" disabled={busy}>{busy ? "Processing..." : "Run Interaction Analysis"}</RetroButton>
        </form>
      </RetroWindow>
      <RetroWindow title="Run Summary">
        <div className="grid grid-cols-3 gap-2 text-center">
          {([["employees", count("employee")], ["customers", count("customer")], ["interactions", interactions.length]] as const).map(([label, value]) => <div key={label} className="border border-border-soft bg-surface-alt p-3"><p className="font-mono text-2xl font-bold text-text">{value}</p><p className="font-mono text-[10px] uppercase tracking-wider text-text-muted">{label}</p></div>)}
        </div>
        {result && <p className="mt-4 break-all text-xs text-text-muted">Annotated video written to {result.output}</p>}
        {error && <p className="mt-4 border border-danger bg-surface-alt p-3 text-sm text-danger">{error}</p>}
      </RetroWindow>
    </div>
    <RetroWindow title="Single Frame Check" className="mt-6">
      <label className="flex flex-col gap-2 text-sm font-medium text-text">
        Upload a still image for a quick person count and staffing check
        <input type="file" accept="image/*" onChange={checkFrame} disabled={frameBusy} className="text-sm text-text-muted" />
      </label>
      {frameBusy && <p className="mt-3 text-sm text-text-muted">Analyzing frame...</p>}
      {frameError && <p className="mt-3 border border-danger bg-surface-alt p-3 text-sm text-danger">{frameError}</p>}
      {frame && <p className="mt-3 text-sm text-text"><span className="font-mono">{frame.total_people}</span> people (<span className="font-mono">{frame.employee_count}</span> staff, <span className="font-mono">{frame.customer_count}</span> customers): <span className="font-semibold">{frame.interaction.status}</span>. {frame.interaction.message}</p>}
    </RetroWindow>
    <RetroWindow title="Confirmed Interactions" className="mt-6">
      {interactions.length === 0 ? <p className="text-sm text-text-muted">{result ? "No confirmed interactions in this recording." : "Run an analysis to view interactions."}</p> : <div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead><tr className="border-b border-border-soft font-mono uppercase tracking-wider text-text-muted"><th className="p-2">Employee</th><th className="p-2">Customer</th><th className="p-2">Window</th><th className="p-2">Duration</th><th className="p-2">Distance</th><th className="p-2">Verdict</th></tr></thead><tbody>{interactions.map((item) => <tr key={`${item.employee_track_id}-${item.customer_track_id}-${item.started_at}`} className="border-b border-border-soft/50"><td className="p-2 font-mono text-accent">#{item.employee_track_id}</td><td className="p-2 font-mono">#{item.customer_track_id}</td><td className="p-2 font-mono">{item.started_at.toFixed(1)}s → {item.last_seen_at.toFixed(1)}s</td><td className="p-2 font-mono">{item.duration_seconds.toFixed(1)}s</td><td className="p-2 font-mono">{item.distance_body_heights.toFixed(2)} bh</td><td className="p-2 font-semibold text-text">{item.verdict || "-"}</td></tr>)}</tbody></table></div>}
    </RetroWindow>
    <RetroWindow title="Tracked People" className="mt-6">
      {people.length === 0 ? <p className="text-sm text-text-muted">No people yet.</p> : <div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead><tr className="border-b border-border-soft font-mono uppercase tracking-wider text-text-muted"><th className="p-2">Track</th><th className="p-2">Role</th><th className="p-2">Seen</th><th className="p-2">Frames</th><th className="p-2">Employee score</th></tr></thead><tbody>{people.map((person) => <tr key={person.track_id} className="border-b border-border-soft/50"><td className="p-2 font-mono text-accent">#{person.track_id}</td><td className="p-2 font-semibold text-text">{person.role}</td><td className="p-2 font-mono">{person.first_seen.toFixed(1)}s → {person.last_seen.toFixed(1)}s</td><td className="p-2 font-mono">{person.frames_observed}</td><td className="p-2 font-mono">{person.employee_score.toFixed(2)}</td></tr>)}</tbody></table></div>}
    </RetroWindow>
    <RetroWindow title="Processing Log" className="mt-6"><pre className="max-h-56 overflow-auto whitespace-pre-wrap font-mono text-xs text-text-muted">{logs || "No run yet."}</pre></RetroWindow>
  </main>;
}
