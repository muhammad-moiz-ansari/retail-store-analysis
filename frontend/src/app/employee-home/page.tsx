"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Badge, RetroButton } from "@/components/ui";
import { ManagerPage, ManagerHeader, ManagerPanel, ManagerCard } from "@/components/ui/ManagerLayout";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const SHIFT_OVERVIEW = [
  { label: "Shift", value: "9:00 AM – 6:00 PM", note: "Electronics floor" },
  { label: "Break", value: "2:30 PM", note: "30 minutes remaining" },
  {
    label: "Today's Interactions",
    value: "12 customers",
    note: "4 flagged as strong engagement",
  },
];

const SCORE_BREAKDOWN = [
  { label: "Approach Speed", score: 28, max: 30 },
  { label: "Idle Time", score: 22, max: 25 },
  { label: "Interaction Score", score: 37, max: 45 },
];

const WEEKLY_SCORES = [
  { day: "Mon", score: 74 },
  { day: "Tue", score: 79 },
  { day: "Wed", score: 76 },
  { day: "Thu", score: 81 },
  { day: "Fri", score: 84 },
  { day: "Sat", score: 85 },
  { day: "Sun", score: 87 },
];

type Task = {
  id: string;
  instruction: string;
  state: "pending" | "delivered" | "acknowledged" | "in_progress" | "completed" | "declined" | "expired" | "cancelled";
  created_at: string;
  target_zone_id?: string | null;
  evidence?: { zoneName?: string; reason?: string; alertTitle?: string } | null;
  due_at?: string;
};

