"use client";

import React, { useState, FormEvent } from "react";
import Link from "next/link";
import {
  RetroWindow,
  RetroCard,
  RetroButton,
  RetroInput,
  Badge,
} from "@/components/ui";

/* ═══════════════════════════════════════════════════════════════
   Role gate — hardcoded to "Manager" to match NavbarShell.
   Employee users who navigate here directly see an access-denied
   screen instead of the settings content.
   ═══════════════════════════════════════════════════════════════ */

const CURRENT_ROLE: "Manager" | "Employee" = "Manager";

/* ═══════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════ */

interface Camera {
  id: string;
  name: string;
  zone: string;
  online: boolean;
}

interface Zone {
  id: string;
  name: string;
  type: "Entry/Exit" | "Aisle" | "Display" | "Checkout";
  capacity: number;
}

interface StaffMember {
  id: string;
  label: string;
  zone: string;
  shift: string;
}

interface Account {
  id: string;
  name: string;
  email: string;
  role: "Manager" | "Employee";
  active: boolean;
}

/* ═══════════════════════════════════════════════════════════════
   Initial mock data
   ═══════════════════════════════════════════════════════════════ */

const INITIAL_ZONES: Zone[] = [
  { id: "z1", name: "Entrance Lobby", type: "Entry/Exit", capacity: 15 },
  { id: "z2", name: "Aisle 1 — Snacks", type: "Aisle", capacity: 10 },
  { id: "z3", name: "Aisle 2 — Beverages", type: "Aisle", capacity: 10 },
  { id: "z4", name: "Aisle 3 — Household", type: "Aisle", capacity: 12 },
  { id: "z5", name: "Promo Display", type: "Display", capacity: 8 },
  { id: "z6", name: "Checkout Counter", type: "Checkout", capacity: 20 },
];

const INITIAL_CAMERAS: Camera[] = [
  { id: "c1", name: "CAM 01 — ENTRANCE", zone: "Entrance Lobby", online: true },
  { id: "c2", name: "CAM 02 — AISLE 1", zone: "Aisle 1 — Snacks", online: true },
  { id: "c3", name: "CAM 03 — CHECKOUT", zone: "Checkout Counter", online: true },
];

const INITIAL_STAFF: StaffMember[] = [
  { id: "s1", label: "Staff 01", zone: "Aisle 1 — Snacks", shift: "9 AM – 1 PM" },
  { id: "s2", label: "Staff 02", zone: "Checkout Counter", shift: "9 AM – 1 PM" },
  { id: "s3", label: "Staff 03", zone: "Promo Display", shift: "1 PM – 5 PM" },
  { id: "s4", label: "Staff 04", zone: "Aisle 2 — Beverages", shift: "1 PM – 5 PM" },
  { id: "s5", label: "Staff 05", zone: "Aisle 3 — Household", shift: "5 PM – 9 PM" },
];

const INITIAL_ACCOUNTS: Account[] = [
  { id: "a1", name: "Ahmed Raza", email: "ahmed.raza@retailpulse.com", role: "Manager", active: true },
  { id: "a2", name: "Sara Khan", email: "sara.khan@retailpulse.com", role: "Employee", active: true },
  { id: "a3", name: "Bilal Hussain", email: "bilal.hussain@retailpulse.com", role: "Employee", active: true },
];

const SHIFT_OPTIONS = ["9 AM – 1 PM", "1 PM – 5 PM", "5 PM – 9 PM"];
const ZONE_TYPE_OPTIONS: Zone["type"][] = ["Entry/Exit", "Aisle", "Display", "Checkout"];
const RETENTION_OPTIONS = ["30 days", "60 days", "90 days"];

/* ═══════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════ */

let nextId = 100;
function uid() {
  return `_${++nextId}`;
}

/* ═══════════════════════════════════════════════════════════════
   Page Component
   ═══════════════════════════════════════════════════════════════ */

export default function SettingsPage() {
  /* ── Role guard ── */
  if (CURRENT_ROLE !== "Manager") {
    return <AccessRestricted />;
  }

  return <SettingsContent />;
}

