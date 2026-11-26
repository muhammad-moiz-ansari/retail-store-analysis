"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { RetroButton } from "@/components/ui";
import { ManagerPage, ManagerHeader, ManagerCard, ManagerPanel, ManagerTable } from "@/components/ui/ManagerLayout";

type DispatchTask = { id: string; instruction: string; state: string; target_zone_id?: string | null };

function DispatchStatus() {
  const [tasks, setTasks] = useState<DispatchTask[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/backend/tasks/me", { cache: "no-store", signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error("Task list unavailable");
        const data = await response.json();
        if (!controller.signal.aborted) {
          setTasks(data.tasks);
          setFailed(false);
        }
      })
      .catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [refresh]);
  return (
    <ManagerPanel title="Staff assignment status">
      <RetroButton type="button" variant="secondary" className="mb-3 min-h-11" onClick={() => setRefresh(value => value + 1)}>Refresh assignments</RetroButton>
      {failed && <p role="status" className="mb-3 text-sm text-danger">Assignment status could not be refreshed.</p>}
      {tasks?.length ? (
        <ManagerTable label="Staff assignments">
          <table className="w-full text-left text-sm">
            <thead><tr><th scope="col" className="p-2">Instruction</th><th scope="col" className="p-2">Zone</th><th scope="col" className="p-2">Status</th></tr></thead>
            <tbody>{tasks.map(task => (
              <tr key={task.id} className="border-b border-border-soft">
                <th scope="row" className="p-2 font-medium">{task.instruction}</th>
                <td className="p-2">{task.target_zone_id || "Unspecified"}</td>
                <td className="p-2">{task.state.replaceAll("_", " ")}</td>
              </tr>
            ))}</tbody>
          </table>
        </ManagerTable>
      ) : !failed && <p role="status" className="text-sm text-text-muted">{tasks ? "No staff assignments." : "Loading assignment status…"}</p>}
    </ManagerPanel>
  );
}

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
  id: string;
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

type BackendAlert = {
  id: string;
  category: string;
  severity: string;
  created_at: string;
  title: string;
  context: string;
  href?: string;
  status: "active" | "resolved";
  resolvedBy?: string;
};

