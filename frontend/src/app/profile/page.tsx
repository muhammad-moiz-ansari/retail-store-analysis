"use client";

import React, { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge, RetroButton, RetroCard, RetroInput, RetroWindow } from "@/components/ui";
import { useAuth } from "@/components/auth/AuthProvider";

const PROFILE_DATA = {
  Manager: {
    name: "Alex Morgan",
    initials: "A",
    memberSince: "January 2024",
    employeeId: "MGR-001",
  },
  Employee: {
    name: "Staff 03",
    initials: "S",
    memberSince: "March 2024",
    employeeId: "STF-003",
  },
} as const;

export default function ProfilePage() {
  const router = useRouter();
  const { role, signOut } = useAuth();
  const [photoNote, setPhotoNote] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("0300-1234567");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingDetails, setSavingDetails] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [detailsSaved, setDetailsSaved] = useState(false);
  const [passwordSaved, setPasswordSaved] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [shiftUpdates, setShiftUpdates] = useState(true);
  const [performanceSummary, setPerformanceSummary] = useState(true);
  const [systemAlerts, setSystemAlerts] = useState(true);
  const profile = PROFILE_DATA[role === "Manager" ? "Manager" : "Employee"];

  function handleLogout() {
    signOut();
    router.push("/");
  }

  function handleDetailsSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingDetails(true);
    setDetailsSaved(false);
    window.setTimeout(() => {
      setSavingDetails(false);
      setDetailsSaved(true);
      window.setTimeout(() => setDetailsSaved(false), 3000);
    }, 600);
  }

  function handlePasswordSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (newPassword !== confirmPassword) {
      setPasswordError("Passwords do not match.");
      return;
    }
    setPasswordError("");
    setSavingPassword(true);
    setPasswordSaved(false);
    window.setTimeout(() => {
      setSavingPassword(false);
      setPasswordSaved(true);
      window.setTimeout(() => setPasswordSaved(false), 3000);
    }, 600);
  }

  return (
    <main className="mx-auto flex w-full max-w-[900px] flex-col gap-10 px-4 py-10 md:px-6 md:py-16">
      <RetroWindow title="Edit Profile">
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.16em] text-accent">Account Settings</p>
        <h1 className="mt-2 font-heading text-3xl font-bold tracking-tight text-text">Your Profile</h1>
        <p className="mt-2 text-sm text-text-muted">Update your account details and preferences.</p>
      </RetroWindow>

      <section aria-labelledby="profile-overview-heading">
        <RetroCard>
          <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
            <div className="flex shrink-0 flex-col items-center gap-2">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-accent-soft font-heading text-3xl font-bold text-text" aria-label={`Avatar for ${profile.name}`}>
                {profile.initials}
              </div>
              <button type="button" onClick={() => setPhotoNote(true)} className="text-xs font-semibold text-accent underline underline-offset-2 hover:text-accent-hover">
                Change Photo
              </button>
              {photoNote && <p className="text-center text-xs text-text-muted">Photo upload coming soon</p>}
            </div>
            <div className="text-center sm:text-left">
              <h2 id="profile-overview-heading" className="font-heading text-2xl font-semibold text-text">{profile.name}</h2>
              <div className="mt-2"><Badge variant={role === "Manager" ? "accent" : "neutral"}>{role === "Manager" ? "Manager" : "Employee Access"}</Badge></div>
              <p className="mt-3 font-mono text-xs text-text-muted">Member since {profile.memberSince}</p>
              <p className="mt-1 font-mono text-xs text-text-muted">System ID: {profile.employeeId}</p>
            </div>
          </div>
        </RetroCard>
      </section>

      <RetroWindow title="Account Details">
        <form onSubmit={handleDetailsSubmit} className="space-y-6">
          <RetroCard>
            <div className="grid gap-5 md:grid-cols-2">
              <RetroInput label="Full Name" type="text" value={fullName || profile.name} onChange={(event) => setFullName(event.target.value)} autoComplete="name" />
              <RetroInput label="Email Address" type="email" value={email || (role === "Manager" ? "alex.morgan@retailpulse.com" : "staff03@retailpulse.com")} onChange={(event) => setEmail(event.target.value)} autoComplete="email" />
              <RetroInput label="Phone Number" type="text" value={phone} onChange={(event) => setPhone(event.target.value)} autoComplete="tel" />
              <RetroInput label="Employee/Staff ID" type="text" value={profile.employeeId} disabled readOnly />
              {role === "Employee" && (
                <label className="block md:col-span-2">
                  <span className="mb-1.5 block font-heading text-xs font-semibold uppercase tracking-wide text-text-muted">Assigned Zone</span>
                  <select disabled value="Electronics Floor" className="w-full rounded-md border-2 border-border-soft bg-surface-alt px-3 py-2.5 text-sm text-text-muted focus:outline-none">
                    <option>Electronics Floor</option>
                  </select>
                  <span className="mt-1.5 block text-xs text-text-muted">Zone assignments are set by your manager.</span>
                </label>
              )}
            </div>
          </RetroCard>
          <RetroButton type="submit" variant="primary" disabled={savingDetails}>{savingDetails ? "Saving..." : "Save Changes"}</RetroButton>
          {detailsSaved && <SuccessBanner>Profile updated successfully.</SuccessBanner>}
        </form>
      </RetroWindow>

      <RetroWindow title="Change Password">
        <form onSubmit={handlePasswordSubmit} className="space-y-6">
          <RetroCard>
            <div className="space-y-5">
              <RetroInput label="Current Password" type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} autoComplete="current-password" />
              <div>
                <RetroInput label="New Password" type="password" value={newPassword} onChange={(event) => { setNewPassword(event.target.value); setPasswordError(""); }} autoComplete="new-password" error={!!passwordError} />
                <p className="mt-1.5 text-xs text-text-muted">Minimum 8 characters, include a number.</p>
              </div>
              <RetroInput label="Confirm New Password" type="password" value={confirmPassword} onChange={(event) => { setConfirmPassword(event.target.value); setPasswordError(""); }} autoComplete="new-password" error={!!passwordError} helperText={passwordError} />
            </div>
          </RetroCard>
          <RetroButton type="submit" variant="secondary" disabled={savingPassword}>{savingPassword ? "Updating..." : "Update Password"}</RetroButton>
          {passwordSaved && <SuccessBanner>Password updated successfully.</SuccessBanner>}
        </form>
      </RetroWindow>

      <RetroWindow title="Notifications">
        <RetroCard>
          <div className="divide-y divide-border-soft/50">
            <PreferenceToggle label="Shift Updates" description="Get notified when your manager posts a shift update." checked={shiftUpdates} onChange={() => setShiftUpdates((value) => !value)} />
            <PreferenceToggle label="Performance Summary" description="Weekly email summary of your performance score." checked={performanceSummary} onChange={() => setPerformanceSummary((value) => !value)} />
            {role === "Manager" && <PreferenceToggle label="System Alerts" description="Get notified about active alerts requiring attention." checked={systemAlerts} onChange={() => setSystemAlerts((value) => !value)} />}
          </div>
        </RetroCard>
      </RetroWindow>

      <RetroWindow title="Danger Zone" titleBarClassName="bg-danger/10">
        <RetroCard className="border-danger">
          <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-text">Signing out will end your current session.</p>
            <RetroButton type="button" variant="secondary" className="!border-danger !text-danger hover:!bg-danger/10" onClick={handleLogout}>Log Out</RetroButton>
          </div>
        </RetroCard>
      </RetroWindow>
    </main>
  );
}

function SuccessBanner({ children }: { children: React.ReactNode }) {
  return <div className="border-l-4 border-success bg-success/10 px-4 py-3 font-mono text-xs font-semibold text-success">{children}</div>;
}

function PreferenceToggle({ label, description, checked, onChange }: { label: string; description: string; checked: boolean; onChange: () => void }) {
  return (
    <div className="flex items-center justify-between gap-5 py-4 first:pt-0 last:pb-0">
      <div>
        <p className="font-heading text-sm font-semibold text-text">{label}</p>
        <p className="mt-1 text-xs text-text-muted">{description}</p>
      </div>
      <button type="button" role="switch" aria-checked={checked} aria-label={`${label}: ${checked ? "on" : "off"}`} onClick={onChange} className={`relative h-6 w-11 shrink-0 rounded border-2 border-border-soft transition-colors ${checked ? "bg-accent" : "bg-border-soft"}`}>
        <span className={`absolute top-0.5 h-4 w-4 rounded-sm bg-surface transition-transform ${checked ? "translate-x-5" : "translate-x-0.5"}`} />
      </button>
    </div>
  );
}
