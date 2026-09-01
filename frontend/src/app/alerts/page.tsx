"use client";

import React, { useState } from "react";
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
      </main>
    </div>
  );
}

function StatPill({ label, className }: { label: string; className: string }) {
  return <span className={`rounded-full border px-2.5 py-1 font-mono text-[11px] font-semibold ${className}`}>{label}</span>;
}