const ALERTS: Alert[] = [
  { id: '1', category: "Unstaffed Zones", severity: "high", timestamp: "2 minutes ago", title: "Aisle 2 — Beverages left unstaffed for 42 minutes", context: "No employee detected in this zone since 10:15 AM. Nearest staff: Staff 03, Checkout Counter.", href: "/manager/employees", status: "active", order: 6 },
  { id: '2', category: "Unattended Customers", severity: "high", timestamp: "8 minutes ago", title: "Customer waited 6m 03s unattended at Checkout Counter", context: "Customer activity was detected without a staff interaction during the service threshold.", href: "/manager/customers", status: "active", order: 5 },
  { id: '3', category: "High Idle Time", severity: "medium", timestamp: "10:42 AM", title: "Staff 04 idle time exceeds 2 hours this shift", context: "Idle duration is above the configured shift threshold. Current zone: Home Appliances.", href: "/manager/employees", status: "active", order: 4 },
  { id: '4', category: "Unusual Traffic", severity: "medium", timestamp: "10:15 AM", title: "Unusual traffic spike detected — Entrance, 2:00–2:15 PM", context: "Entrance footfall was 34% above the usual interval. Consider short-term coverage support.", href: "/manager/spatial-analytics", status: "active", order: 3 },
  { id: '5', category: "System", severity: "low", timestamp: "9:30 AM", title: "Weekly report generated and ready for review", context: "The latest store performance report is ready for review.", href: "/manager/home", status: "active", order: 2 },
  { id: '6', category: "Unstaffed Zones", severity: "low", timestamp: "Yesterday, 4:22 PM", title: "Promo Display unstaffed for 28 minutes — resolved by Staff 01", context: "Coverage was restored and the zone has remained active since resolution.", href: "/manager/employees", status: "resolved", resolvedBy: "Staff 01", order: 1 },
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

function toCategory(category: string): Category {
  return CATEGORIES.includes(category as Category) ? (category as Category) : "System";
}

function toSeverity(severity: string): AlertSeverity {
  return ["high", "medium", "low"].includes(severity) ? (severity as AlertSeverity) : "low";
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<Category[]>(CATEGORIES);
  const [status, setStatus] = useState<Status>("active");
  const [sortOrder, setSortOrder] = useState<SortOrder>("recent");
  const [loading, setLoading] = useState(true);
  const [showingSample, setShowingSample] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    fetch("/api/backend/alerts?status=all", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (data?.alerts) {
          setAlerts(
            (data.alerts as BackendAlert[]).map((alert, index) => ({
              id: alert.id,
              category: toCategory(alert.category),
              severity: toSeverity(alert.severity),
              timestamp: new Date(alert.created_at).toLocaleString(),
              title: alert.title,
              context: alert.context,
              href: alert.href || "/manager/alerts",
              status: alert.status,
              resolvedBy: alert.resolvedBy,
              order: data.alerts.length - index,
            }))
          );
        } else throw new Error("Alert feed unavailable");
      })
      .catch(() => {
        setAlerts(ALERTS);
        setShowingSample(true);
      })
      .finally(() => setLoading(false));
  }, []);

  function toggleCategory(category: Category) {
    setSelectedCategories((current) =>
      current.includes(category)
        ? current.filter((item) => item !== category)
        : [...current, category]
    );
  }

  async function markResolved(id: string) {
    const response = await fetch(`/api/backend/alerts/${id}/resolve`, { method: "POST" });
    if (response.ok) {
      setAlerts((current) => current.map((alert) =>
        alert.id === id ? { ...alert, status: "resolved", resolvedBy: "Current manager" } : alert
      ));
    }
  }

  async function dispatchStaff(alert: Alert) {
    const response = await fetch("/api/backend/tasks/dispatch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alertId: alert.id, instruction: `Please respond to: ${alert.title}`, evidence: { alertTitle: alert.title } }),
    });
    const data = await response.json().catch(() => ({}));
    setNotice(response.ok ? `Staff dispatched for "${alert.title}".` : data.detail || data.error || "Dispatch failed.");
  }

  async function investigate(alert: Alert) {
    const response = await fetch(`/api/backend/agents/alerts/${encodeURIComponent(alert.id)}/investigate`, { method: "POST" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !Array.isArray(data.candidates)) {
      setNotice(response.status === 404 ? "No scoped analytics evidence is linked to this alert." : data.detail || "Investigation unavailable.");
      return;
    }
    const labels: Record<string, string> = { pipeline_issue: "camera problem", low_staffed_coverage: "low staffed coverage", long_queue: "long queue" };
    const found = (data.candidates as { signal: string; evidence: { matched_count: number }[] }[])
      .map((candidate) => `${labels[candidate.signal] ?? candidate.signal} (${candidate.evidence.reduce((total, item) => total + item.matched_count, 0)} cited rows)`);
    const missing = Array.isArray(data.unavailable_sources) && data.unavailable_sources.length ? ` Not available: ${data.unavailable_sources.join(", ")}.` : "";
    setNotice(`${data.synthetic ? "Synthetic data. " : ""}Possible factors for "${alert.title}": ${found.length ? found.join("; ") : "none found in the selected window"}.${missing} These are co-occurring signals, not a confirmed cause.`);
  }

  function clearFilters() {
    setSelectedCategories(CATEGORIES);
    setStatus("active");
    setSortOrder("recent");
  }

  const filteredAlerts = alerts
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
      <ManagerPage>
        <ManagerHeader title="Alerts & notifications" actions={!loading && (
            <div className="flex flex-wrap gap-2">
              <StatPill label={`Active: ${alerts.filter((alert) => alert.status === "active").length}`} className="border-danger/40 bg-danger/15 text-danger" />
              <StatPill label={`Resolved: ${alerts.filter((alert) => alert.status === "resolved").length}`} className="border-success/40 bg-success/15 text-success" />
              <StatPill label={`Total: ${alerts.length}`} className="border-border-soft bg-surface-alt text-text-muted" />
            </div>
          )}>
          <p>Review and resolve alerts reported by the RetailPulse backend.</p>
        </ManagerHeader>
        {showingSample && <p role="status" className="rounded-lg bg-surface-alt p-3 text-sm">Backend alerts unavailable. Showing the existing sample alert feed.</p>}
        {notice && <p role="status" className="rounded-lg bg-surface-alt p-3 text-sm font-semibold">{notice}</p>}

        <section aria-labelledby="filters-heading">
          <h2 id="filters-heading" className="sr-only">Alert filters</h2>
          <ManagerCard>
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
          </ManagerCard>
        </section>

        <section aria-labelledby="alert-feed-heading">
          <h2 id="alert-feed-heading" className="sr-only">Alert feed</h2>
          <div className="space-y-3">
            {loading ? (
              <ManagerCard className="py-10 text-center">
                <p className="font-heading text-base font-semibold text-text">Loading alerts...</p>
              </ManagerCard>
            ) : filteredAlerts.length > 0 ? (
              filteredAlerts.map((alert) => (
                <AlertFeedCard key={alert.id} alert={alert} onResolve={markResolved} onDispatch={dispatchStaff} onInvestigate={investigate} />
              ))
            ) : (
              <ManagerCard className="flex flex-col items-center justify-center gap-4 py-12 text-center">
                <p className="font-heading text-base font-semibold text-text">No alerts match your current filters.</p>
                <RetroButton type="button" variant="secondary" className="!px-3 !py-1.5 !text-xs" onClick={clearFilters}>
                  Clear Filters
                </RetroButton>
              </ManagerCard>
            )}
          </div>
        </section>
        <DispatchStatus />
        <StaffingProposal />
      </ManagerPage>
  );
}