/* ═══════════════════════════════════════════════════════════════
   Access-Restricted screen (Employee role guard)
   ═══════════════════════════════════════════════════════════════ */

function AccessRestricted() {
  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <RetroWindow title="Access Restricted" className="w-full max-w-md">
        <div className="text-center space-y-4">
          <p className="font-body text-sm text-text">
            Store Settings is available to Managers only.
          </p>
          <Link href="/dashboard">
            <RetroButton variant="secondary">← Back to Dashboard</RetroButton>
          </Link>
        </div>
      </RetroWindow>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Main Settings Content (Manager view)
   ═══════════════════════════════════════════════════════════════ */

function SettingsContent() {
  /* ── Shared zone state (used by Cameras, Zones, and Staff) ── */
  const [zones, setZones] = useState<Zone[]>(INITIAL_ZONES);

  return (
    <main className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-6 md:py-8 space-y-8">
      {/* ── Page Header ── */}
      <RetroWindow title="Store Settings — Configuration & Management">
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="accent">Manager Access</Badge>
          <span className="text-sm text-text-muted">
            Changes here affect what staff and customers see across the dashboard.
          </span>
        </div>
      </RetroWindow>

      {/* ── Section 1: Camera Management ── */}
      <CameraManagement zones={zones} />

      {/* ── Section 2: Zone Management ── */}
      <ZoneManagement zones={zones} setZones={setZones} />

      {/* ── Section 3: Staff Shift Assignment ── */}
      <StaffShifts zones={zones} />

      {/* ── Section 4: Alert & Threshold Configuration ── */}
      <AlertThresholds />

      {/* ── Section 5: User & Account Management ── */}
      <AccountManagement />

      {/* ── Section 6: Data & Privacy Settings ── */}
      <DataPrivacy />
    </main>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 1 — Camera Management
   ═══════════════════════════════════════════════════════════════ */

function CameraManagement({ zones }: { zones: Zone[] }) {
  const [cameras, setCameras] = useState<Camera[]>(INITIAL_CAMERAS);
  const [newName, setNewName] = useState("");
  const [newZone, setNewZone] = useState(zones[0]?.name ?? "");

  function handleRemove(id: string) {
    if (window.confirm("Remove this camera from the system?")) {
      setCameras((prev) => prev.filter((c) => c.id !== id));
    }
  }

  function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setCameras((prev) => [
      ...prev,
      { id: uid(), name: newName.trim(), zone: newZone, online: false },
    ]);
    setNewName("");
  }

  return (
    <RetroWindow title="Cameras">
      {/* Camera list */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {cameras.map((cam) => (
          <RetroCard key={cam.id} label={cam.name}>
            <div className="pt-2 space-y-2">
              <p className="text-xs text-text-muted font-mono">
                Zone: <span className="text-text">{cam.zone}</span>
              </p>
              <div className="flex items-center justify-between">
                <Badge variant={cam.online ? "success" : "neutral"}>
                  {cam.online ? "Online" : "Offline"}
                </Badge>
                <RetroButton
                  variant="danger"
                  className="!px-2.5 !py-1 !text-xs"
                  onClick={() => handleRemove(cam.id)}
                >
                  Remove
                </RetroButton>
              </div>
            </div>
          </RetroCard>
        ))}
        {cameras.length === 0 && (
          <p className="text-sm text-text-muted col-span-full italic">
            No cameras configured. Add one below.
          </p>
        )}
      </div>

      {/* Add Camera form */}
      <RetroCard label="Add Camera">
        <form onSubmit={handleAdd} className="pt-2 flex flex-col sm:flex-row items-end gap-3">
          <RetroInput
            label="Camera Name"
            placeholder="e.g. CAM 04 — STOCKROOM"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <div className="w-full sm:w-auto">
            <label className="block mb-1.5 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
              Assign to Zone
            </label>
            <select
              value={newZone}
              onChange={(e) => setNewZone(e.target.value)}
              className="w-full rounded-md border-2 border-border-soft bg-surface px-3 py-2 font-body text-sm text-text shadow-[inset_1px_2px_4px_rgba(74,46,30,0.15)] focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors"
            >
              {zones.map((z) => (
                <option key={z.id} value={z.name}>
                  {z.name}
                </option>
              ))}
            </select>
          </div>
          <RetroButton type="submit" variant="primary" className="shrink-0">
            Add Camera
          </RetroButton>
        </form>
      </RetroCard>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 2 — Zone Management
   ═══════════════════════════════════════════════════════════════ */

function ZoneManagement({
  zones,
  setZones,
}: {
  zones: Zone[];
  setZones: React.Dispatch<React.SetStateAction<Zone[]>>;
}) {
  const [savedRows, setSavedRows] = useState<Record<string, boolean>>({});
  const [newZoneName, setNewZoneName] = useState("");
  const [newZoneType, setNewZoneType] = useState<Zone["type"]>("Aisle");
  const [newZoneCap, setNewZoneCap] = useState("10");

  function handleCapacityChange(id: string, value: number) {
    setZones((prev) =>
      prev.map((z) => (z.id === id ? { ...z, capacity: value } : z))
    );
  }

  function handleSaveRow(id: string) {
    setSavedRows((prev) => ({ ...prev, [id]: true }));
    setTimeout(() => {
      setSavedRows((prev) => ({ ...prev, [id]: false }));
    }, 1500);
  }

  function handleAddZone(e: FormEvent) {
    e.preventDefault();
    if (!newZoneName.trim()) return;
    setZones((prev) => [
      ...prev,
      {
        id: uid(),
        name: newZoneName.trim(),
        type: newZoneType,
        capacity: parseInt(newZoneCap) || 10,
      },
    ]);
    setNewZoneName("");
    setNewZoneCap("10");
  }

  return (
    <RetroWindow title="Zones">
      <RetroCard>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-border-soft text-left">
                <th className="py-2 pr-4 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Zone Name
                </th>
                <th className="py-2 pr-4 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Type
                </th>
                <th className="py-2 pr-4 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Capacity Threshold
                </th>
                <th className="py-2 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {zones.map((zone) => (
                <tr key={zone.id} className="border-b border-border-soft/50">
                  <td className="py-2.5 pr-4 font-mono text-xs text-text">
                    {zone.name}
                  </td>
                  <td className="py-2.5 pr-4 text-xs text-text-muted">
                    {zone.type}
                  </td>
                  <td className="py-2.5 pr-4">
                    <input
                      type="number"
                      min={1}
                      value={zone.capacity}
                      onChange={(e) =>
                        handleCapacityChange(zone.id, parseInt(e.target.value) || 0)
                      }
                      className="w-20 rounded-md border-2 border-border-soft bg-surface px-2 py-1 font-mono text-xs text-text shadow-[inset_1px_2px_4px_rgba(74,46,30,0.15)] focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors"
                    />
                  </td>
                  <td className="py-2.5">
                    <RetroButton
                      variant="secondary"
                      className="!px-2.5 !py-1 !text-xs"
                      onClick={() => handleSaveRow(zone.id)}
                    >
                      {savedRows[zone.id] ? (
                        <span className="text-success">✓ Saved</span>
                      ) : (
                        "Save"
                      )}
                    </RetroButton>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </RetroCard>

      {/* Add Zone form */}
      <RetroCard label="Add Zone" className="mt-4">
        <form onSubmit={handleAddZone} className="pt-2 flex flex-col sm:flex-row items-end gap-3">
          <RetroInput
            label="Zone Name"
            placeholder="e.g. Storage Room"
            value={newZoneName}
            onChange={(e) => setNewZoneName(e.target.value)}
          />
          <div className="w-full sm:w-auto">
            <label className="block mb-1.5 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
              Type
            </label>
            <select
              value={newZoneType}
              onChange={(e) => setNewZoneType(e.target.value as Zone["type"])}
              className="w-full rounded-md border-2 border-border-soft bg-surface px-3 py-2 font-body text-sm text-text shadow-[inset_1px_2px_4px_rgba(74,46,30,0.15)] focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors"
            >
              {ZONE_TYPE_OPTIONS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <RetroInput
            label="Capacity"
            type="number"
            min={1}
            value={newZoneCap}
            onChange={(e) => setNewZoneCap(e.target.value)}
            className="!w-24"
          />
          <RetroButton type="submit" variant="primary" className="shrink-0">
            Add Zone
          </RetroButton>
        </form>
      </RetroCard>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 3 — Staff Shift Assignment
   ═══════════════════════════════════════════════════════════════ */

function StaffShifts({ zones }: { zones: Zone[] }) {
  const [staff, setStaff] = useState<StaffMember[]>(INITIAL_STAFF);
  const [savedRows, setSavedRows] = useState<Record<string, boolean>>({});

  function updateStaff(id: string, field: "zone" | "shift", value: string) {
    setStaff((prev) =>
      prev.map((s) => (s.id === id ? { ...s, [field]: value } : s))
    );
  }

  function handleSaveRow(id: string) {
    setSavedRows((prev) => ({ ...prev, [id]: true }));
    setTimeout(() => {
      setSavedRows((prev) => ({ ...prev, [id]: false }));
    }, 1500);
  }

  function handleAddStaff() {
    const nextNum = staff.length + 1;
    const label = `Staff ${String(nextNum).padStart(2, "0")}`;
    setStaff((prev) => [
      ...prev,
      { id: uid(), label, zone: "", shift: "" },
    ]);
  }

  return (
    <RetroWindow title="Staff Shifts">
      <RetroCard>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-border-soft text-left">
                <th className="py-2 pr-4 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Staff ID
                </th>
                <th className="py-2 pr-4 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Assigned Zone
                </th>
                <th className="py-2 pr-4 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Shift
                </th>
                <th className="py-2 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {staff.map((s) => (
                <tr key={s.id} className="border-b border-border-soft/50">
                  <td className="py-2.5 pr-4 font-mono text-xs text-text font-semibold">
                    {s.label}
                  </td>
                  <td className="py-2.5 pr-4">
                    <select
                      value={s.zone}
                      onChange={(e) => updateStaff(s.id, "zone", e.target.value)}
                      className="w-full min-w-[160px] rounded-md border-2 border-border-soft bg-surface px-2 py-1 font-body text-xs text-text shadow-[inset_1px_2px_4px_rgba(74,46,30,0.15)] focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors"
                    >
                      <option value="">— Select Zone —</option>
                      {zones.map((z) => (
                        <option key={z.id} value={z.name}>
                          {z.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2.5 pr-4">
                    <select
                      value={s.shift}
                      onChange={(e) => updateStaff(s.id, "shift", e.target.value)}
                      className="w-full min-w-[130px] rounded-md border-2 border-border-soft bg-surface px-2 py-1 font-body text-xs text-text shadow-[inset_1px_2px_4px_rgba(74,46,30,0.15)] focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors"
                    >
                      <option value="">— Select Shift —</option>
                      {SHIFT_OPTIONS.map((sh) => (
                        <option key={sh} value={sh}>
                          {sh}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2.5">
                    <RetroButton
                      variant="secondary"
                      className="!px-2.5 !py-1 !text-xs"
                      onClick={() => handleSaveRow(s.id)}
                    >
                      {savedRows[s.id] ? (
                        <span className="text-success">✓ Saved</span>
                      ) : (
                        "Save"
                      )}
                    </RetroButton>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4">
          <RetroButton variant="primary" onClick={handleAddStaff}>
            Add Staff Member
          </RetroButton>
        </div>
      </RetroCard>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 4 — Alert & Threshold Configuration
   ═══════════════════════════════════════════════════════════════ */

function AlertThresholds() {
  const [responseTime, setResponseTime] = useState("2");
  const [waitThreshold, setWaitThreshold] = useState("3");
  const [crowdDensity, setCrowdDensity] = useState("85");
  const [notifyMode, setNotifyMode] = useState<"any" | "senior">("any");
  const [saved, setSaved] = useState(false);

  function handleSave() {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <RetroWindow title="Alert Thresholds">
      <p className="text-sm text-text-muted mb-5">
        These thresholds control the targets and alerts shown across the dashboard.
      </p>

      {/* Three threshold cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
        <RetroCard label="Response Time">
          <div className="pt-2 space-y-2">
            <RetroInput
              label="Target (minutes)"
              type="number"
              min={1}
              value={responseTime}
              onChange={(e) => setResponseTime(e.target.value)}
            />
            <p className="text-xs text-text-muted">
              minutes — time to first approach
            </p>
            <p className="text-[10px] text-text-muted italic">
              Currently used as the target line on Employee Info.
            </p>
          </div>
        </RetroCard>

        <RetroCard label="Unattended Wait">
          <div className="pt-2 space-y-2">
            <RetroInput
              label="Threshold (minutes)"
              type="number"
              min={1}
              value={waitThreshold}
              onChange={(e) => setWaitThreshold(e.target.value)}
            />
            <p className="text-xs text-text-muted">
              minutes before a customer is flagged unattended
            </p>
          </div>
        </RetroCard>

        <RetroCard label="Crowd Density">
          <div className="pt-2 space-y-2">
            <RetroInput
              label="Alert Threshold (%)"
              type="number"
              min={1}
              max={100}
              value={crowdDensity}
              onChange={(e) => setCrowdDensity(e.target.value)}
            />
            <p className="text-xs text-text-muted">
              % of zone capacity before a Crowded alert fires on Spatial Analytics
            </p>
          </div>
        </RetroCard>
      </div>

      {/* Notification routing toggle */}
      <RetroCard label="Unattended Notification Routing" className="mb-5">
        <div className="pt-2 space-y-3">
          <div className="flex rounded-md overflow-hidden border-2 border-border">
            <button
              type="button"
              onClick={() => setNotifyMode("any")}
              className={[
                "flex-1 px-4 py-2 font-heading text-sm font-semibold tracking-wide transition-colors cursor-pointer select-none",
                notifyMode === "any"
                  ? "bg-accent text-surface"
                  : "bg-surface text-text hover:bg-surface-alt",
              ].join(" ")}
            >
              Notify Any Available Staff
            </button>
            <div className="w-[2px] bg-border" />
            <button
              type="button"
              onClick={() => setNotifyMode("senior")}
              className={[
                "flex-1 px-4 py-2 font-heading text-sm font-semibold tracking-wide transition-colors cursor-pointer select-none",
                notifyMode === "senior"
                  ? "bg-accent text-surface"
                  : "bg-surface text-text hover:bg-surface-alt",
              ].join(" ")}
            >
              Notify Senior Staff Only
            </button>
          </div>
          <p className="text-xs text-text-muted">
            Determines who is alerted when a customer is flagged unattended.
          </p>
        </div>
      </RetroCard>

      {/* Save button */}
      <div className="flex items-center gap-3">
        <RetroButton variant="primary" onClick={handleSave}>
          Save Thresholds
        </RetroButton>
        {saved && (
          <span className="text-sm font-semibold text-success">
            ✓ Thresholds saved
          </span>
        )}
      </div>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 5 — User & Account Management
   ═══════════════════════════════════════════════════════════════ */

function AccountManagement() {
  const [accounts, setAccounts] = useState<Account[]>(INITIAL_ACCOUNTS);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"Manager" | "Employee">("Employee");
  const [inviteMsg, setInviteMsg] = useState("");

  function handleDeactivate(id: string) {
    setAccounts((prev) =>
      prev.map((a) => (a.id === id ? { ...a, active: false } : a))
    );
  }

  function handleInvite(e: FormEvent) {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setInviteMsg(`Invite sent to ${inviteEmail.trim()}`);
    setInviteEmail("");
    setTimeout(() => setInviteMsg(""), 3000);
  }

  return (
    <RetroWindow title="Accounts">
      <RetroCard>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b-2 border-border-soft text-left">
                <th className="py-2 pr-4 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Name
                </th>
                <th className="py-2 pr-4 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Email
                </th>
                <th className="py-2 pr-4 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Role
                </th>
                <th className="py-2 pr-4 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Status
                </th>
                <th className="py-2 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((acct) => (
                <tr key={acct.id} className="border-b border-border-soft/50">
                  <td className="py-2.5 pr-4 text-text font-semibold">
                    {acct.name}
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-xs text-text-muted">
                    {acct.email}
                  </td>
                  <td className="py-2.5 pr-4">
                    <Badge variant={acct.role === "Manager" ? "accent" : "neutral"}>
                      {acct.role}
                    </Badge>
                  </td>
                  <td className="py-2.5 pr-4">
                    <Badge variant={acct.active ? "success" : "danger"}>
                      {acct.active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td className="py-2.5">
                    {acct.active && (
                      <RetroButton
                        variant="danger"
                        className="!px-2.5 !py-1 !text-xs"
                        onClick={() => handleDeactivate(acct.id)}
                      >
                        Deactivate
                      </RetroButton>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </RetroCard>

      {/* Invite form */}
      <RetroCard label="Invite New User" className="mt-4">
        <form onSubmit={handleInvite} className="pt-2 flex flex-col sm:flex-row items-end gap-3">
          <RetroInput
            label="Email"
            type="email"
            placeholder="colleague@retailpulse.com"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
          />
          <div className="w-full sm:w-auto">
            <label className="block mb-1.5 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
              Role
            </label>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as "Manager" | "Employee")}
              className="w-full rounded-md border-2 border-border-soft bg-surface px-3 py-2 font-body text-sm text-text shadow-[inset_1px_2px_4px_rgba(74,46,30,0.15)] focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors"
            >
              <option value="Employee">Employee</option>
              <option value="Manager">Manager</option>
            </select>
          </div>
          <RetroButton type="submit" variant="primary" className="shrink-0">
            Send Invite
          </RetroButton>
        </form>
        {inviteMsg && (
          <p className="mt-3 text-sm font-semibold text-success">
            ✓ {inviteMsg}
          </p>
        )}
      </RetroCard>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 6 — Data & Privacy Settings
   ═══════════════════════════════════════════════════════════════ */

function DataPrivacy() {
  const [retention, setRetention] = useState("60 days");
  const [saved, setSaved] = useState(false);

  function handleSave() {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <RetroWindow title="Data & Privacy">
      <div className="space-y-5">
        {/* Anonymized tracking — locked ON */}
        <RetroCard label="Anonymized Tracking">
          <div className="pt-2 flex items-start gap-3">
            {/* Locked toggle */}
            <div
              className="shrink-0 mt-0.5 relative w-10 h-5 rounded-full bg-success/30 border border-success/40 cursor-not-allowed opacity-70"
              title="This setting is locked"
            >
              <div className="absolute right-0.5 top-0.5 w-4 h-4 rounded-full bg-success shadow-sm" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-text flex items-center gap-1.5">
                🔒 Anonymized Customer Tracking — Always On
              </p>
              <p className="text-xs text-text-muted leading-relaxed">
                RetailPulse does not store facial recognition data or persistent
                biometric identifiers. This is a core design principle, not a
                configurable setting.
              </p>
            </div>
          </div>
        </RetroCard>

        {/* Data retention — configurable */}
        <RetroCard label="Data Retention">
          <div className="pt-2 space-y-2">
            <label className="block mb-1.5 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
              Retention Period
            </label>
            <select
              value={retention}
              onChange={(e) => setRetention(e.target.value)}
              className="w-full max-w-xs rounded-md border-2 border-border-soft bg-surface px-3 py-2 font-body text-sm text-text shadow-[inset_1px_2px_4px_rgba(74,46,30,0.15)] focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors"
            >
              {RETENTION_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            <p className="text-xs text-text-muted">
              How long tracking event data is kept before automatic deletion.
            </p>
          </div>
        </RetroCard>

        {/* Save button */}
        <div className="flex items-center gap-3">
          <RetroButton variant="primary" onClick={handleSave}>
            Save Privacy Settings
          </RetroButton>
          {saved && (
            <span className="text-sm font-semibold text-success">
              ✓ Privacy settings saved
            </span>
          )}
        </div>
      </div>
    </RetroWindow>
  );
}
