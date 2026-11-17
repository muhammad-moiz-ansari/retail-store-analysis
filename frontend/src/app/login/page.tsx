"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthField, AuthPageShell } from "@/components/auth/AuthPageShell";
import { RetroButton } from "@/components/ui/RetroButton";
import { useAuth } from "@/components/auth/AuthProvider";

export default function LoginPage() {
  const router = useRouter();
  const { signIn } = useAuth();

  const [role, setRole] = useState<"Manager" | "Employee">("Manager");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [submitError, setSubmitError] = useState<string>();
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
      const signedInAs = await signIn({ email, password, role });
      router.push(signedInAs === "Manager" ? "/manager/home" : "/employee/home");
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Sign-in failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthPageShell title="Sign in" description="Sign in to open your workspace.">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate aria-busy={submitting}>
        <fieldset disabled={submitting}>
          <legend className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-muted">Sign in as</legend>
          <div className="grid grid-cols-2 gap-2">
            {(["Manager", "Employee"] as const).map((option) => (
              <label key={option}>
                <input type="radio" name="sign-in-role" value={option} checked={role === option}
                  onChange={() => { setRole(option); setSubmitError(undefined); }} className="peer sr-only" />
                <span className="flex min-h-11 cursor-pointer items-center justify-center rounded-lg border border-border-soft px-3 text-sm font-semibold text-text peer-checked:border-accent peer-checked:bg-surface-alt peer-checked:text-accent peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent peer-disabled:cursor-not-allowed peer-disabled:opacity-60">{option}</span>
              </label>
            ))}
          </div>
        </fieldset>
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
        {process.env.NODE_ENV === "development" && <details className="text-sm text-text-muted">
          <summary className="w-fit cursor-pointer">Local demo credentials</summary>
          <p className="mt-2 break-words">The accounts are manager@retailpulse.local and employee@retailpulse.local. The password 000000 only works on a local database created with <code>--seed-demo</code>. On the shared demo database, use the manager and employee passwords written in <code>.env.demo</code>.</p>
        </details>}
      </form>
    </AuthPageShell>
  );
}
