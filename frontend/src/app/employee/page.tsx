"use client";

import React from "react";
import { Badge, RetroCard, RetroWindow } from "@/components/ui";

const TASKS = [
  { title: "Welcome customers", detail: "Entrance and electronics", status: "Active" },
  { title: "Restock promo display", detail: "Aisle 3 · by 3:00 PM", status: "Pending" },
  { title: "Checkout support", detail: "Cover break at 4:30 PM", status: "Upcoming" },
];

const SHIFT_UPDATES = [
  "Keep the electronics demo table clear for the afternoon promotion.",
  "Ask a floor lead for assistance with returns over Rs. 10,000.",
  "Your break is scheduled for 2:30 PM.",
];

export default function EmployeePage() {
  return (
    <div className="min-h-screen bg-bg">
      <main className="mx-auto w-full max-w-6xl px-4 py-10 md:px-6 md:py-14">
        <section className="mb-8 flex flex-col gap-4 border-b border-border-soft pb-7 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-accent">Employee workspace</p>
            <h1 className="mt-2 font-heading text-3xl font-bold tracking-tight text-text md:text-4xl">Your shift at a glance</h1>
            <p className="mt-2 text-sm text-text-muted">The information you need to serve customers and complete today&apos;s work.</p>
          </div>
          <Badge variant="neutral">Employee access</Badge>
        </section>

        <div className="grid gap-5 md:grid-cols-3">
          <Metric label="Shift" value="9:00 AM – 6:00 PM" note="Electronics floor" />
          <Metric label="Break" value="2:30 PM" note="30 minutes remaining" />
          <Metric label="Today&apos;s service" value="12 customers" note="4 helpful interactions logged" />
        </div>

        <div className="mt-7 grid gap-7 lg:grid-cols-5">
          <RetroWindow title="Today&apos;s tasks" className="lg:col-span-3">
            <div className="space-y-3">
              {TASKS.map((task) => (
                <div key={task.title} className="flex items-center gap-4 rounded-md border border-border-soft bg-surface-alt p-4">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 border-accent font-mono text-sm font-bold text-accent">✓</span>
                  <div className="min-w-0 flex-1">
                    <p className="font-heading text-sm font-semibold text-text">{task.title}</p>
                    <p className="mt-0.5 text-xs text-text-muted">{task.detail}</p>
                  </div>
                  <span className="font-mono text-[11px] text-text-muted">{task.status}</span>
                </div>
              ))}
            </div>
          </RetroWindow>

          <RetroWindow title="Shift updates" className="lg:col-span-2">
            <ul className="space-y-4">
              {SHIFT_UPDATES.map((update) => (
                <li key={update} className="flex gap-3 text-sm leading-relaxed text-text">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                  {update}
                </li>
              ))}
            </ul>
          </RetroWindow>
        </div>

        <RetroCard className="mt-7 border-l-4 border-l-accent">
          <p className="font-heading text-sm font-semibold text-text">Need help?</p>
          <p className="mt-1 text-sm text-text-muted">Contact the floor lead for customer escalations, stock issues, or changes to your assigned area.</p>
        </RetroCard>

        <RetroCard className="mt-5 border-l-4 border-l-accent">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-heading text-sm font-semibold text-text">Compare people counts</p>
              <p className="mt-1 text-sm text-text-muted">Analyze and compare people counts between two video feeds.</p>
            </div>
            <a
              href="/compare-people"
              className="ml-4 shrink-0 rounded-md bg-accent px-4 py-2 font-heading text-sm font-semibold text-surface hover:bg-accent-hover transition-colors"
            >
              Compare
            </a>
          </div>
        </RetroCard>
      </main>
    </div>
  );
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <RetroCard>
      <p className="font-mono text-[11px] uppercase tracking-wider text-text-muted">{label}</p>
      <p className="mt-2 font-heading text-xl font-bold text-text">{value}</p>
      <p className="mt-1 text-xs text-text-muted">{note}</p>
    </RetroCard>
  );
}
