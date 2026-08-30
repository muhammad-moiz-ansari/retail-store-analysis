"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { RetroCard } from "@/components/ui/RetroCard";
import { RetroButton } from "@/components/ui/RetroButton";
import { Badge } from "@/components/ui/Badge";
import { RetroWindow } from "@/components/ui/RetroWindow";

export default function LandingPage() {
  // Smooth scroll to section
  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="flex flex-col">
      {/* ══ HERO SECTION ══ */}
      <section className="w-full px-4 md:px-6 lg:px-8 py-20 md:py-24 lg:py-28">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            {/* Left Column: Text Content */}
            <div className="space-y-6">
              {/* Eyebrow Badge */}
              <Badge variant="accent" className="!text-[10px] !px-3 !py-1">
                AI-POWERED RETAIL ANALYTICS
              </Badge>

              {/* Headline */}
              <h1 className="font-heading text-4xl md:text-5xl lg:text-[52px] font-bold text-text leading-[1.1]">
                Store Intelligence for Retail Teams — Without New Hardware
              </h1>

              {/* Sub-headline */}
              <p className="text-lg text-text-muted max-w-[480px] leading-relaxed">
                RetailPulse turns your existing CCTV into a live system for
                customer engagement, staff performance, and store analytics —
                no new cameras, no new hardware.
              </p>

              {/* CTA Row */}
              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                <Link href="/signup">
                  <RetroButton variant="primary" className="!px-6 !py-3 !text-base">
                    Get Started
                  </RetroButton>
                </Link>
                <RetroButton
                  variant="secondary"
                  className="!px-6 !py-3 !text-base"
                  onClick={() => scrollToSection("how-it-works")}
                >
                  See How It Works
                </RetroButton>
                <Link href="/compare-people">
                  <RetroButton variant="secondary" className="!px-6 !py-3 !text-base">
                    Process & Compare People
                  </RetroButton>
                </Link>
              </div>

              {/* Trust Line */}
              <p className="text-sm text-text-muted pt-2">
                Built for single-store and multi-store retail operations.
              </p>
            </div>

            {/* Right Column: Hero Visual */}
            <div className="flex justify-center lg:justify-end">
              <RetroWindow
                title="Dashboard Preview"
                className="max-w-[560px] w-full transform lg:-rotate-2"
              >
                <HeroDashboardPreview />
              </RetroWindow>
            </div>
          </div>
        </div>
      </section>

      {/* ══ PROBLEM / AGITATE SECTION ══ */}
      <section className="w-full bg-surface-alt px-4 md:px-6 lg:px-8 py-16 md:py-20">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          {/* Section Heading */}
          <h2 className="font-heading text-3xl md:text-4xl font-bold text-text">
            Most Retail Cameras Only Watch for Theft
          </h2>

          {/* Problem Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
            <RetroCard>
              <p className="text-sm text-text leading-relaxed">
                Managers can't tell if customers are actually being helped — or
                just wandering, unattended, until they leave.
              </p>
            </RetroCard>
            <RetroCard>
              <p className="text-sm text-text leading-relaxed">
                Staff performance is invisible until a customer complains or
                sales quietly drop.
              </p>
            </RetroCard>
            <RetroCard>
              <p className="text-sm text-text leading-relaxed">
                Footfall and floor traffic data sits unused in security footage
                nobody has time to review.
              </p>
            </RetroCard>
          </div>

          {/* Transition Line */}
          <p className="font-heading text-xl md:text-2xl font-medium text-accent pt-6">
            RetailPulse turns that same footage into a live, actionable signal.
          </p>
        </div>
      </section>

      {/* ══ HOW IT WORKS SECTION ══ */}
      <section
        id="how-it-works"
        className="w-full px-4 md:px-6 lg:px-8 py-16 md:py-20 scroll-mt-16"
      >
        <div className="max-w-6xl mx-auto">
          {/* Title */}
          <h2 className="font-heading text-3xl md:text-4xl font-bold text-text text-center mb-12">
            How It Works
          </h2>

          {/* Four-Step Flow */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 relative">
            {[
              {
                num: "01",
                title: "Observe",
                desc: "Existing CCTV cameras — entrance and floor — feed the system in real time.",
              },
              {
                num: "02",
                title: "Analyze",
                desc: "AI agents track footfall, staff-customer engagement, and movement patterns automatically.",
              },
              {
                num: "03",
                title: "Summarize",
                desc: "Insights are organized into a live dashboard — no manual review of raw footage required.",
              },
              {
                num: "04",
                title: "Act",
                desc: "Managers see what's working and what needs attention, backed by data instead of guesswork.",
              },
            ].map((step, i) => (
              <div key={step.num} className="relative">
                <RetroCard className="h-full">
                  <div className="space-y-3">
                    <Badge variant="accent" className="!text-base !px-3 !py-1.5 !font-mono">
                      {step.num}
                    </Badge>
                    <h3 className="font-heading text-lg font-semibold text-text">
                      {step.title}
                    </h3>
                    <p className="text-sm text-text-muted leading-relaxed">
                      {step.desc}
                    </p>
                  </div>
                </RetroCard>
                {/* Connector line (desktop only) */}
                {i < 3 && (
                  <div
                    className="hidden lg:block absolute top-1/2 -right-3 w-6 h-px border-t border-dashed border-border-soft"
                    style={{ transform: "translateY(-50%)" }}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ PRODUCT CAPABILITIES (BENTO GRID) ══ */}
      <section className="w-full bg-surface-alt px-4 md:px-6 lg:px-8 py-16 md:py-20">
        <div className="max-w-6xl mx-auto">
          {/* Title */}
          <h2 className="font-heading text-3xl md:text-4xl font-bold text-text text-center mb-12">
            One Dashboard. Every Signal.
          </h2>

          {/* Bento Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Large Feature Card - spans 2 columns on desktop */}
            <div className="lg:col-span-2">
              <RetroCard className="h-full">
                <div className="space-y-4">
                  <h3 className="font-heading text-xl font-semibold text-text">
                    Live Camera Dashboard
                  </h3>
                  <p className="text-sm text-text-muted leading-relaxed">
                    Real-time CCTV feed with overlaid insights — see customer
                    movement, staff engagement, and zone activity as it happens.
                  </p>
                  <div className="bg-surface-alt rounded border border-border-soft p-4 flex items-center justify-center h-32">
                    <DashboardPreviewPlaceholder />
                  </div>
                </div>
              </RetroCard>
            </div>

            {/* Standard Feature Cards */}
            <RetroCard>
              <div className="space-y-3">
                <h3 className="font-heading text-lg font-semibold text-text">
                  Customer Info Analytics
                </h3>
                <p className="text-sm text-text-muted leading-relaxed">
                  Footfall, engagement, trajectory insights — understand who
                  walks in and what they do.
                </p>
              </div>
            </RetroCard>

            <RetroCard>
              <div className="space-y-3">
                <h3 className="font-heading text-lg font-semibold text-text">
                  Employee Performance
                </h3>
                <p className="text-sm text-text-muted leading-relaxed">
                  Scoring, leaderboard, coverage alerts — fair metrics based on
                  objective activity data.
                </p>
              </div>
            </RetroCard>

            <RetroCard>
              <div className="space-y-3">
                <h3 className="font-heading text-lg font-semibold text-text">
                  Spatial Analytics & Heatmaps
                </h3>
                <p className="text-sm text-text-muted leading-relaxed">
                  Movement and zone insight — see where customers spend time
                  and where they don't.
                </p>
              </div>
            </RetroCard>

            <RetroCard>
              <div className="space-y-3">
                <h3 className="font-heading text-lg font-semibold text-text">
                  Sales & Product Trends
                </h3>
                <p className="text-sm text-text-muted leading-relaxed">
                  POS-driven trend data — connect sales performance to customer
                  behavior patterns.
                </p>
              </div>
            </RetroCard>

            <RetroCard>
              <div className="space-y-3">
                <h3 className="font-heading text-lg font-semibold text-text">
                  AI Reports & Exports
                </h3>
                <p className="text-sm text-text-muted leading-relaxed">
                  One-click PDF summaries generated by the Insight Narration
                  agent — ready to share.
                </p>
              </div>
            </RetroCard>
          </div>
        </div>
      </section>

      {/* ══ WHO IT'S FOR SECTION ══ */}
      <section className="w-full px-4 md:px-6 lg:px-8 py-16 md:py-20">
        <div className="max-w-4xl mx-auto">
          {/* Title */}
          <h2 className="font-heading text-3xl md:text-4xl font-bold text-text text-center mb-12">
            Built for Your Team
          </h2>

          {/* Two Persona Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <RetroCard>
              <div className="space-y-4">
                <h3 className="font-heading text-xl font-semibold text-text">
                  Managers
                </h3>
                <p className="text-sm text-text leading-relaxed">
                  Full visibility into store performance: staff scoring,
                  customer engagement trends, and exportable reports for
                  data-backed decisions.
                </p>
              </div>
            </RetroCard>

            <RetroCard>
              <div className="space-y-4">
                <h3 className="font-heading text-xl font-semibold text-text">
                  Employees
                </h3>
                <p className="text-sm text-text leading-relaxed">
                  A fair, transparent view of performance metrics — built on
                  objective activity data, not subjective judgment.
                </p>
              </div>
            </RetroCard>
          </div>
        </div>
      </section>

      {/* ══ FINAL CTA BAND ══ */}
      <section className="w-full bg-accent px-4 md:px-6 lg:px-8 py-16 md:py-20">
        <div className="max-w-3xl mx-auto text-center space-y-6">
          <h2 className="font-heading text-3xl md:text-4xl font-bold text-surface">
            See RetailPulse in Action
          </h2>
          <p className="text-lg text-surface/90">
            Get started and explore the dashboard with sample data.
          </p>
          <Link href="/signup">
            <RetroButton
              variant="secondary"
              className="!px-8 !py-4 !text-lg !bg-surface !text-accent hover:!brightness-95"
            >
              Get Started
            </RetroButton>
          </Link>
        </div>
      </section>
    </div>
  );
}

/** Hero dashboard preview with graceful fallback */
function HeroDashboardPreview() {
  const [imgError, setImgError] = React.useState(false);

  if (imgError) {
    return (
      <div className="w-full h-64 bg-surface-alt rounded flex items-center justify-center border border-border-soft">
        <p className="text-sm text-text-muted font-mono">Dashboard Preview</p>
      </div>
    );
  }

  return (
    <Image
      src="/hero-dashboard-preview.png"
      alt="RetailPulse Dashboard Preview"
      width={800}
      height={500}
      className="w-full h-auto rounded"
      onError={() => setImgError(true)}
    />
  );
}

/** Small placeholder for dashboard preview in bento grid */
function DashboardPreviewPlaceholder() {
  const [imgError, setImgError] = React.useState(false);

  if (imgError) {
    return <p className="text-xs text-text-muted font-mono">Preview</p>;
  }

  return (
    <Image
      src="/preview-dashboard.png"
      alt="Dashboard preview"
      width={200}
      height={120}
      className="w-full h-auto object-contain rounded"
      onError={() => setImgError(true)}
    />
  );
}
