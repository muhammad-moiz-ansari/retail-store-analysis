"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { AuthField, AuthPageShell } from "@/components/auth/AuthPageShell";
import { RetroButton } from "@/components/ui/RetroButton";

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<Record<string, string | undefined>>({});
  const [submitError, setSubmitError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);

  function validate() {
    const next: Record<string, string> = {};
    if (!name.trim()) next.name = "Full name is required";
    if (!email.trim()) next.email = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      next.email = "Enter a valid email address";
    if (!token.trim()) next.token = "Invite token is required";
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

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (submitting) return;
    setSubmitError(undefined);
    if (!validate()) {
      const form = e.currentTarget;
      requestAnimationFrame(() => form.querySelector<HTMLInputElement>('input[aria-invalid="true"]')?.focus());
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, token, password }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Signup failed");
      // Reload the auth provider so the protected route reads the new session cookie.
      window.location.assign(data.role === "Manager" ? "/dashboard" : "/employee-home");
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Signup failed");
      setSubmitting(false);
    }
  }

  return (
    <AuthPageShell title="Create an account" description="Use the invite token from your manager to join your store.">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate aria-busy={submitting}>
        <AuthField
          label="Full name"
          type="text"
          placeholder="Jane Smith"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            clearError("name");
          }}
          error={errors.name}
          autoComplete="name"
        />

        <AuthField
          label="Email"
          type="email"
          placeholder="you@company.com"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            clearError("email");
          }}
          error={errors.email}
          autoComplete="email"
        />

        <AuthField
          label="Invite token"
          type="text"
          placeholder="Paste the token from your manager"
          value={token}
          onChange={(e) => {
            setToken(e.target.value);
            clearError("token");
          }}
          error={errors.token}
          autoComplete="one-time-code"
        />

        <AuthField
          label="Password"
          type="password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            clearError("password");
          }}
          error={errors.password}
          autoComplete="new-password"
        />

        <AuthField
          label="Confirm password"
          type="password"
          value={confirm}
          onChange={(e) => {
            setConfirm(e.target.value);
            clearError("confirm");
          }}
          error={errors.confirm}
          autoComplete="new-password"
        />

        {submitError && <p role="alert" className="text-sm text-danger">{submitError}</p>}
        <RetroButton
          type="submit"
          variant="primary"
          disabled={submitting}
          className="min-h-11 w-full"
        >
          {submitting ? "Creating account…" : "Create account"}
        </RetroButton>

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
    </AuthPageShell>
  );
}
