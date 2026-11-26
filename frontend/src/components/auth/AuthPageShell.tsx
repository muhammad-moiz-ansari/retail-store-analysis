import { useId, type ComponentPropsWithoutRef, type ReactNode } from "react";
import { Logo } from "@/components/ui/Logo";
import { RetroInput } from "@/components/ui/RetroInput";

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
    <main className="auth-backdrop w-full px-5 py-10 sm:px-8 sm:py-16">
      <div className="mx-auto max-w-[32rem] overflow-hidden rounded-2xl border border-border-soft bg-surface shadow-[0_18px_44px_-20px_rgb(5_10_28_/_38%)]">
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
  return (
    <RetroInput {...inputProps} id={id} label={label} required error={Boolean(error)}
      helperText={error} className="auth-field min-h-11 !text-base" />
  );
}
