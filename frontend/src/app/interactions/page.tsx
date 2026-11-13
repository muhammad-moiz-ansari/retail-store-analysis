"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { RetroButton, RetroInput } from "@/components/ui";
import { ManagerPage, ManagerHeader, ManagerPanel, ManagerTable } from "@/components/ui/ManagerLayout";
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

type Person = { track_id: number; role: "employee" | "customer" | "unknown"; first_seen: number; last_seen: number; frames_observed: number; employee_score: number };

type Result = { video: string; output: string; interactions: Interaction[]; people: Person[] };

type FrameCheck = { total_people: number; employee_count: number; customer_count: number; interaction: { status: string; message: string; score: number } };

const defaults = { video: "backend/videos/ShopAssistant1cor.mp4", judge: "pose", every: "1", trackEvery: "1", host: "", port: "4747", resolution: "640x480" };

export default function InteractionsPage() {
  const [form, setForm] = useState(defaults);
  const [logs, setLogs] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [frame, setFrame] = useState<FrameCheck | null>(null);
  const [frameError, setFrameError] = useState("");
  const [frameBusy, setFrameBusy] = useState(false);
  const [source, setSource] = useState<"recording" | "live">("recording");
  const [liveId, setLiveId] = useState("");
  const [previewReady, setPreviewReady] = useState(false);
  const [stopping, setStopping] = useState(false);

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
    setBusy(true); setError(""); setLogs(""); setResult(null); setLiveId(""); setPreviewReady(false); setStopping(false);
    try {
      const job = source === "live"
        ? await runBackendJob<Result>("interaction/live", "jobs",
          { host: form.host, port: Number(form.port), resolution: form.resolution, judge: form.judge, every: Number(form.every) },
          (update) => { setLiveId(update.id); setLogs(update.logs.join("\n")); })
        : await runBackendJob<Result>("interaction/runs", "jobs",
          { video: form.video, judge: form.judge, every: Number(form.every), track_every: Number(form.trackEvery) },
          (update) => setLogs(update.logs.join("\n")));
      setResult(job.result);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Processing failed."); }
    finally { setBusy(false); setLiveId(""); }
  }

  // Leaving the page must not keep the phone and CPU busy; a beacon still goes out while the tab closes.
  useEffect(() => {
    if (!liveId) return;
    const stop = () => navigator.sendBeacon(`/api/backend/interaction/live/${liveId}/stop`);
    window.addEventListener("pagehide", stop);
    // Also on unmount (navigating away in-app); stopping a run that already ended is a no-op.
    return () => { window.removeEventListener("pagehide", stop); stop(); };
  }, [liveId]);

  async function stopLive() {
    setStopping(true);
    const response = await fetch(`/api/backend/interaction/live/${liveId}/stop`, { method: "POST" });
    if (!response.ok) { setStopping(false); setError("Could not stop the live run."); }
  }

  const people = result?.people ?? [];
  const interactions = result?.interactions ?? [];
  const count = (role: Person["role"]) => people.filter((person) => person.role === role).length;

  return <ManagerPage>
    <ManagerHeader title="Interactions"><p>Detect, track and classify people in a recording or a live DroidCam feed, then find employee-customer interactions confirmed by the pose judge.</p></ManagerHeader>
    <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <ManagerPanel title="Processing Configuration">
        <form onSubmit={run} className="space-y-4">
          <fieldset disabled={busy}>
            <legend className="mb-2 text-sm font-semibold">Source</legend>
            <div className="flex flex-wrap gap-2">
              {([["recording", "Recording"], ["live", "Live DroidCam"]] as const).map(([value, label]) => (
                <label key={value}>
                  <input type="radio" name="interaction-source" value={value} checked={source === value}
                    onChange={() => setSource(value)} className="peer sr-only" />
                  <span className="flex min-h-11 cursor-pointer items-center rounded-lg border border-border-soft px-3 text-sm font-semibold peer-checked:border-accent peer-checked:bg-surface-alt peer-checked:text-accent peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent peer-disabled:cursor-not-allowed peer-disabled:opacity-60">{label}</span>
                </label>
              ))}
            </div>
          </fieldset>
          {source === "recording" ? <RetroInput label="Video (inside the project)" value={form.video} onChange={(event) => setForm({ ...form, video: event.target.value })} /> : <>
            <div className="grid grid-cols-[minmax(0,1fr)_7rem] gap-3">
              <RetroInput label="Phone IP (shown in the DroidCam app)" placeholder="192.168.1.20" value={form.host} onChange={(event) => setForm({ ...form, host: event.target.value })} />
              <RetroInput label="Port" value={form.port} onChange={(event) => setForm({ ...form, port: event.target.value })} />
            </div>
            <label className="flex flex-col gap-1 text-sm font-medium text-text">
              Resolution
              <select value={form.resolution} onChange={(event) => setForm({ ...form, resolution: event.target.value })} className="border border-border-soft bg-surface px-3 py-2 text-sm text-text">
                <option value="">Phone default</option>
                <option value="1280x720">1280x720</option>
                <option value="640x480">640x480 (faster)</option>
                <option value="320x240">320x240 (fastest, less accurate)</option>
                <option value="480x480">480x480 square (centre crop)</option>
                <option value="240x240">240x240 square (centre crop)</option>
              </select>
            </label>
            <p className="text-xs text-text-muted">Phone and computer on the same Wi-Fi; close the DroidCam PC client first, since the phone serves one viewer at a time.</p>
          </>}
          <div className={`grid grid-cols-1 gap-3 ${source === "recording" ? "sm:grid-cols-3" : "sm:grid-cols-2"}`}>
            <label className="flex flex-col gap-1 text-sm font-medium text-text">
              Judge
              <select value={form.judge} onChange={(event) => setForm({ ...form, judge: event.target.value })} className="border border-border-soft bg-surface px-3 py-2 text-sm text-text">
                <option value="pose">pose</option>
                <option value="off">off</option>
              </select>
            </label>
            <RetroInput label="Score every Nth frame" value={form.every} onChange={(event) => setForm({ ...form, every: event.target.value })} />
            {source === "recording" && <RetroInput label="Track every Nth frame" value={form.trackEvery} onChange={(event) => setForm({ ...form, trackEvery: event.target.value })} />}
          </div>
          <div className="flex flex-wrap gap-3">
            <RetroButton type="submit" disabled={busy}>{busy ? (source === "live" ? "Live..." : "Processing...") : source === "live" ? "Start Live Analysis" : "Run Interaction Analysis"}</RetroButton>
            {source === "live" && busy && liveId && <RetroButton type="button" variant="secondary" disabled={stopping} onClick={stopLive}>{stopping ? "Stopping..." : "Stop"}</RetroButton>}
          </div>
        </form>
      </ManagerPanel>
      <ManagerPanel title="Run Summary">
        <div className="grid grid-cols-3 gap-2 text-center">
          {([["employees", count("employee")], ["customers", count("customer")], ["interactions", interactions.length]] as const).map(([label, value]) => <div key={label} className="min-w-0 rounded-lg bg-surface-alt p-2 [overflow-wrap:anywhere] sm:p-3"><p className="font-heading text-3xl font-bold tabular-nums text-text">{value}</p><p className="text-xs text-text-muted">{label}</p></div>)}
        </div>
        {result && <p className="mt-4 break-all text-xs text-text-muted">Annotated video written to {result.output}</p>}
        {error && <p role="alert" className="mt-4 rounded-lg border border-danger bg-surface-alt p-3 text-sm text-danger">{error}</p>}
      </ManagerPanel>
    </div>
    {source === "live" && liveId && <ManagerPanel title="Live Preview">
      {/* eslint-disable-next-line @next/next/no-img-element -- live MJPEG stream from the backend, not a static asset */}
      <img src={`/api/backend/interaction/live/${liveId}/stream`} alt="Live annotated DroidCam feed" onLoad={() => setPreviewReady(true)} className="w-full border border-border-soft" />
      {!previewReady && <p className="text-sm text-text-muted">Connecting to the phone and loading models...</p>}
      <p className="mt-2 text-xs text-text-muted">Results (people and interactions) appear after you press Stop.</p>
    </ManagerPanel>}
    <ManagerPanel title="Single Frame Check">
      <label className="flex flex-col gap-2 text-sm font-medium text-text">
        Upload a still image for a quick person count and staffing check
        <input type="file" accept="image/*" onChange={checkFrame} disabled={frameBusy} className="text-sm text-text-muted" />
      </label>
      {frameBusy && <p className="mt-3 text-sm text-text-muted">Analyzing frame...</p>}
      {frameError && <p className="mt-3 border border-danger bg-surface-alt p-3 text-sm text-danger">{frameError}</p>}
      {frame && <p className="mt-3 text-sm text-text"><span className="font-mono">{frame.total_people}</span> people (<span className="font-mono">{frame.employee_count}</span> staff, <span className="font-mono">{frame.customer_count}</span> customers): <span className="font-semibold">{frame.interaction.status}</span>. {frame.interaction.message}</p>}
    </ManagerPanel>
    <ManagerPanel title="Confirmed Interactions">
      {interactions.length === 0 ? <p className="text-sm text-text-muted">{result ? "No confirmed interactions in this recording." : "Run an analysis to view interactions."}</p> : <ManagerTable label="Confirmed interactions">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-border-soft font-mono uppercase tracking-wider text-text-muted">
              <th scope="col" className="p-2">Employee</th>
              <th scope="col" className="p-2">Customer</th>
              <th scope="col" className="p-2">Window</th>
              <th scope="col" className="p-2">Duration</th>
              <th scope="col" className="p-2">Distance</th>
              <th scope="col" className="p-2">Verdict</th>
            </tr>
          </thead>
          <tbody>
            {interactions.map((item) => (
              <tr key={`${item.employee_track_id}-${item.customer_track_id}-${item.started_at}`} className="border-b border-border-soft/50">
                <td className="p-2 font-mono text-accent">#{item.employee_track_id}</td>
                <td className="p-2 font-mono">#{item.customer_track_id}</td>
                <td className="p-2 font-mono">{item.started_at.toFixed(1)}s → {item.last_seen_at.toFixed(1)}s</td>
                <td className="p-2 font-mono">{item.duration_seconds.toFixed(1)}s</td>
                <td className="p-2 font-mono">{item.distance_body_heights.toFixed(2)} bh</td>
                <td className="p-2 font-semibold text-text">{item.verdict || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </ManagerTable>}
    </ManagerPanel>
    <ManagerPanel title="Tracked People">
      {people.length === 0 ? <p className="text-sm text-text-muted">No people yet.</p> : <ManagerTable label="Tracked people">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-border-soft font-mono uppercase tracking-wider text-text-muted">
              <th scope="col" className="p-2">Track</th>
              <th scope="col" className="p-2">Role</th>
              <th scope="col" className="p-2">Seen</th>
              <th scope="col" className="p-2">Frames</th>
              <th scope="col" className="p-2">Employee score</th>
            </tr>
          </thead>
          <tbody>
            {people.map((person) => (
              <tr key={person.track_id} className="border-b border-border-soft/50">
                <td className="p-2 font-mono text-accent">#{person.track_id}</td>
                <td className="p-2 font-semibold text-text">{person.role}</td>
                <td className="p-2 font-mono">{person.first_seen.toFixed(1)}s → {person.last_seen.toFixed(1)}s</td>
                <td className="p-2 font-mono">{person.frames_observed}</td>
                <td className="p-2 font-mono">{person.employee_score.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </ManagerTable>}
    </ManagerPanel>
    <ManagerPanel title="Processing Log"><pre className="max-h-56 overflow-auto whitespace-pre-wrap font-mono text-xs text-text-muted">{logs || "No run yet."}</pre></ManagerPanel>
  </ManagerPage>;
}
