"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { RetroButton, RetroInput } from "@/components/ui";
import { ManagerPage, ManagerHeader, ManagerPanel, ManagerTable } from "@/components/ui/ManagerLayout";
import { runBackendJob } from "@/lib/backend-job";

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

type GlobalPerson = { global_person_id: string; role: "employee" | "customer" | "unknown"; role_source: string; created_at: string };

const defaults = { cam1: "backend/videos/cam1.mp4", cam2: "backend/videos/cam2.mp4", sampleEvery: "5", minGap: "1", maxGap: "45", cam1Boundary: "0.85", cam2Boundary: "0.15" };

export default function CameraHandoffPage() {
  const [form, setForm] = useState(defaults);
  const [logs, setLogs] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [people, setPeople] = useState<GlobalPerson[]>([]);

  const loadPeople = useCallback(async () => {
    const response = await fetch("/api/backend/camera/people", { cache: "no-store" });
    if (response.ok) setPeople(await response.json());
  }, []);

  useEffect(() => { loadPeople(); }, [loadPeople]);

  async function setRole(id: string, role: "employee" | "unknown") {
    const response = await fetch(`/api/backend/camera/people/${id}/role`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role, assigned_by: "manager", reason: "Set from the Camera Handoff page" }),
    });
    if (!response.ok) setError((await response.json().catch(() => ({}))).detail || "Role update failed.");
    await loadPeople();
  }

  async function run(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError(""); setLogs(""); setResult(null);
    try {
      const body = {
        cam1: form.cam1, cam2: form.cam2,
        sample_every: Number(form.sampleEvery), min_gap: Number(form.minGap), max_gap: Number(form.maxGap),
        cam1_boundary: Number(form.cam1Boundary), cam2_boundary: Number(form.cam2Boundary),
      };
      const job = await runBackendJob<Result>("camera/handoff", "camera/jobs", body, (update) => setLogs(update.logs.join("\n")));
      setResult(job.result);
      await loadPeople();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Processing failed."); }
    finally { setBusy(false); }
  }

  const handoffs = result?.handoffs ?? [];
  const count = (status: Handoff["status"]) => handoffs.filter((item) => item.status === status).length;

  return <ManagerPage>
    <ManagerHeader title="Camera Handoff"><p>Offline directional matching for the configured transition: Camera 1 right exit to Camera 2 left entry.</p></ManagerHeader>
    <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <ManagerPanel title="Processing Configuration">
        <form onSubmit={run} className="space-y-4">
          <RetroInput label="Camera 1 video" value={form.cam1} onChange={(event) => setForm({ ...form, cam1: event.target.value })} />
          <RetroInput label="Camera 2 video" value={form.cam2} onChange={(event) => setForm({ ...form, cam2: event.target.value })} />
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {(["sampleEvery", "minGap", "maxGap", "cam1Boundary", "cam2Boundary"] as const).map((key) => <RetroInput key={key} label={key} value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} />)}
          </div>
          <RetroButton type="submit" disabled={busy}>{busy ? "Processing..." : "Run Handoff Analysis"}</RetroButton>
        </form>
      </ManagerPanel>
      <ManagerPanel title="Association Status">
        <div className="grid grid-cols-3 gap-2 text-center">
          {(["confirmed", "uncertain", "unmatched"] as const).map((status) => <div key={status} className="min-w-0 rounded-lg bg-surface-alt p-2 [overflow-wrap:anywhere] sm:p-3"><p className="font-heading text-3xl font-bold tabular-nums text-text">{count(status)}</p><p className="text-xs text-text-muted">{status}</p></div>)}
        </div>
        {result?.processing && <p className="mt-4 text-xs text-text-muted">Completed in {result.processing.elapsed_seconds}s using {result.processing.appearance_method}.</p>}
        {error && <p role="alert" className="mt-4 rounded-lg border border-danger bg-surface-alt p-3 text-sm text-danger">{error}</p>}
      </ManagerPanel>
    </div>
    <ManagerPanel title="Handoff Evidence">
      {handoffs.length === 0 ? <p className="text-sm text-text-muted">Run an analysis to view directional events and identity decisions.</p> : <ManagerTable label="Handoff evidence">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-border-soft font-mono uppercase tracking-wider text-text-muted">
              <th scope="col" className="p-2">Status</th>
              <th scope="col" className="p-2">Master ID</th>
              <th scope="col" className="p-2">Tracks</th>
              <th scope="col" className="p-2">Score</th>
              <th scope="col" className="p-2">Evidence</th>
            </tr>
          </thead>
          <tbody>
            {handoffs.map((item, index) => (
              <tr key={`${item.source_event_id}-${item.target_event_id}-${index}`} className="border-b border-border-soft/50">
                <td className="p-2 font-semibold text-text">{item.status}</td>
                <td className="p-2 font-mono text-accent">{item.master_id || "-"}</td>
                <td className="p-2 font-mono">{item.source_track_id || "-"} → {item.target_track_id || "-"}</td>
                <td className="p-2 font-mono">{item.score.toFixed(2)}</td>
                <td className="p-2 text-text-muted">appearance {item.evidence.appearance_similarity?.toFixed(2) || "-"}, gap {item.evidence.gap_seconds?.toFixed(1) || "-"}s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </ManagerTable>}
    </ManagerPanel>
    <ManagerPanel title="Global People">
      {people.length === 0 ? <p className="text-sm text-text-muted">No global identities yet. Run a handoff analysis to create them.</p> : <ManagerTable label="Global people">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-border-soft font-mono uppercase tracking-wider text-text-muted">
              <th scope="col" className="p-2">Global ID</th>
              <th scope="col" className="p-2">Role</th>
              <th scope="col" className="p-2">Source</th>
              <th scope="col" className="p-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {people.map((person) => (
              <tr key={person.global_person_id} className="border-b border-border-soft/50">
                <td className="p-2 font-mono text-accent">{person.global_person_id}</td>
                <td className="p-2 font-semibold text-text">{person.role}</td>
                <td className="p-2 text-text-muted">{person.role_source}</td>
                <td className="p-2">{person.role === "employee" ? <RetroButton type="button" variant="secondary" className="!px-3 !py-1 !text-xs" onClick={() => setRole(person.global_person_id, "unknown")}>Clear role</RetroButton> : <RetroButton type="button" variant="secondary" className="!px-3 !py-1 !text-xs" onClick={() => setRole(person.global_person_id, "employee")}>Register employee</RetroButton>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </ManagerTable>}
    </ManagerPanel>
    <ManagerPanel title="Processing Log"><pre className="max-h-56 overflow-auto whitespace-pre-wrap font-mono text-xs text-text-muted">{logs || "No run yet."}</pre></ManagerPanel>
  </ManagerPage>;
}