"use client";

import React, { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { RetroWindow, RetroInput, RetroButton, Logo } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [submitting, setSubmitting] = useState(false);

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

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    // eslint-disable-next-line no-console
    console.log("Login →", { email, password });

    // Simulate brief delay then navigate
    setTimeout(() => {
      router.push("/dashboard");
    }, 400);
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
