"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Badge, RetroButton } from "@/components/ui";
import { ManagerCard, ManagerHeader, ManagerPage, ManagerPanel, ManagerTable } from "@/components/ui/ManagerLayout";

type AisleState = "empty" | "covered" | "uncovered" | "waiting_for_staff" | "help_sent";
type Aisle = { label: string; zoneId: string; zoneName: string | null; customers: number; employees: number; state: AisleState };
type Outcome = { decision?: string; reason?: string; employeeName?: string | null; taskId?: string | null };
type Step = { t: number; kind: "observe" | "need" | "arrived"; aisle: string; text: string; source?: string | null; outcome?: Outcome };
type Mode = "live" | "replay";
type Run = {
  id: string; mode: Mode; state: "starting" | "loading models" | "running" | "finished" | "stopped" | "failed"; error: string | null;
  t: number; duration: number; speed: number; policy: { need_hold_s: number; arrive_hold_s: number };
  trace: {
    video?: string; processingSeconds?: number; models?: { person_tracker?: string; role_model?: string };
    samples?: number; droppedSamples?: number; processingFps?: number | null;
  };
  aisles: Record<string, Aisle>; steps: Step[]; preview?: number | null;
};
type Task = {
  id: string; state: string; instruction: string; target_zone_id: string | null; source_zone_id: string | null;
  created_at: string; ack_seconds: number | null; employee_name: string; employee_email: string;
  target_zone_name: string | null; source_zone_name: string | null;
};
type Status = { run: Run | null; tasks: Task[]; videos: ("webm" | "mp4")[] };

const STATE_LABEL: Record<AisleState, string> = {
  empty: "Empty", covered: "Staffed", uncovered: "Customers alone", waiting_for_staff: "Needs staff", help_sent: "Help sent",
};
const STATE_BADGE: Record<AisleState, "neutral" | "success" | "danger" | "attention" | "accent"> = {
  empty: "neutral", covered: "success", uncovered: "attention", waiting_for_staff: "danger", help_sent: "accent",
};
const TASK_BADGE: Record<string, "neutral" | "success" | "danger" | "attention" | "accent"> = {
  delivered: "attention", acknowledged: "accent", in_progress: "accent", completed: "success", declined: "danger", cancelled: "neutral",
};

function seconds(value: number) {
  return `${value.toFixed(1)} s`;
}

