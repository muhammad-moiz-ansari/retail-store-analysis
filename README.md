# RetailPulse

**Agentic AI for Retail Store Intelligence**

RetailPulse turns existing in-store CCTV footage into a live system for customer engagement analytics, staff performance insight, and store traffic intelligence - without requiring new cameras or hardware. Built as a Final Year Project exploring practical applications of multi-agent AI systems in a real-world, resource-constrained retail environment.

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [System Architecture](#system-architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Scope](#scope)
- [Future Work](#future-work)
- [Team](#team)
- [Acknowledgements](#acknowledgements)
- [License](#license)

---

## Overview

Most retail CCTV systems exist solely for theft prevention - footage is recorded, rarely reviewed, and holds no operational value beyond security. RetailPulse repurposes that same footage using a coordinated set of AI agents to answer questions retail managers actually care about:

- Are customers being approached and helped in a reasonable time?
- Which zones of the store see the most traffic - and the most neglect?
- How is staff performance distributed across a shift?
- Where are the store's actual coverage gaps?

The system is built around a **three-camera setup** (one entrance-facing, two floor-facing) feeding a pipeline of specialized agents, orchestrated to produce a unified, reconciled view of store activity - surfaced through a full-featured web dashboard for managers and a focused workspace for employees.

## Problem Statement

Retail store owners and managers currently have no low-cost way to know:
1. Whether customers on the floor are being attended to.
2. How staff time is actually distributed between active engagement and idle time.
3. Which areas of the store attract traffic - and which are ignored.

Hiring dedicated analysts or installing specialized retail-analytics hardware is often financially out of reach for small and mid-sized retail operations. RetailPulse addresses this using **existing infrastructure and non-GPU-dependent, lightweight computer vision**, making store intelligence accessible without new capital investment.

## System Architecture

RetailPulse is built as a coordinated **multi-agent pipeline**, orchestrated using LangGraph, where each agent owns a distinct responsibility and outputs are reconciled against the same tracked entities before reaching the dashboard.

```
Camera Feeds
    │
    ▼
Detection Agent          - person detection per frame (YOLO-based)
    │
    ▼
Classification Agent     - staff vs. customer classification (zone/appearance heuristic, non-biometric)
    │
    ▼
Engagement Agent         - interaction duration, approach time, idle detection
    │
    ▼
Trajectory Agent         - movement paths, zone dwell time, heatmap generation
    │
    ▼
Orchestrator             - reconciles all agent outputs per tracked entity, resolves conflicts
    │
    ▼
Dashboard Output          → Next.js frontend

Insight Narration Agent  - generates natural-language report summaries (on-demand)
```

This architecture is visualized live in the app's **System Status** page, which shows real-time (mock, in the current frontend-only build) agent health, throughput, and an activity log.

## Features

### Manager-facing
- **Dashboard** - live view of all 3 camera feeds with real-time text overlays for footfall, engagement, and trajectory data
- **Customer Info** - traffic/footfall metrics, service quality (attended vs. unattended ratio, response time, interaction duration), spatial behavior (dwell time, shopper behavior split, top paths)
- **Employee Info** - store-wide staff score, activity leaderboard, responsiveness charts, idle time and floor coverage, zone-by-zone performance
- **Spatial Analytics** - heatmaps and movement pattern analysis
- **Sales & Product Trends** - POS-driven product and category performance
- **Reports & Exports** - configurable report builder with AI-generated narrative summaries, exported as a downloadable PDF (via jsPDF)
- **Alerts & Notifications** - unified, filterable feed of active/resolved system alerts (unattended customers, unstaffed zones, idle spikes, traffic anomalies)
- **System Status** - live agent pipeline visualization, per-agent health, and activity log
- **Store Settings** - system configuration
- **Profile** - account details, password management, notification preferences

### Employee-facing
- **My Workspace** - shift overview, today's score, 7-day performance trend, zone assignment, shift updates
- **My Performance** - full personal performance history with rubric breakdown, score trend charts, and a clickable daily log
- **Profile** - shared with Manager role, scoped to employee-relevant fields

### Shared
- **Landing Page** - public marketing/pitch page (problem → solution → how it works → capabilities)
- **Login / Signup** - role-aware authentication (Manager / Employee)
- **About** - system explanation and contact information

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router), React |
| Styling | Tailwind CSS, custom retro-industrial design system |
| Charts | Recharts |
| PDF Export | jsPDF |
| Computer Vision | YOLO-based detection (lightweight, non-GPU-dependent) |
| Agent Orchestration | LangGraph |
| Fonts | Space Grotesk (headings), Inter (body), JetBrains Mono (stats/data) |

> **Note:** the current build is frontend-first - CV pipeline and agent orchestration are represented in the UI (System Status page) with mock data while the backend integration is developed in parallel.

## Project Structure

```
retailpulse/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx             # Landing page (/)
│   │   ├── login/
│   │   ├── signup/
│   │   ├── dashboard/
│   │   ├── customer-info/
│   │   ├── employee-info/
│   │   ├── spatial-analytics/
│   │   ├── sales-trends/
│   │   ├── reports/
│   │   ├── alerts/
│   │   ├── system-status/
│   │   ├── store-settings/
│   │   ├── employee-home/
│   │   ├── my-performance/
│   │   ├── profile/
│   │   └── about/
│   ├── components/
│   │   └── ui/                 # RetroWindow, RetroCard, RetroButton, Navbar, Footer
│   └── lib/                    # Helpers (e.g. PDF generation)
├── public/
│   └── logo.png
├── package.json
└── README.md
```

*(Update this section to match your actual repo layout if it has diverged.)*

## Getting Started

### Prerequisites
- Node.js 18+
- npm

### Installation

```bash
git clone <repo-url>
cd retailpulse
npm install
```

### Running locally

```bash
npm run dev
```

The app will be available at `http://localhost:3000`.

### Build for production

```bash
npm run build
npm start
```

## Scope

To fit within the project timeline and available hardware (no dedicated GPU), the following scope was deliberately committed to after a feasibility triage against hardware, timeline, and dependency constraints:

**In scope:**
- Footfall counting (entrance camera)
- Staff/customer classification (non-biometric, zone/appearance-based)
- Engagement analytics (approach time, interaction duration, idle detection, unattended flagging, employee scoring)
- Trajectory & spatial behavior (path tracking, zone dwell time, heatmaps, crowd density)

**Explicitly descoped (see Future Work):**
- Multi-camera identity linking (Global Master ID / cross-camera re-identification)
- Direct POS integration for a live purchase-conversion funnel
- Shelf-level product interaction detection
- Long-term store layout / promotional-effectiveness evaluation

## Future Work

- **Pilot deployment** with a real retail partner (e.g. Imtiaz, Punjab Cash & Carry, Max Mart) to validate against live store conditions
- **Multi-store scaling** beyond the single-store prototype
- **Multi-camera identity linking** for full cross-camera customer tracking
- **POS integration** for a true footfall-to-purchase conversion funnel
- **Shelf-level interaction detection**
- **Real-time dashboard** as the primary deliverable (currently offline/batch processing)
- **Expanded agent layer** - additional reasoning agents (anomaly detection, natural-language querying over store data)

## Team

| Name | Role |
|---|---|
| *[Your name]* | *[Role]* |
| *[Teammate name]* | *[Role]* |

**Supervisor:** *[Supervisor name]*

## Acknowledgements

- Otterbring, F. (2024) - field research on employee proactivity and customer purchase behavior, referenced in the project's motivation and literature review
- Harter, J. K. et al. (2002) - meta-analysis on employee engagement and business outcomes

## License

*Academic project - all rights reserved*

---

*This project was developed as a Final Year Project. It demonstrates a multi-agent AI system applied to a real-world retail analytics problem, with emphasis on hardware-constrained deployment, non-biometric privacy-conscious design, and manager decision-support rather than automated employee evaluation.*