function AlertFeedCard({ alert, onResolve, onDispatch, onInvestigate }: { alert: Alert; onResolve: (id: string) => void; onDispatch: (alert: Alert) => void; onInvestigate: (alert: Alert) => void }) {
  const isResolved = alert.status === "resolved";
  const severityLabel = alert.severity === "high" ? "HIGH" : alert.severity === "medium" ? "MEDIUM" : "LOW";

  return (
    <ManagerCard
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
            <RetroButton type="button" variant="secondary" className="!px-3 !py-1.5 !text-xs" aria-label={`Mark ${alert.title} as resolved`} onClick={() => onResolve(alert.id)}>Mark Resolved</RetroButton>
            <RetroButton type="button" variant="secondary" className="!px-3 !py-1.5 !text-xs" aria-label={`Dispatch staff for ${alert.title}`} onClick={() => onDispatch(alert)}>Dispatch Staff</RetroButton>
            <RetroButton type="button" variant="secondary" className="!px-3 !py-1.5 !text-xs" aria-label={`Investigate ${alert.title}`} onClick={() => onInvestigate(alert)}>Investigate</RetroButton>
            <Link href={alert.href} className="text-sm font-semibold text-accent underline underline-offset-2 transition-colors hover:text-accent-hover">
              View Details →
            </Link>
          </div>
        )}
      </div>
    </ManagerCard>
  );
}

type StaffingZone = { zone_id: string; suggested_staff: number | null; additional_staff: number | null; missing_inputs: string[] };

/** Advisory only: the backend never schedules anyone, and every answer requires a manager's approval. */
function StaffingProposal() {
  const [zones, setZones] = useState<StaffingZone[] | null>(null);
  const [message, setMessage] = useState("");
  const [decision, setDecision] = useState("");

  async function load(decide?: "approved" | "rejected") {
    const response = decide
      ? await fetch("/api/backend/agents/staffing/next-day/decision", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision: decide }) })
      : await fetch("/api/backend/agents/staffing/next-day", { cache: "no-store" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !Array.isArray(data.zones)) {
      setZones(null);
      setMessage(data.detail || "Staffing proposal unavailable.");
      return;
    }
    setZones(data.zones);
    setDecision(data.decision ? `${data.decision.decision} by ${data.decision.decided_by || "a manager"}` : "no decision recorded");
    setMessage(`${data.synthetic ? "Synthetic data. " : ""}Partial feature: assumes tomorrow repeats the selected window and ${data.customers_per_employee} customers per employee. Requires manager approval; nothing is scheduled.`);
  }

  return (
    <ManagerPanel title="Next-day staffing proposal (partial)">
      <RetroButton type="button" variant="secondary" className="mb-3 min-h-11" onClick={() => load()}>Load proposal</RetroButton>
      {message && <p role="status" className="mb-3 text-sm text-text-muted">{message}</p>}
      {zones && (
        <ul className="space-y-1 text-sm text-text">
          {zones.map((zone) => (
            <li key={zone.zone_id}>
              {zone.zone_id}: {zone.suggested_staff === null
                ? `no suggestion (missing ${zone.missing_inputs.join(", ")})`
                : `${zone.suggested_staff} staff suggested, ${zone.additional_staff ?? 0} more than rostered`}
            </li>
          ))}
        </ul>
      )}
      {zones && (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <RetroButton type="button" variant="secondary" className="!px-3 !py-1.5 !text-xs" onClick={() => load("approved")}>Approve</RetroButton>
          <RetroButton type="button" variant="secondary" className="!px-3 !py-1.5 !text-xs" onClick={() => load("rejected")}>Reject</RetroButton>
          <span className="font-mono text-xs text-text-muted">Decision for tomorrow: {decision}</span>
        </div>
      )}
    </ManagerPanel>
  );
}

function StatPill({ label, className }: { label: string; className: string }) {
  return <span className={`rounded-full border px-2.5 py-1 font-mono text-[11px] font-semibold ${className}`}>{label}</span>;
}
