"use client";

import React, { useState } from "react";
import Link from "next/link";
import { RetroButton, RetroCard, RetroWindow } from "@/components/ui";

type Category = "Unattended Customers" | "Unstaffed Zones" | "High Idle Time" | "Unusual Traffic" | "System";
type Status = "all" | "active" | "resolved";
type SortOrder = "recent" | "oldest" | "severity";

const CATEGORIES: Category[] = [
  "Unattended Customers",
  "Unstaffed Zones",
  "High Idle Time",
  "Unusual Traffic",
  "System",
];

type AlertSeverity = "high" | "medium" | "low";
type Alert = {
  id: number;
  category: Category;
  severity: AlertSeverity;
  timestamp: string;
  title: string;
  context: string;
  href: string;
  status: "active" | "resolved";
  resolvedBy?: string;
  order: number;
};

const ALERTS: Alert[] = [
  { id: 1, category: "Unstaffed Zones", severity: "high", timestamp: "2 minutes ago", title: "Aisle 2 — Beverages left unstaffed for 42 minutes", context: "No employee detected in this zone since 10:15 AM. Nearest staff: Staff 03, Checkout Counter.", href: "/employee-info", status: "active", order: 6 },
  { id: 2, category: "Unattended Customers", severity: "high", timestamp: "8 minutes ago", title: "Customer waited 6m 03s unattended at Checkout Counter", context: "Customer activity was detected without a staff interaction during the service threshold.", href: "/customer-info", status: "active", order: 5 },
  { id: 3, category: "High Idle Time", severity: "medium", timestamp: "10:42 AM", title: "Staff 04 idle time exceeds 2 hours this shift", context: "Idle duration is above the configured shift threshold. Current zone: Home Appliances.", href: "/employee-info", status: "active", order: 4 },
  { id: 4, category: "Unusual Traffic", severity: "medium", timestamp: "10:15 AM", title: "Unusual traffic spike detected — Entrance, 2:00–2:15 PM", context: "Entrance footfall was 34% above the usual interval. Consider short-term coverage support.", href: "/spatial-analytics", status: "active", order: 3 },
  { id: 5, category: "System", severity: "low", timestamp: "9:30 AM", title: "Weekly report generated and ready for review", context: "The latest store performance report is available in Reports & Exports.", href: "/reports", status: "active", order: 2 },
  { id: 6, category: "Unstaffed Zones", severity: "low", timestamp: "Yesterday, 4:22 PM", title: "Promo Display unstaffed for 28 minutes — resolved by Staff 01", context: "Coverage was restored and the zone has remained active since resolution.", href: "/employee-info", status: "resolved", resolvedBy: "Staff 01", order: 1 },
];

const CATEGORY_STYLES: Record<Category, string> = {
  "Unattended Customers": "border-danger/40 bg-danger/15 text-danger",
  "Unstaffed Zones": "border-accent/40 bg-accent/15 text-accent",
  "High Idle Time": "border-accent-soft/60 bg-accent-soft/20 text-text",
  "Unusual Traffic": "border-success/40 bg-success/15 text-success",
  System: "border-border-soft bg-surface-alt text-text-muted",
};

const SEVERITY_BARS: Record<AlertSeverity, string> = {
  high: "border-l-danger",
  medium: "border-l-accent",
  low: "border-l-accent-soft",
};

