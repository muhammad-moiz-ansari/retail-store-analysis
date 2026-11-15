"use client";

import React, { useEffect, useState } from "react";
import { CRTFrame, RetroButton } from "@/components/ui";
import { ManagerHeader, ManagerPage, ManagerPanel } from "@/components/ui/ManagerLayout";
import { DashboardDataSource } from "@/components/dashboard/DashboardAnalytics";

type SystemStatus = {
  workers: Record<string, string>;
  activeAlerts: number;
  activeTasks: number;
  cameras: { total: number; online: number };
  acknowledgement?: { tasks: number; meanSeconds: number | null; medianSeconds: number | null };
  dispatchOutcomes?: Record<string, number>;
};

const dispatchLabels: Record<string, string> = {
  dispatched: "Assigned",
  already_assigned: "Already assigned",
  no_eligible_employee: "No eligible employee",
  paused: "Dispatch paused",
  alert_only: "Alert only",
};

function formatSeconds(seconds: number | null) {
  return seconds === null ? "Unavailable" : `${seconds.toLocaleString(undefined, { maximumFractionDigits: 2 })} s`;
}

function SystemStatusStrip() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [failed, setFailed] = useState(false);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/backend/system-status", { cache: "no-store", signal: controller.signal })
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((data: SystemStatus) => {
        if (!controller.signal.aborted) setStatus(data);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, [refresh]);

  function refreshStatus() {
    setStatus(null);
    setFailed(false);
    setRefresh((current) => current + 1);
  }

  if (failed) return (
    <div className="space-y-2">
      <p role="status" className="text-sm text-danger">Backend unavailable: system status could not be loaded.</p>
      <RetroButton variant="secondary" onClick={refreshStatus}>Retry system status</RetroButton>
    </div>
  );
  if (!status) return <p role="status" className="font-mono text-xs text-text-muted">Loading system status...</p>;
  const items = [
    ["Active alerts", status.activeAlerts],
    ["Active tasks", status.activeTasks],
    ["Cameras online", `${status.cameras.online}/${status.cameras.total}`],
    ...Object.entries(status.workers).map(([name, state]) => [name, state.replace(/_/g, " ")]),
  ];
  const acknowledgement = status.acknowledgement;
  const outcomes = status.dispatchOutcomes ? Object.entries(status.dispatchOutcomes) : null;
  return (
    <div className="space-y-4">
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {items.map(([label, value]) => (
          <div key={label} className="min-w-0 rounded-lg bg-surface-alt p-3 [overflow-wrap:anywhere]">
            <dt className="text-xs font-medium text-text-muted">{label}</dt>
            <dd className="mt-1 font-heading text-lg font-bold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="grid gap-4 md:grid-cols-2">
        <section aria-label="Dispatch outcomes" className="rounded-lg bg-surface-alt p-3">
          <h3 className="font-semibold">Dispatch outcomes</h3>
          <p className="mt-1 text-xs text-text-muted">All recorded decisions. Same-event retries reuse the original decision.</p>
          {outcomes === null ? (
            <p className="mt-2 text-sm text-text-muted">Dispatch outcome counts are unavailable.</p>
          ) : outcomes.length === 0 ? (
            <p className="mt-2 text-sm text-text-muted">No dispatch decisions recorded.</p>
          ) : (
            <dl className="mt-2 space-y-1 text-sm">
              {outcomes.map(([decision, count]) => (
                <div key={decision} className="flex justify-between gap-3">
                  <dt>{dispatchLabels[decision] ?? decision.replace(/_/g, " ")}</dt>
                  <dd className="font-semibold tabular-nums">{count}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>
        <section aria-label="Acknowledgement timing" className="rounded-lg bg-surface-alt p-3">
          <h3 className="font-semibold">Acknowledgement timing</h3>
          <p className="mt-1 text-xs text-text-muted">Time from task creation to first acknowledgement.</p>
          {acknowledgement ? (
            <dl className="mt-2 space-y-1 text-sm">
              {[
                ["Tasks with timing", acknowledgement.tasks],
                ["Mean time", formatSeconds(acknowledgement.meanSeconds)],
                ["Median time", formatSeconds(acknowledgement.medianSeconds)],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between gap-3">
                  <dt>{label}</dt>
                  <dd className="font-semibold tabular-nums">{value}</dd>
                </div>
              ))}
            </dl>
          ) : <p className="mt-2 text-sm text-text-muted">Acknowledgement timing is unavailable.</p>}
        </section>
      </div>
      <RetroButton variant="secondary" onClick={refreshStatus}>Refresh system status</RetroButton>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ManagerPage>
        <ManagerHeader title="Manager dashboard">
          <p>Review recorded activity for your selected window, then check backend and camera status.</p>
        </ManagerHeader>
        <ManagerPanel title="Camera previews">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <div>
              <CRTFrame label="CAM 01 - NOT CONNECTED" signal={false} className="w-full" />
              <p className="text-sm text-text-muted mt-3">Live entrance feed unavailable.</p>
            </div>
            <div>
              <CRTFrame label="RECORDED DEMO CLIP" videoSrc="/videos/cam1.mp4" controls className="w-full" />
              <p className="text-sm text-text-muted mt-3">Recorded sample video, separate from the selected analytics. No live inference is connected here.</p>
            </div>
            <div>
              <CRTFrame label="CAM 03 - NOT CONNECTED" signal={false} className="w-full" />
              <p className="text-sm text-text-muted mt-3">Live floor feed unavailable.</p>
            </div>
          </div>
        </ManagerPanel>
        <DashboardDataSource>
          <ManagerPanel title="Backend system status">
            <p className="mb-4 text-sm text-text-muted">Application status reported by the backend, separate from event analytics and camera-feed verification.</p>
            <SystemStatusStrip />
          </ManagerPanel>
          <ManagerPanel title="Trajectory & heatmaps">
            <p className="text-sm text-text-muted">Map analytics unavailable. A registered store map and role/interaction layers have not been connected.</p>
          </ManagerPanel>
        </DashboardDataSource>
    </ManagerPage>
  );
}
