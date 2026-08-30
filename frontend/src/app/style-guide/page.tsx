import {
  RetroWindow,
  CRTFrame,
  RetroButton,
  RetroInput,
  RetroCard,
  Badge,
} from "@/components/ui";

/* ── Small icon helpers (inline SVGs, no deps) ── */

function SearchIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

/* ── Section wrapper ── */

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-4">
      <h2 className="font-heading text-xl font-bold text-text border-b border-border-soft pb-2">
        {title}
      </h2>
      {children}
    </section>
  );
}

/* ── Page ── */

export default function StyleGuidePage() {
  return (
    <main className="min-h-screen bg-bg p-6 md:p-12 max-w-5xl mx-auto space-y-12">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="font-heading text-3xl md:text-4xl font-bold text-text">
          RetailPulse - Style Guide
        </h1>
        <p className="font-body text-text-muted text-sm">
          Design system components · Elegant Retro OS
        </p>
      </div>

      {/* ─── Color Palette ─── */}
      <Section title="Color Palette">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {[
            { name: "bg", hex: "#EDE0C8" },
            { name: "surface", hex: "#F7EFDD" },
            { name: "surface-alt", hex: "#E4D4B0" },
            { name: "border", hex: "#4A2E1E", light: true },
            { name: "border-soft", hex: "#8B6A4A", light: true },
            { name: "accent", hex: "#C1652F", light: true },
            { name: "accent-hover", hex: "#A6521F", light: true },
            { name: "accent-soft", hex: "#E8B84B" },
            { name: "success", hex: "#4C7A5A", light: true },
            { name: "danger", hex: "#B5432E", light: true },
            { name: "text", hex: "#2E1F14", light: true },
            { name: "text-muted", hex: "#6B5642", light: true },
          ].map(({ name, hex, light }) => (
            <div
              key={name}
              className="rounded-lg border border-border-soft overflow-hidden"
            >
              <div
                className="h-16"
                style={{ backgroundColor: hex }}
              />
              <div className="bg-surface px-3 py-2">
                <p className="font-mono text-[11px] text-text font-semibold">
                  --color-{name}
                </p>
                <p className="font-mono text-[10px] text-text-muted">
                  {hex}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* ─── Typography ─── */}
      <Section title="Typography">
        <div className="space-y-3 bg-surface border border-border-soft rounded-lg p-5">
          <p className="font-heading text-2xl font-bold">
            Space Grotesk - Headings
          </p>
          <p className="font-body text-base">
            Inter - Body text used across the UI. Highly readable at every
            size.
          </p>
          <p className="font-mono text-sm text-text-muted">
            JetBrains Mono - Stats, counters, timestamps, camera labels
          </p>
        </div>
      </Section>

      {/* ─── RetroWindow ─── */}
      <Section title="RetroWindow">
        <div className="grid gap-6 md:grid-cols-2">
          <RetroWindow title="Store Overview">
            <p className="text-sm text-text-muted">
              This is a default RetroWindow with a title bar, traffic-light
              buttons, and content area. It can hold any content.
            </p>
          </RetroWindow>

          <RetroWindow title="⚠ Alert Panel">
            <div className="space-y-2">
              <p className="text-sm font-semibold text-danger">
                2 alerts require attention
              </p>
              <p className="text-sm text-text-muted">
                Unauthorized access detected - Camera 03, 14:32
              </p>
            </div>
          </RetroWindow>
        </div>
      </Section>

      {/* ─── CRTFrame ─── */}
      <Section title="CRTFrame">
        <div className="flex flex-wrap gap-6">
          <CRTFrame label="CAM 01 - ENTRANCE" live>
            <div className="w-64 h-40 bg-gradient-to-br from-neutral-800 to-neutral-900 flex items-center justify-center">
              <span className="text-neutral-500 font-mono text-s">
                LIVE FEED
              </span>
            </div>
          </CRTFrame>

          <CRTFrame label="CAM 04 - CHECKOUT" live signal={false} />
        </div>
      </Section>

      {/* ─── RetroButton ─── */}
      <Section title="RetroButton">
        <div className="flex flex-wrap items-center gap-3">
          <RetroButton variant="primary">Primary Action</RetroButton>
          <RetroButton variant="secondary">Secondary</RetroButton>
          <RetroButton variant="danger">Delete</RetroButton>
          <RetroButton variant="primary" disabled>
            Disabled
          </RetroButton>
        </div>
      </Section>

      {/* ─── RetroInput ─── */}
      <Section title="RetroInput">
        <div className="grid gap-4 max-w-sm">
          <RetroInput placeholder="Search stores…" leadingIcon={<SearchIcon />} />
          <RetroInput placeholder="Enter employee ID" />
          <RetroInput placeholder="Disabled input" disabled />
        </div>
      </Section>

      {/* ─── RetroCard ─── */}
      <Section title="RetroCard">
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
          <RetroCard label="Visitors">
            <p className="font-mono text-3xl font-bold text-text mt-2">
              1,247
            </p>
            <p className="text-xs text-text-muted mt-1">Today</p>
          </RetroCard>

          <RetroCard label="Revenue">
            <p className="font-mono text-3xl font-bold text-accent mt-2">
              $24.8k
            </p>
            <p className="text-xs text-text-muted mt-1">+12% vs yesterday</p>
          </RetroCard>

          <RetroCard>
            <p className="text-sm text-text-muted">
              A card without a label - useful for generic content blocks.
            </p>
          </RetroCard>
        </div>
      </Section>

      {/* ─── Badge ─── */}
      <Section title="Badge">
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="accent">Manager</Badge>
          <Badge variant="success">Online</Badge>
          <Badge variant="danger">Offline</Badge>
          <Badge variant="neutral">Employee</Badge>
        </div>
      </Section>

      {/* ─── Combined Example ─── */}
      <Section title="Combined Example">
        <RetroWindow title="Employee Overview - Store #014">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <RetroInput
                placeholder="Search employees…"
                leadingIcon={<SearchIcon />}
                className="flex-1"
              />
              <RetroButton variant="primary">Add</RetroButton>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <RetroCard label="Total Staff">
                <p className="font-mono text-2xl font-bold mt-2">12</p>
              </RetroCard>
              <RetroCard label="On Shift">
                <p className="font-mono text-2xl font-bold text-success mt-2">
                  8
                </p>
              </RetroCard>
              <RetroCard label="Idle &gt; 15m">
                <p className="font-mono text-2xl font-bold text-danger mt-2">
                  2
                </p>
              </RetroCard>
            </div>

            <div className="flex flex-wrap gap-2">
              <Badge variant="success">Online</Badge>
              <Badge variant="accent">Manager</Badge>
              <Badge variant="neutral">Employee</Badge>
              <Badge variant="danger">Offline</Badge>
            </div>
          </div>
        </RetroWindow>
      </Section>

      {/* Footer */}
      <footer className="text-center text-xs text-text-muted pt-6 border-t border-border-soft">
        RetailPulse Design System · v0.1
      </footer>
    </main>
  );
}
