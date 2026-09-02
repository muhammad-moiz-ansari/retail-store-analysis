"use client";

import React, { useState } from "react";
import { Badge, RetroCard, RetroWindow } from "@/components/ui";
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
  const { role } = useAuth();
  const [photoNote, setPhotoNote] = useState(false);
  const profile = PROFILE_DATA[role === "Manager" ? "Manager" : "Employee"];

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
    </main>
  );
}
