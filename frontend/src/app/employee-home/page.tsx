"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Badge, RetroButton, RetroCard, RetroWindow } from "@/components/ui";
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
  due_at?: string;
};

export default function EmployeeHomePage() {
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    const load = () =>
      fetch("/api/backend/tasks/me", { cache: "no-store" })
        .then((response) => (response.ok ? response.json() : null))
        .then((data) => setTasks(data?.tasks || []));
    load();
    // The backend task stream announces changes; refetch on each event so new dispatches appear without a reload.
    const events = new EventSource("/api/backend/tasks/events");
    events.addEventListener("ready", load);
    events.onmessage = load;
    return () => events.close();
  }, []);

  async function transitionTask(taskId: string, state: Task["state"]) {
    const response = await fetch(`/api/backend/tasks/${taskId}/transition`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state }),
    });
    const data = await response.json().catch(() => ({}));
    if (response.ok) setTasks(data.tasks || []);
  }

  const activeTasks = tasks.filter((task) => ["pending", "delivered", "acknowledged", "in_progress"].includes(task.state));

  return (
    <div className="min-h-screen bg-bg">
      <main className="mx-auto w-full max-w-[1280px] px-4 py-10 md:px-6 md:py-14 lg:px-8">
        <RetroWindow title="Employee Workspace">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.16em] text-accent">
                Employee workspace
              </p>
              <h1 className="mt-2 font-heading text-[32px] font-bold leading-tight tracking-tight text-text">
                Your Shift at a Glance
              </h1>
              <p className="mt-2 text-sm text-text-muted">
                The information you need to serve customers and track your performance today.
              </p>
            </div>
            <Badge variant="neutral" className="shrink-0">
              Employee Access
            </Badge>
          </div>
        </RetroWindow>

        <section className="mt-7 grid grid-cols-1 gap-5 md:grid-cols-3" aria-label="Shift overview">
          {SHIFT_OVERVIEW.map((item) => (
            <RetroCard key={item.label}>
              <p className="font-mono text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                {item.label}
              </p>
              <p className="mt-2 font-heading text-xl font-bold text-text">{item.value}</p>
              <p className="mt-1 text-sm text-text-muted">{item.note}</p>
            </RetroCard>
          ))}
        </section>

        <section className="mt-12" aria-labelledby="task-heading">
          <RetroWindow title="Task Inbox">
            <h2 id="task-heading" className="sr-only">Task Inbox</h2>
            <div className="space-y-3">
              {activeTasks.length > 0 ? (
                activeTasks.map((task) => (
                  <RetroCard key={task.id} className="border-l-4 border-l-accent">
                    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                      <div>
                        <Badge variant="accent">{task.state.replace("_", " ")}</Badge>
                        <p className="mt-3 font-heading text-base font-semibold text-text">{task.instruction}</p>
                        <p className="mt-1 font-mono text-xs text-text-muted">
                          Delivered {new Date(task.created_at).toLocaleString()}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {task.state === "delivered" && (
                          <RetroButton type="button" variant="primary" className="!px-3 !py-1.5 !text-xs" onClick={() => transitionTask(task.id, "acknowledged")}>
                            Acknowledge
                          </RetroButton>
                        )}
                        {task.state === "acknowledged" && (
                          <RetroButton type="button" variant="primary" className="!px-3 !py-1.5 !text-xs" onClick={() => transitionTask(task.id, "in_progress")}>
                            Start
                          </RetroButton>
                        )}
                        {task.state === "in_progress" && (
                          <RetroButton type="button" variant="primary" className="!px-3 !py-1.5 !text-xs" onClick={() => transitionTask(task.id, "completed")}>
                            Complete
                          </RetroButton>
                        )}
                        {task.state !== "in_progress" && (
                          <RetroButton type="button" variant="danger" className="!px-3 !py-1.5 !text-xs" onClick={() => transitionTask(task.id, "declined")}>
                            Decline
                          </RetroButton>
                        )}
                      </div>
                    </div>
                  </RetroCard>
                ))
              ) : (
                <RetroCard>
                  <p className="text-sm text-text-muted">No active dispatch tasks.</p>
                </RetroCard>
              )}
            </div>
          </RetroWindow>
        </section>

        <section className="mt-12" aria-labelledby="performance-heading">
          <RetroWindow title="My Performance">
            <h2 id="performance-heading" className="sr-only">My Performance</h2>
            <div className="grid gap-6 md:grid-cols-2">
              <RetroCard className="flex flex-col items-center justify-center py-6 text-center">
                <ScoreRing score={87} max={100} />
                <h3 className="mt-4 font-heading text-base font-bold text-text">Today&apos;s Score</h3>
                <p className="mt-1 max-w-sm text-sm leading-relaxed text-text-muted">
                  Strong — you&apos;re approaching customers quickly and keeping interactions meaningful.
                </p>
              </RetroCard>

              <RetroCard label="Score Breakdown" className="py-6">
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
              </RetroCard>
            </div>

            <div className="mt-6 border-l-4 border-l-accent-soft bg-surface-alt/50 px-4 py-3 text-sm leading-relaxed text-text-muted">
              This score reflects approach speed, idle time, and interaction duration from today&apos;s shift. It&apos;s a support tool for you and your manager — not an automatic judgment. Questions about your score? Talk to your floor lead.
            </div>
          </RetroWindow>
        </section>

        <section className="mt-12" aria-labelledby="trend-heading">
          <RetroWindow title="Your Score This Week">
            <h2 id="trend-heading" className="sr-only">Your Score This Week</h2>
            <RetroCard>
              <div className="h-[280px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={WEEKLY_SCORES} margin={{ top: 12, right: 12, left: -20, bottom: 0 }}>
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
            </RetroCard>
          </RetroWindow>
        </section>

        <section className="mt-12" aria-label="Shift updates and zone assignment">
          <div className="grid gap-6 md:grid-cols-2">
            <RetroWindow title="Zone Assignment">
              <div className="space-y-2">
                <p className="font-heading text-lg font-semibold text-text">Electronics Floor</p>
                <p className="text-sm text-text-muted">Assigned for this shift · 9:00 AM – 6:00 PM</p>
                <div className="flex items-center gap-2 pt-3 text-sm text-text-muted">
                  <span className="h-2 w-2 rounded-full bg-success" aria-hidden="true" />
                  <span>Coverage status: <span className="font-medium text-success">Active</span></span>
                </div>
              </div>
            </RetroWindow>

            <RetroWindow title="Shift Updates">
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
            </RetroWindow>
          </div>
        </section>

        <section className="mt-12" aria-label="Need help">
          <RetroCard className="border-l-4 border-l-accent">
            <p className="font-heading text-sm font-semibold text-text">Need help?</p>
            <p className="mt-1 text-sm leading-relaxed text-text-muted">
              Contact the floor lead for customer escalations, stock issues, or changes to your assigned area.
            </p>
          </RetroCard>
        </section>
      </main>
    </div>
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