export default function AisleRelayPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [videoError, setVideoError] = useState(false);
  const [mode, setMode] = useState<Mode>("live");
  const video = useRef<HTMLVideoElement>(null);

  const load = useCallback(async () => {
    try {
      const response = await fetch("/api/backend/aisle-relay/status", { cache: "no-store" });
      const data = await response.json().catch(() => null);
      if (!response.ok || !data) throw new Error(data?.detail || "Relay status unavailable");
      setStatus(data);
      setFailed(null);
    } catch (error) {
      setFailed(error instanceof Error ? error.message : "Relay status unavailable");
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(load, 1000);
    return () => window.clearInterval(timer);
  }, [load]);

  // Keep the recorded video on the replay clock (a live run shows its own frames instead).
  const run = status?.run;
  useEffect(() => {
    const el = video.current;
    if (!el || !run || run.mode !== "replay") return;
    el.playbackRate = run.speed;
    if (run.state === "running") {
      if (Math.abs(el.currentTime - run.t) > 1.2) el.currentTime = run.t;
      if (el.paused) void el.play().catch(() => undefined);
    } else if (!el.paused) {
      el.pause();
    }
  }, [run]);

  async function command(path: "start" | "stop") {
    setBusy(true);
    try {
      const response = await fetch(`/api/backend/aisle-relay/${path}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ speed: 1, mode }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || `Could not ${path} the relay`);
      if (path === "start" && video.current) video.current.currentTime = 0;
      if (path === "start") setVideoError(false);
      setFailed(null);
      await load();
    } catch (error) {
      setFailed(error instanceof Error ? error.message : `Could not ${path} the relay`);
    } finally {
      setBusy(false);
    }
  }

  const running = run?.state === "running" || run?.state === "loading models" || run?.state === "starting";
  const liveView = run?.mode === "live" && running;
  const decisions = run?.steps ?? [];

  return (
    <ManagerPage>
      <ManagerHeader
        title="Aisle relay"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 text-sm">
              <span className="text-text-muted">Source</span>
              <select value={mode} disabled={busy || running} onChange={(event) => setMode(event.target.value as Mode)}
                className="min-h-11 rounded-md border border-border-soft bg-surface px-2">
                <option value="live">Live CV on the video</option>
                <option value="replay">Replay recorded pass</option>
              </select>
            </label>
            <RetroButton type="button" variant="primary" className="min-h-11" disabled={busy || running} onClick={() => command("start")}>
              {run ? "Run again" : "Start relay"}
            </RetroButton>
            <RetroButton type="button" variant="secondary" className="min-h-11" disabled={busy || !running} onClick={() => command("stop")}>
              Stop
            </RetroButton>
          </div>
        }
      >
        <p>
          Two aisle cameras in one split-screen video. Each frame goes through YOLO once; the detections are split back into
          Aisle 1 (left) and Aisle 2 (right). When an aisle has customers and no staff for {run?.policy.need_hold_s ?? 2} s, the
          agent dispatches an employee from the aisle that has staff to spare. The employee gets the assignment on their
          phone; the camera closes it when they arrive.
        </p>
      </ManagerHeader>

      {failed && <p role="alert" className="rounded-lg bg-danger/15 p-3 text-sm text-danger">{failed}</p>}
      {run?.error && <p role="alert" className="rounded-lg bg-danger/15 p-3 text-sm text-danger">Run failed: {run.error}</p>}

      <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <ManagerPanel title="Camera feeds · left Aisle 1 · right Aisle 2">
          {liveView ? (
            run.preview ? (
              // eslint-disable-next-line @next/next/no-img-element -- MJPEG stream, not an optimisable image
              <img src={`/api/backend/aisle-relay/stream?run=${run.id}`} alt="Live annotated feed of both aisles"
                className="aspect-video w-full rounded-lg bg-black object-contain" />
            ) : (
              <ManagerCard><p role="status" className="text-sm text-text-muted">{run.state === "loading models" ? "Loading the YOLO models…" : "Waiting for the first analysed frame…"}</p></ManagerCard>
            )
          ) : status?.videos.length ? (
            <>
              <video key={run?.id ?? "none"} ref={video} muted playsInline preload="auto" controls={run?.mode === "live"} className="aspect-video w-full rounded-lg bg-black"
                aria-label="Annotated aisle camera video" onLoadedData={() => setVideoError(false)}>
                {status.videos.map((fmt, index) => (
                  <source key={`${run?.id}-${fmt}`} src={`/api/backend/aisle-relay/video/${fmt}?run=${run?.id ?? "none"}`} type={`video/${fmt}`}
                    onError={index === status.videos.length - 1 ? () => setVideoError(true) : undefined} />
                ))}
              </video>
              {videoError && (
                <p role="alert" className="mt-2 text-sm text-danger">
                  This browser could not play the camera video ({status.videos.join(" or ")}). The relay still runs; try Chrome, Edge or Firefox.
                </p>
              )}
            </>
          ) : (
            <ManagerCard><p className="text-sm text-text-muted">{run?.mode === "live" ? "This run's recorded video is not available." : "No video yet. Start a live CV run, or record a pass with scripts/aisle_relay_demo.py to replay."}</p></ManagerCard>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-3 font-mono text-xs text-text-muted">
            <Badge variant={running ? "accent" : run?.state === "finished" ? "success" : "neutral"}>{run ? `${run.mode} · ${run.state}` : "idle"}</Badge>
            {run && <span>{seconds(run.t)} / {seconds(run.duration)}</span>}
            {run?.mode === "live" && run.trace.samples != null && (
              <span>{run.trace.samples} frames analysed · {run.trace.droppedSamples ?? 0} dropped to stay live{run.trace.processingFps ? ` · ${run.trace.processingFps} fps` : ""}</span>
            )}
            {run?.trace.models?.person_tracker && <span>{run.trace.models.person_tracker} · {run.trace.models.role_model}</span>}
          </div>
          {run && (
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-border-soft/40" aria-hidden="true">
              <div className="h-full rounded-full bg-accent transition-[width]" style={{ width: `${Math.min(100, (run.t / run.duration) * 100)}%` }} />
            </div>
          )}
        </ManagerPanel>

        <ManagerPanel title="Aisles now">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            {run ? Object.entries(run.aisles).map(([id, aisle]) => (
              <ManagerCard key={id} className={aisle.state === "waiting_for_staff" ? "border-l-4 border-l-danger" : aisle.state === "help_sent" ? "border-l-4 border-l-accent" : ""}>
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-heading text-base font-bold">{aisle.label}</h3>
                  <Badge variant={STATE_BADGE[aisle.state]}>{STATE_LABEL[aisle.state]}</Badge>
                </div>
                <p className="text-sm text-text-muted">{aisle.zoneName} · zone {aisle.zoneId}</p>
                <p className="mt-2 font-mono text-sm">
                  <span className="text-lg font-semibold">{aisle.customers}</span> customers ·{" "}
                  <span className="text-lg font-semibold">{aisle.employees}</span> staff
                </p>
              </ManagerCard>
            )) : (
              <ManagerCard><p className="text-sm text-text-muted">Start the relay to watch both aisles.</p></ManagerCard>
            )}
          </div>
        </ManagerPanel>
      </div>

      <div className="grid min-w-0 gap-6 xl:grid-cols-2">
        <ManagerPanel title="Assignments sent">
          {status?.tasks.length ? (
            <ManagerTable label="Aisle relay assignments">
              <table className="w-full text-left text-sm">
                <thead><tr>
                  <th scope="col" className="p-2">Employee</th><th scope="col" className="p-2">Move</th>
                  <th scope="col" className="p-2">Status</th><th scope="col" className="p-2">Ack time</th>
                </tr></thead>
                <tbody>{status.tasks.map((task) => (
                  <tr key={task.id} className="border-b border-border-soft">
                    <th scope="row" className="p-2 font-medium">{task.employee_name}<span className="block font-mono text-xs font-normal text-text-muted">{task.employee_email}</span></th>
                    <td className="p-2">{task.source_zone_name ?? task.source_zone_id ?? "Unknown"} → {task.target_zone_name ?? task.target_zone_id}</td>
                    <td className="p-2"><Badge variant={TASK_BADGE[task.state] ?? "neutral"}>{task.state.replaceAll("_", " ")}</Badge></td>
                    <td className="p-2 font-mono">{task.ack_seconds == null ? "not yet" : seconds(task.ack_seconds)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </ManagerTable>
          ) : (
            <p role="status" className="text-sm text-text-muted">No assignments in this run yet.</p>
          )}
        </ManagerPanel>

        <ManagerPanel title="What the agent saw and did">
          {decisions.length ? (
            <ol className="max-h-[26rem] space-y-0 overflow-auto border-t border-border-soft" aria-label="Agent trace">
              {decisions.map((step, index) => (
                <li key={index} className="grid grid-cols-[3.5rem_4.5rem_minmax(0,1fr)] gap-2 border-b border-border-soft py-2 text-sm">
                  <span className="font-mono text-text-muted">{seconds(step.t)}</span>
                  <span className={`font-mono text-[11px] font-semibold uppercase ${step.kind === "need" ? "text-danger" : step.kind === "arrived" ? "text-success" : "text-text-muted"}`}>{step.kind}</span>
                  <span className="min-w-0">
                    {step.text}
                    {step.outcome?.decision && (
                      <span className="mt-1 block text-text-muted">
                        → {step.outcome.decision.replaceAll("_", " ")}
                        {step.outcome.reason ? `: ${step.outcome.reason}` : ""}
                      </span>
                    )}
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            <p role="status" className="text-sm text-text-muted">The agent&apos;s observations and decisions appear here as the video plays.</p>
          )}
        </ManagerPanel>
      </div>
    </ManagerPage>
  );
}
