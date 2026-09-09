"use client";

import React, { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { RetroWindow, RetroInput, RetroButton, Logo } from "@/components/ui";
import { useAuth, type UserRole } from "@/components/auth/AuthProvider";

export default function LoginPage() {
  const router = useRouter();
  const { signIn } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [submitting, setSubmitting] = useState(false);
  const [role, setRole] = useState<UserRole>("Employee");

  function validate() {
    const next: typeof errors = {};
    if (!email.trim()) next.email = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      next.email = "Enter a valid email address";
    if (!password) next.password = "Password is required";
    else if (password.length < 6)
      next.password = "Password must be at least 6 characters";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    try {
      await signIn(role, { email, password });
      router.push(role === "Manager" ? "/dashboard" : "/employee-home");
    } catch (error) {
      setErrors((current) => ({
        ...current,
        password: error instanceof Error ? error.message : "Sign-in failed",
      }));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-bg px-4 py-12 overflow-hidden">
      {/* ── Decorative background shapes ── */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-32 -right-32 w-[500px] h-[500px] rounded-full opacity-[0.04]"
        style={{
          background:
            "repeating-radial-gradient(circle, var(--color-border) 0px, var(--color-border) 1px, transparent 1px, transparent 28px)",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-24 -left-24 w-[400px] h-[400px] rounded-full opacity-[0.04]"
        style={{
          background:
            "repeating-radial-gradient(circle, var(--color-accent) 0px, var(--color-accent) 1px, transparent 1px, transparent 32px)",
        }}
      />

      {/* ── Sign-in window ── */}
      <RetroWindow title="RetailPulse - Sign In" className="w-full max-w-md relative z-10">
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {/* Logo */}
          <div className="flex justify-center pb-2">
            <Logo size={36} />
          </div>

          {/* Email */}
          <RetroInput
            label="Email"
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (errors.email) setErrors((p) => ({ ...p, email: undefined }));
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
              if (errors.password) setErrors((p) => ({ ...p, password: undefined }));
            }}
            error={!!errors.password}
            helperText={errors.password}
            autoComplete="current-password"
          />

          <div>
            <span className="block mb-1.5 font-heading text-xs font-semibold tracking-wide text-text-muted uppercase">
              Access level
            </span>
            <div className="flex overflow-hidden rounded-md border-2 border-border">
              {(["Employee", "Manager"] as UserRole[]).map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setRole(option)}
                  className={`flex-1 px-4 py-2 font-heading text-sm font-semibold transition-colors ${role === option ? "bg-accent text-surface" : "bg-surface text-text hover:bg-surface-alt"}`}
                >
                  {option}
                </button>
              ))}
            </div>
            <p className="mt-1.5 text-xs text-text-muted">
              Demo access: choose a role and use any valid email with a 6+ character password.
            </p>
          </div>

          {/* Submit */}
          <RetroButton
            type="submit"
            variant="primary"
            disabled={submitting}
            className="w-full"
          >
            {submitting ? "Signing in…" : "Sign In"}
          </RetroButton>

          {/* Link to signup */}
          <p className="text-center text-sm text-text-muted">
            Don&apos;t have an account?{" "}
            <Link
              href="/signup"
              className="font-semibold text-accent hover:text-accent-hover underline underline-offset-2 transition-colors"
            >
              Sign up
            </Link>
          </p>
        </form>
      </RetroWindow>
    </div>
  );
}