export default function AlertsPage() {
  const [selectedCategories, setSelectedCategories] = useState<Category[]>(CATEGORIES);
  const [status, setStatus] = useState<Status>("active");
  const [sortOrder, setSortOrder] = useState<SortOrder>("recent");

  function toggleCategory(category: Category) {
    setSelectedCategories((current) =>
      current.includes(category)
        ? current.filter((item) => item !== category)
        : [...current, category]
    );
  }

  const filteredAlerts = ALERTS
    .filter((alert) => selectedCategories.includes(alert.category))
    .filter((alert) => status === "all" || alert.status === status)
    .sort((first, second) => {
      if (sortOrder === "oldest") return first.order - second.order;
      if (sortOrder === "severity") {
        const weights: Record<AlertSeverity, number> = { high: 3, medium: 2, low: 1 };
        return weights[second.severity] - weights[first.severity] || second.order - first.order;
      }
      return second.order - first.order;
    });

  return (
    <div className="min-h-screen bg-bg">
      <main className="mx-auto w-full max-w-[1280px] space-y-12 px-4 py-10 md:px-6 md:py-16 lg:px-8">
        <RetroWindow title="Alerts & Notifications">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.16em] text-accent">Live Monitoring</p>
              <h1 className="mt-2 font-heading text-3xl font-bold tracking-tight text-text md:text-[32px]">Alerts & Notifications</h1>
              <p className="mt-2 max-w-2xl text-sm text-text-muted">Real-time flags from the RetailPulse monitoring agents — review and resolve as needed.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StatPill label="Active: 5" className="border-danger/40 bg-danger/15 text-danger" />
              <StatPill label="Resolved Today: 12" className="border-success/40 bg-success/15 text-success" />
              <StatPill label="Total This Week: 34" className="border-border-soft bg-surface-alt text-text-muted" />
            </div>
          </div>
        </RetroWindow>

        <section aria-labelledby="filters-heading">
          <h2 id="filters-heading" className="sr-only">Alert filters</h2>
          <RetroCard>
            <div className="grid gap-6 xl:grid-cols-[1fr_auto_auto] xl:items-end">
              <fieldset>
                <legend className="font-heading text-xs font-semibold uppercase tracking-wider text-text-muted">Category</legend>
                <div className="mt-2 flex flex-wrap gap-2">
                  {CATEGORIES.map((category) => (
                    <RetroButton
                      key={category}
                      type="button"
                      variant={selectedCategories.includes(category) ? "primary" : "secondary"}
                      className="!px-3 !py-1.5 !text-xs"
                      aria-pressed={selectedCategories.includes(category)}
                      onClick={() => toggleCategory(category)}
                    >
                      {category}
                    </RetroButton>
                  ))}
                </div>
              </fieldset>

              <fieldset>
                <legend className="font-heading text-xs font-semibold uppercase tracking-wider text-text-muted">Status</legend>
                <div className="mt-2 flex flex-wrap gap-2">
                  {(["all", "active", "resolved"] as Status[]).map((option) => (
                    <RetroButton
                      key={option}
                      type="button"
                      variant={status === option ? "primary" : "secondary"}
                      className="!px-3 !py-1.5 !text-xs capitalize"
                      aria-pressed={status === option}
                      onClick={() => setStatus(option)}
                    >
                      {option}
                    </RetroButton>
                  ))}
                </div>
              </fieldset>

              <label className="block font-heading text-xs font-semibold uppercase tracking-wider text-text-muted">
                Sort
                <select
                  value={sortOrder}
                  onChange={(event) => setSortOrder(event.target.value as SortOrder)}
                  className="mt-2 w-full min-w-48 rounded border border-border bg-surface px-3 py-2 text-sm font-normal text-text focus:outline-none focus:ring-2 focus:ring-accent"
                >
                  <option value="recent">Most Recent</option>
                  <option value="oldest">Oldest First</option>
                  <option value="severity">Severity: High to Low</option>
                </select>
              </label>
            </div>
          </RetroCard>
        </section>

        <section aria-labelledby="alert-feed-heading">
          <h2 id="alert-feed-heading" className="sr-only">Alert feed</h2>
          <div className="space-y-3">
            {filteredAlerts.map((alert) => <AlertFeedCard key={alert.id} alert={alert} />)}
          </div>
        </section>
      </main>
    </div>
  );
}

function AlertFeedCard({ alert }: { alert: Alert }) {
  const isResolved = alert.status === "resolved";
  const severityLabel = alert.severity === "high" ? "HIGH" : alert.severity === "medium" ? "MEDIUM" : "LOW";

  return (
    <RetroCard
      className={`${isResolved ? "opacity-60" : `border-l-4 ${SEVERITY_BARS[alert.severity]}`} transition-opacity duration-300`}
      aria-label={`${severityLabel} alert: ${alert.title}`}
    >
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${CATEGORY_STYLES[alert.category]}`}>
              {alert.category}
            </span>
            {!isResolved && <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-text-muted">{severityLabel}</span>}
          </div>
          <span className="font-mono text-xs text-text-muted">{alert.timestamp}</span>
        </div>
        <div>
          <h3 className="font-heading text-base font-semibold text-text">{alert.title}</h3>
          <p className="mt-1 text-sm leading-relaxed text-text-muted">{alert.context}</p>
        </div>
        {isResolved ? (
          <p className="flex items-center gap-2 font-mono text-xs font-semibold text-success">
            <span aria-hidden="true">✓</span> Resolved by {alert.resolvedBy}
          </p>
        ) : (
          <div className="flex flex-wrap items-center gap-4">
            <RetroButton type="button" variant="secondary" className="!px-3 !py-1.5 !text-xs" aria-label={`Mark ${alert.title} as resolved`}>Mark Resolved</RetroButton>
            <Link href={alert.href} className="text-sm font-semibold text-accent underline underline-offset-2 transition-colors hover:text-accent-hover">
              View Details →
            </Link>
          </div>
        )}
      </div>
    </RetroCard>
  );
}

function StatPill({ label, className }: { label: string; className: string }) {
  return <span className={`rounded-full border px-2.5 py-1 font-mono text-[11px] font-semibold ${className}`}>{label}</span>;
}
