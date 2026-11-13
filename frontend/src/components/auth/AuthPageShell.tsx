import { useId, type ComponentPropsWithoutRef, type ReactNode } from "react";
import { Logo } from "@/components/ui/Logo";

export function AuthPageShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto w-full max-w-xl px-5 py-10 sm:px-8 sm:py-16">
      <div className="overflow-hidden rounded-2xl border border-border-soft bg-surface shadow-sm">
        <header className="bg-surface-alt px-6 py-7 sm:px-9">
          <Logo size={30} />
          <h1 className="mt-5 text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
          <p className="mt-2 text-text-muted">{description}</p>
        </header>
        <div className="p-6 sm:p-9">{children}</div>
      </div>
    </main>
  );
}

export function AuthField({
  label,
  error,
  ...inputProps
}: Omit<ComponentPropsWithoutRef<"input">, "id" | "className"> & {
  label: string;
  error?: string;
}) {
  const id = useId();
  const errorId = `${id}-error`;

  return (
    <div>
      <label className="mb-1.5 block text-sm font-semibold" htmlFor={id}>{label}</label>
      <input
        {...inputProps}
        id={id}
        required
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        className={`min-h-11 w-full rounded-lg border bg-surface px-3 text-base text-text placeholder:text-text-muted ${error ? "border-danger" : "border-border-soft"}`}
      />
      {error && <p id={errorId} className="mt-1 text-sm text-danger">{error}</p>}
    </div>
  );
}
