"use client";

import React from "react";
import { Badge, RetroCard, RetroWindow } from "@/components/ui";

const SHIFT_OVERVIEW = [
  { label: "Shift", value: "9:00 AM – 6:00 PM", note: "Electronics floor" },
  { label: "Break", value: "2:30 PM", note: "30 minutes remaining" },
  {
    label: "Today's Interactions",
    value: "12 customers",
    note: "4 flagged as strong engagement",
  },
];

export default function EmployeeHomePage() {
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
      </main>
    </div>
  );
}
