import React from "react";
import { RetroWindow, RetroCard } from "@/components/ui";

/* ═══════════════════════════════════════════════════════════════
   About Page — /about
   ═══════════════════════════════════════════════════════════════ */

const VALUE_PROPS = [
  {
    label: "Customer Care",
    title: "Customer Care, Measured",
    body: "Turn customer experience from a gut feeling into something your store can actually see and act on. RetailPulse tracks response times, flags unattended customers, and surfaces engagement quality — so you know exactly where service is strong and where it needs attention.",
  },
  {
    label: "Oversight",
    title: "Effortless Oversight",
    body: "Get clear visibility into staff performance and floor activity without asking anyone to sit and watch camera feeds all day. Managers see the information that matters — who's engaged, where gaps are forming, and how the floor is running — without the manual effort.",
  },
  {
    label: "Insight",
    title: "Insight, Not Just Footage",
    body: "Your security cameras are already a sunk cost. RetailPulse makes them earn their keep twice over — the same feeds used for loss prevention now answer \"how is my store actually doing,\" turning passive footage into an ongoing source of business intelligence.",
  },
];

const HOW_IT_WORKS = [
  {
    step: "01",
    title: "Cameras Observe",
    description:
      "Your existing security cameras capture the store floor as they always have — no new hardware, no extra installation, no disruption.",
  },
  {
    step: "02",
    title: "The System Tracks",
    description:
      "RetailPulse analyses the feeds in real time, tracking footfall, customer-staff engagement, movement patterns, and dwell times across every zone.",
  },
  {
    step: "03",
    title: "Insights Are Summarised",
    description:
      "Everything is distilled into a clear, at-a-glance dashboard — response times, flagged events, peak hours, and staff activity, all in one place.",
  },
  {
    step: "04",
    title: "Managers Act",
    description:
      "Instead of guessing or relying on anecdotal reports, you make decisions backed by real signals from the floor — and you can spot problems before customers walk out.",
  },
];

export default function AboutPage() {
  return (
    <div className="bg-bg min-h-screen">
      <main className="w-full max-w-6xl mx-auto px-4 md:px-6 lg:px-8 py-10 md:py-16 space-y-14 md:space-y-20">
        {/* ═══════════════════════════════════════════════════════
           Section 1: Hero / Intro
           ═══════════════════════════════════════════════════════ */}
        <RetroWindow title="About RetailPulse">
          <div className="space-y-4 max-w-3xl">
            <h1 className="font-heading text-2xl md:text-3xl font-bold text-text leading-tight">
              Your security cameras already see everything.
              <br />
              <span className="text-accent">Now they understand it, too.</span>
            </h1>
            <p className="text-text-muted leading-relaxed">
              RetailPulse converts a store&apos;s existing security camera infrastructure
              into a customer care and staff performance analytics system — without
              requiring a single piece of new hardware. If you can see the floor on a
              monitor, RetailPulse can tell you what&apos;s actually happening on it.
            </p>
          </div>
        </RetroWindow>

        {/* ═══════════════════════════════════════════════════════
           Section 2: Why RetailPulse
           ═══════════════════════════════════════════════════════ */}
        <section>
          <h2 className="font-heading text-xl md:text-2xl font-bold text-text mb-6 md:mb-8">
            Why Retail<span className="text-accent">Pulse</span>?
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {VALUE_PROPS.map((prop) => (
              <RetroCard key={prop.label} label={prop.label} className="pt-6">
                <h3 className="font-heading text-base font-bold text-text mb-2">
                  {prop.title}
                </h3>
                <p className="text-sm text-text-muted leading-relaxed">
                  {prop.body}
                </p>
              </RetroCard>
            ))}
          </div>
        </section>

        {/* ═══════════════════════════════════════════════════════
           Section 3: How It Works
           ═══════════════════════════════════════════════════════ */}
        <RetroWindow title="How It Works">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {HOW_IT_WORKS.map((item) => (
              <div key={item.step} className="flex gap-4">
                <span className="font-mono text-2xl font-bold text-accent/30 select-none leading-none pt-0.5">
                  {item.step}
                </span>
                <div>
                  <h3 className="font-heading text-sm font-bold text-text mb-1">
                    {item.title}
                  </h3>
                  <p className="text-sm text-text-muted leading-relaxed">
                    {item.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </RetroWindow>

        {/* ═══════════════════════════════════════════════════════
           Section 4: Contact
           ═══════════════════════════════════════════════════════ */}
        <RetroCard label="Contact" className="pt-6 max-w-md">
          <h3 className="font-heading text-base font-bold text-text mb-3">
            Get in touch
          </h3>
          <div className="space-y-2 text-sm text-text-muted">
            <p className="flex items-center gap-2">
              <PhoneIcon />
              <span className="text-text">0300-1234567</span>
            </p>
            <p className="flex items-center gap-2">
              <MailIcon />
              <a
                href="mailto:retailpulse@gmail.com"
                className="text-text hover:text-accent transition-colors duration-150"
              >
                retailpulse@gmail.com
              </a>
            </p>
          </div>
        </RetroCard>
      </main>
    </div>
  );
}

/* ── Inline SVG icons ── */

function PhoneIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-text-muted shrink-0"
    >
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  );
}

function MailIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-text-muted shrink-0"
    >
      <rect width="20" height="16" x="2" y="4" rx="2" />
      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
    </svg>
  );
}
