"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthField, AuthPageShell } from "@/components/auth/AuthPageShell";
import { RetroButton } from "@/components/ui/RetroButton";
import { useAuth, type UserRole } from "@/components/auth/AuthProvider";

export default function LoginPage() {
  const router = useRouter();
  const { signIn } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [submitError, setSubmitError] = useState<string>();
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
      await signIn(role, { email, password });
      router.push(role === "Manager" ? "/dashboard" : "/employee-home");
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Sign-in failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthPageShell title="Sign in" description="Choose your access level to open your workspace.">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate aria-busy={submitting}>
        <AuthField
          label="Email"
          type="email"
          placeholder="you@company.com"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (errors.email) setErrors((p) => ({ ...p, email: undefined }));
          }}
          error={errors.email}
          autoComplete="email"
        />

        <AuthField
          label="Password"
          type="password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (errors.password) setErrors((p) => ({ ...p, password: undefined }));
          }}
          error={errors.password}
          autoComplete="current-password"
        />

        <fieldset>
          <legend className="mb-1.5 text-sm font-semibold">Access level</legend>
          <div className="grid grid-cols-2 gap-2">
            {(["Employee", "Manager"] as UserRole[]).map((option) => (
              <label key={option} className="cursor-pointer">
                <input
                  className="peer sr-only"
                  type="radio"
                  name="role"
                  value={option}
                  checked={role === option}
                  onChange={() => setRole(option)}
                />
                <span className="flex min-h-11 items-center justify-center rounded-lg border border-border-soft px-2 text-sm font-semibold hover:bg-surface-alt peer-checked:border-accent peer-checked:bg-surface-alt peer-checked:text-accent peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent">
                  {option}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        {submitError && <p role="alert" className="text-sm text-danger">{submitError}</p>}
        <RetroButton
          type="submit"
          variant="primary"
          disabled={submitting}
          className="min-h-11 w-full"
        >
          {submitting ? "Signing in…" : "Sign in"}
        </RetroButton>

        <p className="text-center text-sm text-text-muted">
          Don&apos;t have an account?{" "}
          <Link
            href="/signup"
            className="font-semibold text-accent hover:text-accent-hover underline underline-offset-2 transition-colors"
          >
            Sign up
          </Link>
        </p>
        <details className="text-sm text-text-muted">
          <summary className="w-fit cursor-pointer">Local demo credentials</summary>
          <p className="mt-2 break-words">Use manager@retailpulse.local or employee@retailpulse.local with password123.</p>
        </details>
      </form>
    </AuthPageShell>
  );
}
