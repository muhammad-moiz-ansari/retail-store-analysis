import type { ReactNode } from "react";

export function ManagerPage({ children }: { children: ReactNode }) {
  return <main className="mx-auto w-full min-w-0 max-w-[90rem] space-y-6 px-4 py-7 sm:px-6 lg:px-8 lg:py-9">{children}</main>;
}

export function ManagerHeader({ title, children, actions }: {
  title: string;
  children?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
        {children && <div className="mt-2 max-w-3xl text-sm leading-relaxed text-text-muted">{children}</div>}
      </div>
      {actions}
    </header>
  );
}

export function ManagerPanel({ title, children, className = "" }: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`min-w-0 rounded-2xl border border-border-soft bg-surface p-4 sm:p-6 ${className}`}>
      <h2 className="mb-4 text-lg font-bold tracking-tight">{title}</h2>
      {children}
    </section>
  );
}

export function ManagerCard({ label, children, className = "" }: {
  label?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`min-w-0 rounded-xl border border-border-soft bg-surface p-4 ${className}`}>
      {label && <h3 className="mb-3 text-sm font-semibold text-text">{label}</h3>}
      {children}
    </div>
  );
}

export function ManagerTable({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div role="region" aria-label={label} tabIndex={0}
      className="min-w-0 overflow-x-auto rounded-lg [&_thead]:bg-surface-alt [&_th]:whitespace-nowrap [&_th]:font-semibold [&_tbody_tr:hover]:bg-bg">
      {children}
    </div>
  );
}