export default function EmployeeHomePage() {
  const [tasks, setTasks] = useState<Task[]>([]);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [pendingTask, setPendingTask] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ text: string; error: boolean }>();
  const submitting = useRef(false);
  const revision = useRef({ revision: 0 });

  const load = useCallback(async () => {
    const request = ++revision.current.revision;
    try {
      const response = await fetch("/api/backend/tasks/me", { cache: "no-store" });
      if (!response.ok) throw new Error("Task inbox unavailable");
      const data = await response.json();
      if (request === revision.current.revision) {
        setTasks(data.tasks);
        setLoadError(false);
      }
    } catch {
      if (request === revision.current.revision) setLoadError(true);
    } finally {
      if (request === revision.current.revision) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const requests = revision.current;
    void load();
    const events = new EventSource("/api/backend/tasks/events");
    events.addEventListener("ready", load);
    events.onmessage = load;
    return () => {
      ++requests.revision;
      events.close();
    };
  }, [load]);

  async function transitionTask(taskId: string, state: Task["state"]) {
    if (submitting.current) return;
    submitting.current = true;
    setPendingTask(taskId);
    setNotice(undefined);
    try {
      const response = await fetch(`/api/backend/tasks/${taskId}/transition`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error("Assignment update failed");
      ++revision.current.revision;
      setTasks(data.tasks);
      setLoadError(false);
      setNotice({ text: `Assignment ${state.replaceAll("_", " ")}.`, error: false });
    } catch {
      setNotice({ text: "The assignment update could not be confirmed. Check its status and try again.", error: true });
      void load();
    } finally {
      submitting.current = false;
      setPendingTask(null);
    }
  }

  const activeTasks = tasks.filter((task) => ["pending", "delivered", "acknowledged", "in_progress"].includes(task.state));

  return (
    <ManagerPage>
        <ManagerHeader title="My workspace">
          <p>Review your floor assignments and shift activity.</p>
        </ManagerHeader>

        <div>
          <ManagerPanel title="Current assignments">
            {notice && <p role={notice.error ? "alert" : "status"} className="mb-3 rounded-lg bg-surface-alt p-3 text-sm">{notice.text}</p>}
            {loadError && <div className="mb-3 flex flex-wrap items-center gap-3">
              <p role="status" className="text-sm text-danger">Assignments could not be refreshed.</p>
              <RetroButton type="button" variant="secondary" onClick={() => void load()}>Retry</RetroButton>
            </div>}
            <div className="space-y-3">
              {activeTasks.length > 0 ? (
                activeTasks.map((task, index) => (
                  <ManagerCard key={task.id} className={index === 0 ? "border-l-4 border-l-accent bg-surface-alt" : ""}>
                    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                      <div>
                        <Badge variant="accent">{task.state.replaceAll("_", " ")}</Badge>
                        <h3 className="mt-2 text-lg font-bold">{task.evidence?.zoneName || task.target_zone_id || "Aisle unspecified"}</h3>
                        <p className="mt-1 font-semibold">{task.instruction}</p>
                        <p className="mt-1 text-sm text-text-muted">{task.evidence?.reason || task.evidence?.alertTitle || "No reason was supplied."}</p>
                        <p className="mt-1 font-mono text-xs text-text-muted">
                          Delivered {new Date(task.created_at).toLocaleString()}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2" aria-busy={pendingTask === task.id}>
                        {task.state === "delivered" && (
                          <RetroButton type="button" variant="primary" className="min-h-11 flex-1 sm:flex-none" disabled={pendingTask !== null} onClick={() => transitionTask(task.id, "acknowledged")}>
                            Acknowledge
                          </RetroButton>
                        )}
                        {task.state === "acknowledged" && (
                          <RetroButton type="button" variant="primary" className="min-h-11 flex-1 sm:flex-none" disabled={pendingTask !== null} onClick={() => transitionTask(task.id, "in_progress")}>
                            Start
                          </RetroButton>
                        )}
                        {task.state === "in_progress" && (
                          <RetroButton type="button" variant="primary" className="min-h-11 flex-1 sm:flex-none" disabled={pendingTask !== null} onClick={() => transitionTask(task.id, "completed")}>
                            Complete
                          </RetroButton>
                        )}
                        {task.state !== "in_progress" && (
                          <RetroButton type="button" variant="danger" className="min-h-11 flex-1 sm:flex-none" disabled={pendingTask !== null} onClick={() => transitionTask(task.id, "declined")}>
                            Decline
                          </RetroButton>
                        )}
                      </div>
                    </div>
                  </ManagerCard>
                ))
              ) : (
                <ManagerCard>
                  <p className="text-sm text-text-muted">{loading ? "Loading assignments…" : loadError ? "Assignment status is unavailable." : "No active dispatch tasks."}</p>
                </ManagerCard>
              )}
            </div>
          </ManagerPanel>
        </div>

        <p className="rounded-lg bg-surface-alt p-3 text-sm text-text-muted">Shift, coverage and performance below use sample data.</p>
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3" aria-label="Sample shift overview">
          {SHIFT_OVERVIEW.map((item) => (
            <ManagerCard key={item.label}>
              <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                {item.label}
              </p>
              <p className="mt-2 font-heading text-xl font-bold text-text">{item.value}</p>
              <p className="mt-1 text-sm text-text-muted">{item.note}</p>
            </ManagerCard>
          ))}
        </section>

        <section className="mt-12" aria-labelledby="performance-heading">
          <ManagerPanel title="My Performance">
            <h2 id="performance-heading" className="sr-only">My Performance</h2>
            <div className="grid gap-6 md:grid-cols-2">
              <ManagerCard className="flex flex-col items-center justify-center py-6 text-center">
                <ScoreRing score={87} max={100} />
                <h3 className="mt-4 font-heading text-base font-bold text-text">Today&apos;s Score</h3>
                <p className="mt-1 max-w-sm text-sm leading-relaxed text-text-muted">
                  Strong — you&apos;re approaching customers quickly and keeping interactions meaningful.
                </p>
              </ManagerCard>

              <ManagerCard label="Score Breakdown" className="py-6">
                <div className="space-y-5">
                  {SCORE_BREAKDOWN.map((item) => (
                    <div key={item.label}>
                      <div className="flex items-baseline justify-between gap-4">
                        <p className="font-heading text-sm font-semibold text-text">{item.label}</p>
                        <p className="shrink-0 font-mono text-xs text-text-muted">
                          {item.score} / {item.max}
                        </p>
                      </div>
                      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-border-soft/30">
                        <div
                          className="h-full rounded-full bg-accent"
                          style={{ width: `${(item.score / item.max) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <Link href="/my-performance" className="mt-6 inline-block">
                  <RetroButton variant="secondary">View Full History →</RetroButton>
                </Link>
              </ManagerCard>
            </div>

            <div className="mt-6 border-l-4 border-l-accent-soft bg-surface-alt/50 px-4 py-3 text-sm leading-relaxed text-text-muted">
              This score reflects approach speed, idle time, and interaction duration from today&apos;s shift. It&apos;s a support tool for you and your manager — not an automatic judgment. Questions about your score? Talk to your floor lead.
            </div>
          </ManagerPanel>
        </section>

        <section className="mt-12" aria-labelledby="trend-heading">
          <ManagerPanel title="Your Score This Week">
            <h2 id="trend-heading" className="sr-only">Your Score This Week</h2>
            <ManagerCard>
              <div className="h-[280px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart accessibilityLayer data={WEEKLY_SCORES} margin={{ top: 12, right: 12, left: -20, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="var(--color-border-soft)" strokeOpacity={0.25} />
                    <XAxis
                      dataKey="day"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: "var(--color-text-muted)", fontSize: 12, fontFamily: "var(--font-jetbrains-mono)" }}
                    />
                    <YAxis
                      domain={[0, 100]}
                      ticks={[0, 25, 50, 75, 100]}
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: "var(--color-text-muted)", fontSize: 12, fontFamily: "var(--font-jetbrains-mono)" }}
                    />
                    <Tooltip
                      cursor={{ stroke: "var(--color-accent-soft)", strokeWidth: 1 }}
                      contentStyle={{
                        backgroundColor: "var(--color-surface)",
                        border: "1px solid var(--color-border-soft)",
                        borderRadius: "6px",
                        color: "var(--color-text)",
                        fontFamily: "var(--font-jetbrains-mono)",
                        fontSize: "12px",
                      }}
                      formatter={(value) => [`${value} / 100`, "Score"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="score"
                      stroke="var(--color-accent)"
                      strokeWidth={3}
                      dot={{ fill: "var(--color-accent)", r: 4 }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-4 font-mono text-xs font-semibold text-success">↑ 13 points since Monday — keep it up.</p>
            </ManagerCard>
          </ManagerPanel>
        </section>

        <section className="mt-12" aria-label="Shift updates and zone assignment">
          <div className="grid gap-6 md:grid-cols-2">
            <ManagerPanel title="Zone Assignment">
              <div className="space-y-2">
                <p className="font-heading text-lg font-semibold text-text">Electronics Floor</p>
                <p className="text-sm text-text-muted">Assigned for this shift · 9:00 AM – 6:00 PM</p>
                <div className="flex items-center gap-2 pt-3 text-sm text-text-muted">
                  <span className="h-2 w-2 rounded-full bg-success" aria-hidden="true" />
                  <span>Coverage status: <span className="font-medium text-success">Active</span></span>
                </div>
              </div>
            </ManagerPanel>

            <ManagerPanel title="Shift Updates">
              <ul className="space-y-4">
                <li className="flex gap-3 text-sm leading-relaxed text-text">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />
                  Keep the electronics demo table clear for the afternoon promotion.
                </li>
                <li className="flex gap-3 text-sm leading-relaxed text-text">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />
                  Ask a floor lead for assistance with returns over Rs. 10,000.
                </li>
                <li className="flex gap-3 text-sm leading-relaxed text-text">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />
                  Your break is scheduled for 2:30 PM.
                </li>
              </ul>
            </ManagerPanel>
          </div>
        </section>

        <section className="mt-12" aria-label="Need help">
          <ManagerCard className="border-l-4 border-l-accent">
            <p className="font-heading text-sm font-semibold text-text">Need help?</p>
            <p className="mt-1 text-sm leading-relaxed text-text-muted">
              Contact the floor lead for customer escalations, stock issues, or changes to your assigned area.
            </p>
          </ManagerCard>
        </section>
    </ManagerPage>
  );
}

function ScoreRing({ score, max }: { score: number; max: number }) {
  const size = 160;
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden="true">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-border-soft)"
          strokeWidth={strokeWidth}
          strokeOpacity={0.3}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - score / max)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-4xl font-bold text-accent">{score}</span>
        <span className="font-mono text-sm text-text-muted">/ {max}</span>
      </div>
    </div>
  );
}
