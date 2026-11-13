"use client";

import React, { useEffect, useState } from "react";
import { RetroWindow, CRTFrame, RetroCard, RetroButton, RetroInput } from "@/components/ui";
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
    <RetroWindow title="System Status">
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {items.map(([label, value]) => (
          <div key={label} className="border border-border-soft bg-surface-alt p-3">
            <dt className="font-mono text-[10px] uppercase tracking-wider text-text-muted">{label}</dt>
            <dd className="mt-1 font-mono text-lg font-bold text-text">{value}</dd>
          </div>
        ))}
      </dl>
    </RetroWindow>
  );
}

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-bg flex flex-col">
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-6 md:py-8 space-y-8 pb-12">
        <h1 className="font-heading text-2xl font-bold text-text">Manager dashboard</h1>
        <DashboardDataSource />
        <section aria-label="Backend system status" className="space-y-3">
          <h2 className="font-heading text-lg font-bold text-text">Backend system status</h2>
          <p className="text-sm text-text-muted">Application status reported by the backend, separate from event analytics and camera-feed verification.</p>
          <SystemStatusStrip />
        </section>
        <section aria-label="Camera previews">
          <h2 className="font-heading text-lg font-bold text-text mb-4">Camera previews</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
        </section>
        <section aria-label="Additional analytics" className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <RetroWindow title="Recent interactions">
            <p className="text-sm text-text-muted">Interaction details unavailable. This provider currently supplies aggregate counts, not employee/customer event rows.</p>
          </RetroWindow>
          <RetroWindow title="Trajectory & Heatmaps">
            <p className="text-sm text-text-muted">Map analytics unavailable. A registered store map and role/interaction layers have not been connected.</p>
          </RetroWindow>
        </section>
        <RetroCard label="Ask RetailPulse">
          <p className="text-sm text-text-muted mb-3">Ask is unavailable until the authenticated Query service is connected.</p>
          <div className="flex flex-wrap gap-3">
            <RetroInput aria-label="Ask RetailPulse (unavailable)" placeholder="Ask about store performance" disabled className="flex-1" />
            <RetroButton disabled>Ask</RetroButton>
          </div>
        </RetroCard>
      </main>
    </div>
  );
}
