"use client";

import React, { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  RetroWindow,
  RetroInput,
  RetroButton,
  Logo,
} from "@/components/ui";
import { useAuth } from "@/components/auth/AuthProvider";

type Role = "manager" | "employee";

export default function SignupPage() {
  const router = useRouter();
  const { signIn } = useAuth();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [role, setRole] = useState<Role>("employee");
  const [errors, setErrors] = useState<Record<string, string | undefined>>({});
  const [submitting, setSubmitting] = useState(false);

  function validate() {
    const next: Record<string, string> = {};
    if (!name.trim()) next.name = "Full name is required";
    if (!email.trim()) next.email = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      next.email = "Enter a valid email address";
    if (!password) next.password = "Password is required";
    else if (password.length < 6)
      next.password = "Must be at least 6 characters";
    if (!confirm) next.confirm = "Please confirm your password";
    else if (confirm !== password) next.confirm = "Passwords do not match";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function clearError(field: string) {
    setErrors((p) => ({ ...p, [field]: undefined }));
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    // eslint-disable-next-line no-console
    console.log("Signup →", { name, email, password, role });

    setTimeout(() => {
      const selectedRole = role === "manager" ? "Manager" : "Employee";
      signIn(selectedRole);
      router.push(selectedRole === "Manager" ? "/dashboard" : "/employee");
    }, 400);
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-bg px-4 py-12 overflow-hidden">
      {/* ── Decorative background ── */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-32 -left-32 w-[500px] h-[500px] rounded-full opacity-[0.04]"
        style={{
          background:
            "repeating-radial-gradient(circle, var(--color-border) 0px, var(--color-border) 1px, transparent 1px, transparent 28px)",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-24 -right-24 w-[400px] h-[400px] rounded-full opacity-[0.04]"
        style={{
          background:
            "repeating-radial-gradient(circle, var(--color-accent) 0px, var(--color-accent) 1px, transparent 1px, transparent 32px)",
        }}
      />

      {/* ── Signup window ── */}
      <RetroWindow
        title="RetailPulse - Create Account"
        className="w-full max-w-md relative z-10"
      >
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {/* Logo */}
          <div className="flex justify-center pb-2">
            <Logo size={36} />
          </div>

          {/* Full Name */}
          <RetroInput
            label="Full Name"
            type="text"
            placeholder="Jane Smith"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              clearError("name");
            }}
            error={!!errors.name}
            helperText={errors.name}
            autoComplete="name"
          />

          {/* Email */}
          <RetroInput
            label="Email"
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              clearError("email");
            }}
            error={!!errors.email}
            helperText={errors.email}
            autoComplete="email"
          />

          {/* Password */}
          <RetroInput
            label="Password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              clearError("password");
            }}
            error={!!errors.password}
            helperText={errors.password}
            autoComplete="new-password"
          />

          {/* Confirm Password */}
          <RetroInput
            label="Confirm Password"
            type="password"
            placeholder="••••••••"
            value={confirm}
            onChange={(e) => {
              setConfirm(e.target.value);
              clearError("confirm");
            }}
            error={!!errors.confirm}
            helperText={errors.confirm}
            autoComplete="new-password"
          />

          {/* ── Role selector (retro segmented toggle) ── */}
          <div>
            <span className="block mb-1.5 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
              Role
            </span>
            <div className="flex rounded-md overflow-hidden border-2 border-border">
              <button
                type="button"
                onClick={() => setRole("manager")}
                className={[
                  "flex-1 px-4 py-2 font-heading text-sm font-semibold tracking-wide transition-colors cursor-pointer select-none",
                  role === "manager"
                    ? "bg-accent text-surface"
                    : "bg-surface text-text hover:bg-surface-alt",
                ].join(" ")}
              >
                Manager
              </button>
              <div className="w-[2px] bg-border" />
              <button
                type="button"
                onClick={() => setRole("employee")}
                className={[
                  "flex-1 px-4 py-2 font-heading text-sm font-semibold tracking-wide transition-colors cursor-pointer select-none",
                  role === "employee"
                    ? "bg-accent text-surface"
                    : "bg-surface text-text hover:bg-surface-alt",
                ].join(" ")}
              >
                Employee
              </button>
            </div>
          </div>

          {/* Submit */}
          <RetroButton
            type="submit"
            variant="primary"
            disabled={submitting}
            className="w-full"
          >
            {submitting ? "Creating account…" : "Create Account"}
          </RetroButton>

          {/* Link to login */}
          <p className="text-center text-sm text-text-muted">
            Already have an account?{" "}
            <Link
              href="/login"
              className="font-semibold text-accent hover:text-accent-hover underline underline-offset-2 transition-colors"
            >
              Sign in
            </Link>
          </p>
        </form>
      </RetroWindow>
    </div>
  );
}
