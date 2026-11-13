"use client";

import React, { useEffect, useState } from "react";
import { CRTFrame, RetroButton, RetroInput } from "@/components/ui";
import { ManagerHeader, ManagerPage, ManagerPanel } from "@/components/ui/ManagerLayout";
import { DashboardDataSource } from "@/components/dashboard/DashboardAnalytics";

type SystemStatus = {
  workers: Record<string, string>;
  activeAlerts: number;
  activeTasks: number;
  cameras: { total: number; online: number };
};

function SystemStatusStrip() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch("/api/backend/system-status", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then(setStatus)
      .catch(() => setFailed(true));
  }, []);

  if (failed) return <p role="status" className="font-mono text-xs font-semibold text-danger">Backend unavailable: system status could not be loaded.</p>;
  if (!status) return <p role="status" className="font-mono text-xs text-text-muted">Loading system status...</p>;
  const items = [
    ["Active alerts", status.activeAlerts],
    ["Active tasks", status.activeTasks],
    ["Cameras online", `${status.cameras.online}/${status.cameras.total}`],
    ...Object.entries(status.workers).filter(([name]) => name !== "pos").map(([name, state]) => [name, state.replace(/_/g, " ")]),
  ];
  return (
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {items.map(([label, value]) => (
          <div key={label} className="min-w-0 rounded-lg bg-surface-alt p-3 [overflow-wrap:anywhere]">
            <dt className="text-xs font-medium text-text-muted">{label}</dt>
            <dd className="mt-1 font-heading text-lg font-bold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
  );
}

export default function DashboardPage() {
  return (
    <ManagerPage>
        <ManagerHeader title="Manager dashboard">
          <p>Review recorded activity for your selected window, then check backend and camera status.</p>
        </ManagerHeader>
        <DashboardDataSource />
        <ManagerPanel title="Backend system status">
          <p className="mb-4 text-sm text-text-muted">Application status reported by the backend, separate from event analytics and camera-feed verification.</p>
          <SystemStatusStrip />
        </ManagerPanel>
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
        <section aria-label="Additional analytics" className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ManagerPanel title="Recent interactions">
            <p className="text-sm text-text-muted">Interaction details unavailable. This provider currently supplies aggregate counts, not employee/customer event rows.</p>
          </ManagerPanel>
          <ManagerPanel title="Trajectory & heatmaps">
            <p className="text-sm text-text-muted">Map analytics unavailable. A registered store map and role/interaction layers have not been connected.</p>
          </ManagerPanel>
        </section>
        <section aria-label="Ask RetailPulse" className="sticky bottom-0 z-20 rounded-xl border border-border-soft bg-surface px-3 py-2 shadow-lg">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <h2 className="text-sm font-semibold">Ask RetailPulse</h2>
            <p className="text-xs text-text-muted">Unavailable until the Query service is connected.</p>
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            <RetroInput aria-label="Ask RetailPulse (unavailable)" placeholder="Ask about store performance" disabled className="flex-1" />
            <RetroButton disabled>Ask</RetroButton>
          </div>
        </section>
    </ManagerPage>
  );
}
