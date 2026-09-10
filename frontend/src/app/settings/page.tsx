"use client";

import React, { useEffect, useState, FormEvent } from "react";
import Link from "next/link";
import { useAuth } from "@/components/auth/AuthProvider";
import {
  RetroWindow,
  RetroCard,
  RetroButton,
  RetroInput,
  Badge,
} from "@/components/ui";

/* ═══════════════════════════════════════════════════════════════
   Role gate - hardcoded to "Manager" to match NavbarShell.
   Employee users who navigate here directly see an access-denied
   screen instead of the settings content.
   ═══════════════════════════════════════════════════════════════ */

/* ═══════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════ */

interface Camera {
  id: string;
  name: string;
  zone: string;
  zoneId?: string;
  online: boolean;
}

interface Zone {
  id: string;
  name: string;
  type: "Entry/Exit" | "Aisle" | "Display" | "Checkout";
  capacity: number;
  minStaff?: number;
}

interface StaffMember {
  id: string;
  userId?: string;
  label: string;
  zone: string;
  zoneId?: string;
  shift: string;
  available?: boolean;
}

interface Account {
  id: string;
  name: string;
  email: string;
  role: "Manager" | "Employee";
  active: boolean;
}

interface SettingsSnapshot {
  zones: Zone[];
  cameras: Camera[];
  staff: StaffMember[];
  accounts: Account[];
  thresholds: {
    responseTimeMinutes?: number;
    unattendedWaitMinutes?: number;
    crowdDensityPercent?: number;
    notifyMode?: "any" | "senior";
    dispatchPaused?: boolean;
  };
  privacy: {
    retentionDays?: number;
  };
}

type SaveSettings = (
  path: string,
  init: RequestInit,
  fallbackMessage?: string
) => Promise<SettingsSnapshot & { invitation?: { token: string; email: string; role: string; expiresAt: string } }>;

/* ═══════════════════════════════════════════════════════════════
   Initial mock data
   ═══════════════════════════════════════════════════════════════ */

const INITIAL_ZONES: Zone[] = [
  { id: "z1", name: "Entrance Lobby", type: "Entry/Exit", capacity: 15 },
  { id: "z2", name: "Aisle 1 - Snacks", type: "Aisle", capacity: 10 },
  { id: "z3", name: "Aisle 2 - Beverages", type: "Aisle", capacity: 10 },
  { id: "z4", name: "Aisle 3 - Household", type: "Aisle", capacity: 12 },
  { id: "z5", name: "Promo Display", type: "Display", capacity: 8 },
  { id: "z6", name: "Checkout Counter", type: "Checkout", capacity: 20 },
];

const INITIAL_CAMERAS: Camera[] = [
  { id: "c1", name: "CAM 01 - ENTRANCE", zone: "Entrance Lobby", online: true },
  { id: "c2", name: "CAM 02 - AISLE 1", zone: "Aisle 1 - Snacks", online: true },
  { id: "c3", name: "CAM 03 - CHECKOUT", zone: "Checkout Counter", online: true },
];

const INITIAL_STAFF: StaffMember[] = [
  { id: "s1", label: "Staff 01", zone: "Aisle 1 - Snacks", shift: "9 AM – 1 PM" },
  { id: "s2", label: "Staff 02", zone: "Checkout Counter", shift: "9 AM – 1 PM" },
  { id: "s3", label: "Staff 03", zone: "Promo Display", shift: "1 PM – 5 PM" },
  { id: "s4", label: "Staff 04", zone: "Aisle 2 - Beverages", shift: "1 PM – 5 PM" },
  { id: "s5", label: "Staff 05", zone: "Aisle 3 - Household", shift: "5 PM – 9 PM" },
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
   Page Component
   ═══════════════════════════════════════════════════════════════ */

export default function SettingsPage() {
  /* ── Role guard ── */
  const { ready, role } = useAuth();

  if (!ready) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center px-4">
        <RetroWindow title="Loading Settings" className="w-full max-w-md">
          <p className="font-body text-sm text-text-muted text-center">
            Loading your manager session...
          </p>
        </RetroWindow>
      </div>
    );
  }

  if (role !== "Manager") {
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
  const [snapshot, setSnapshot] = useState<SettingsSnapshot>({
    zones: INITIAL_ZONES,
    cameras: INITIAL_CAMERAS,
    staff: INITIAL_STAFF,
    accounts: INITIAL_ACCOUNTS,
    thresholds: {
      responseTimeMinutes: 2,
      unattendedWaitMinutes: 3,
      crowdDensityPercent: 85,
      notifyMode: "any",
    },
    privacy: { retentionDays: 60 },
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadSettings() {
    setError("");
    const response = await fetch("/api/backend/settings", { cache: "no-store" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || data.detail || "Unable to load settings");
    }
    setSnapshot(data);
  }

  async function saveSettings(
    path: string,
    init: RequestInit,
    fallbackMessage = "Settings update failed"
  ) {
    setError("");
    const response = await fetch(`/api/backend/${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init.headers || {}) },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || data.detail || fallbackMessage);
    }
    setSnapshot(data);
    return data;
  }

  useEffect(() => {
    loadSettings()
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load settings"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-6 md:py-8 space-y-8">
      {/* ── Page Header ── */}
      <RetroWindow title="Store Settings - Configuration & Management">
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="accent">Manager Access</Badge>
          <span className="text-sm text-text-muted">
            Changes here are saved to the RetailPulse demo backend.
          </span>
        </div>
      </RetroWindow>

      {(loading || error) && (
        <RetroWindow title="Backend Connection">
          <p className={`text-sm ${error ? "text-danger" : "text-text-muted"}`}>
            {error || "Loading saved store configuration..."}
          </p>
        </RetroWindow>
      )}

      {/* ── Section 1: Camera Management ── */}
      <CameraManagement
        zones={snapshot.zones}
        cameras={snapshot.cameras}
        saveSettings={saveSettings}
      />

      {/* ── Section 2: Zone Management ── */}
      <ZoneManagement
        zones={snapshot.zones}
        saveSettings={saveSettings}
        setSnapshot={setSnapshot}
      />

      {/* ── Section 3: Staff Shift Assignment ── */}
      <StaffShifts
        zones={snapshot.zones}
        staff={snapshot.staff}
        saveSettings={saveSettings}
        setSnapshot={setSnapshot}
      />

      {/* ── Section 4: Alert & Threshold Configuration ── */}
      <AlertThresholds thresholds={snapshot.thresholds} saveSettings={saveSettings} />

      {/* ── Section 5: User & Account Management ── */}
      <AccountManagement accounts={snapshot.accounts} saveSettings={saveSettings} />

      {/* ── Section 6: Data & Privacy Settings ── */}
      <DataPrivacy privacy={snapshot.privacy} saveSettings={saveSettings} />
    </main>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 1 - Camera Management
   ═══════════════════════════════════════════════════════════════ */

function CameraManagement({
  zones,
  cameras,
  saveSettings,
}: {
  zones: Zone[];
  cameras: Camera[];
  saveSettings: SaveSettings;
}) {
  const [newName, setNewName] = useState("");
  const [newZone, setNewZone] = useState(zones[0]?.id ?? "");
  const [saving, setSaving] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!newZone && zones[0]?.id) setNewZone(zones[0].id);
  }, [newZone, zones]);

  async function handleRemove(id: string) {
    if (!window.confirm("Remove this camera from the system?")) return;
    setSaving(id);
    setError("");
    try {
      await saveSettings(`settings/cameras/${id}`, { method: "DELETE" }, "Camera removal failed");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Camera removal failed");
    } finally {
      setSaving("");
    }
  }

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setSaving("new");
    setError("");
    try {
      await saveSettings(
        "settings/cameras",
        {
          method: "POST",
          body: JSON.stringify({ name: newName.trim(), zoneId: newZone }),
        },
        "Camera creation failed"
      );
      setNewName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Camera creation failed");
    } finally {
      setSaving("");
    }
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
                  disabled={saving === cam.id}
                  onClick={() => handleRemove(cam.id)}
                >
                  {saving === cam.id ? "Removing..." : "Remove"}
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
            placeholder="e.g. CAM 04 - STOCKROOM"
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
                <option key={z.id} value={z.id}>
                  {z.name}
                </option>
              ))}
            </select>
          </div>
          <RetroButton type="submit" variant="primary" className="shrink-0" disabled={saving === "new"}>
            {saving === "new" ? "Adding..." : "Add Camera"}
          </RetroButton>
        </form>
        {error && <p className="mt-3 text-sm font-semibold text-danger">{error}</p>}
      </RetroCard>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 2 - Zone Management
   ═══════════════════════════════════════════════════════════════ */

function ZoneManagement({
  zones,
  saveSettings,
  setSnapshot,
}: {
  zones: Zone[];
  saveSettings: SaveSettings;
  setSnapshot: React.Dispatch<React.SetStateAction<SettingsSnapshot>>;
}) {
  const [savedRows, setSavedRows] = useState<Record<string, boolean>>({});
  const [newZoneName, setNewZoneName] = useState("");
  const [newZoneType, setNewZoneType] = useState<Zone["type"]>("Aisle");
  const [newZoneCap, setNewZoneCap] = useState("10");
  const [error, setError] = useState("");

  function handleCapacityChange(id: string, value: number) {
    setSnapshot((prev) => ({
      ...prev,
      zones: prev.zones.map((z) => (z.id === id ? { ...z, capacity: value } : z)),
    }));
  }

  async function handleSaveRow(zone: Zone) {
    setError("");
    try {
      await saveSettings(
        `settings/zones/${zone.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({ capacity: zone.capacity, minStaff: zone.minStaff ?? 0 }),
        },
        "Zone update failed"
      );
      setSavedRows((prev) => ({ ...prev, [zone.id]: true }));
      setTimeout(() => {
        setSavedRows((prev) => ({ ...prev, [zone.id]: false }));
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Zone update failed");
    }
  }

  async function handleAddZone(e: FormEvent) {
    e.preventDefault();
    if (!newZoneName.trim()) return;
    setError("");
    try {
      await saveSettings(
        "settings/zones",
        {
          method: "POST",
          body: JSON.stringify({
            name: newZoneName.trim(),
            type: newZoneType,
            capacity: parseInt(newZoneCap) || 10,
            minStaff: 0,
          }),
        },
        "Zone creation failed"
      );
      setNewZoneName("");
      setNewZoneCap("10");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Zone creation failed");
    }
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
                      onClick={() => handleSaveRow(zone)}
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
        {error && <p className="mt-3 text-sm font-semibold text-danger">{error}</p>}
      </RetroCard>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 3 - Staff Shift Assignment
   ═══════════════════════════════════════════════════════════════ */

function StaffShifts({
  zones,
  staff,
  saveSettings,
  setSnapshot,
}: {
  zones: Zone[];
  staff: StaffMember[];
  saveSettings: SaveSettings;
  setSnapshot: React.Dispatch<React.SetStateAction<SettingsSnapshot>>;
}) {
  const [savedRows, setSavedRows] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");

  function updateStaff(id: string, field: "zone" | "shift", value: string) {
    setSnapshot((prev) => ({
      ...prev,
      staff: prev.staff.map((s) =>
        s.id === id
          ? {
              ...s,
              [field]: value,
              ...(field === "zone" ? { zoneId: value, zone: zones.find((zone) => zone.id === value)?.name || "" } : {}),
            }
          : s
      ),
    }));
  }

  async function handleSaveRow(member: StaffMember) {
    setError("");
    try {
      await saveSettings(
        `settings/rosters/${member.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({ zoneId: member.zoneId || null, shift: member.shift, available: member.available ?? true }),
        },
        "Roster update failed"
      );
      setSavedRows((prev) => ({ ...prev, [member.id]: true }));
      setTimeout(() => {
        setSavedRows((prev) => ({ ...prev, [member.id]: false }));
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Roster update failed");
    }
  }

  async function handleAddStaff() {
    setError("");
    try {
      await saveSettings(
        "settings/rosters",
        {
          method: "POST",
          body: JSON.stringify({ zoneId: zones[0]?.id || null, shift: SHIFT_OPTIONS[0] }),
        },
        "Roster creation failed"
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Roster creation failed");
    }
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
                      value={s.zoneId || ""}
                      onChange={(e) => updateStaff(s.id, "zone", e.target.value)}
                      className="w-full min-w-[160px] rounded-md border-2 border-border-soft bg-surface px-2 py-1 font-body text-xs text-text shadow-[inset_1px_2px_4px_rgba(74,46,30,0.15)] focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors"
                    >
                      <option value="">- Select Zone -</option>
                      {zones.map((z) => (
                        <option key={z.id} value={z.id}>
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
                      <option value="">- Select Shift -</option>
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
                      onClick={() => handleSaveRow(s)}
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
          {error && <p className="mt-3 text-sm font-semibold text-danger">{error}</p>}
        </div>
      </RetroCard>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 4 - Alert & Threshold Configuration
   ═══════════════════════════════════════════════════════════════ */

function AlertThresholds({
  thresholds,
  saveSettings,
}: {
  thresholds: SettingsSnapshot["thresholds"];
  saveSettings: SaveSettings;
}) {
  const [responseTime, setResponseTime] = useState(String(thresholds.responseTimeMinutes ?? 2));
  const [waitThreshold, setWaitThreshold] = useState(String(thresholds.unattendedWaitMinutes ?? 3));
  const [crowdDensity, setCrowdDensity] = useState(String(thresholds.crowdDensityPercent ?? 85));
  const [notifyMode, setNotifyMode] = useState<"any" | "senior">(thresholds.notifyMode ?? "any");
  const [dispatchPaused, setDispatchPaused] = useState(Boolean(thresholds.dispatchPaused));
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setResponseTime(String(thresholds.responseTimeMinutes ?? 2));
    setWaitThreshold(String(thresholds.unattendedWaitMinutes ?? 3));
    setCrowdDensity(String(thresholds.crowdDensityPercent ?? 85));
    setNotifyMode(thresholds.notifyMode ?? "any");
    setDispatchPaused(Boolean(thresholds.dispatchPaused));
  }, [thresholds]);

  async function handleSave() {
    setError("");
    try {
      await saveSettings(
        "settings/thresholds",
        {
          method: "PUT",
          body: JSON.stringify({
            responseTimeMinutes: parseInt(responseTime) || 2,
            unattendedWaitMinutes: parseInt(waitThreshold) || 3,
            crowdDensityPercent: parseInt(crowdDensity) || 85,
            notifyMode,
            dispatchPaused,
          }),
        },
        "Threshold update failed"
      );
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Threshold update failed");
    }
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
              minutes - time to first approach
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

      <RetroCard label="Automatic Dispatch" className="mb-5">
        <label className="pt-2 flex items-center gap-3 text-sm font-semibold text-text">
          <input
            type="checkbox"
            checked={dispatchPaused}
            onChange={(e) => setDispatchPaused(e.target.checked)}
            className="h-4 w-4 accent-[var(--color-accent)]"
          />
          Pause automatic staff dispatch
        </label>
        <p className="mt-2 text-xs text-text-muted">
          When paused, orchestration events create alerts without assigning staff tasks.
        </p>
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
        {error && <span className="text-sm font-semibold text-danger">{error}</span>}
      </div>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 5 - User & Account Management
   ═══════════════════════════════════════════════════════════════ */

function AccountManagement({
  accounts,
  saveSettings,
}: {
  accounts: Account[];
  saveSettings: SaveSettings;
}) {
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"Manager" | "Employee">("Employee");
  const [inviteMsg, setInviteMsg] = useState("");
  const [error, setError] = useState("");

  async function handleDeactivate(id: string) {
    setError("");
    try {
      await saveSettings(
        `accounts/${id}`,
        { method: "PATCH", body: JSON.stringify({ active: false }) },
        "Account update failed"
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Account update failed");
    }
  }

  async function handleInvite(e: FormEvent) {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setError("");
    try {
      const data = await saveSettings(
        "accounts/invitations",
        {
          method: "POST",
          body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole }),
        },
        "Invitation failed"
      );
      setInviteMsg(
        data.invitation
          ? `Invite token for ${data.invitation.email}: ${data.invitation.token}`
          : `Invite created for ${inviteEmail.trim()}`
      );
      setInviteEmail("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invitation failed");
    }
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
        {error && <p className="mt-3 text-sm font-semibold text-danger">{error}</p>}
      </RetroCard>
    </RetroWindow>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Section 6 - Data & Privacy Settings
   ═══════════════════════════════════════════════════════════════ */

function DataPrivacy({
  privacy,
  saveSettings,
}: {
  privacy: SettingsSnapshot["privacy"];
  saveSettings: SaveSettings;
}) {
  const [retention, setRetention] = useState(`${privacy.retentionDays ?? 60} days`);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setRetention(`${privacy.retentionDays ?? 60} days`);
  }, [privacy]);

  async function handleSave() {
    setError("");
    try {
      await saveSettings(
        "settings/privacy",
        {
          method: "PUT",
          body: JSON.stringify({ retentionDays: parseInt(retention) || 60 }),
        },
        "Privacy update failed"
      );
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Privacy update failed");
    }
  }

  return (
    <RetroWindow title="Data & Privacy">
      <div className="space-y-5">
        {/* Anonymized tracking - locked ON */}
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
                🔒 Anonymized Customer Tracking - Always On
              </p>
              <p className="text-xs text-text-muted leading-relaxed">
                RetailPulse does not store facial recognition data or persistent
                biometric identifiers. This is a core design principle, not a
                configurable setting.
              </p>
            </div>
          </div>
        </RetroCard>

        {/* Data retention - configurable */}
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
          {error && <span className="text-sm font-semibold text-danger">{error}</span>}
        </div>
      </div>
    </RetroWindow>
  );
}
