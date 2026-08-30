import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="font-heading text-4xl font-bold text-text">
          RetailPulse
        </h1>
        <p className="text-text-muted text-sm">
          Retail analytics — elegant retro OS edition
        </p>
        <div className="flex flex-col sm:flex-row items-center gap-3 mt-4">
          <Link
            href="/dashboard"
            className="inline-block px-5 py-2.5 rounded-md bg-accent text-surface font-heading text-sm font-semibold border-2 border-border shadow-[2px_2px_0px_rgba(74,46,30,0.25)] hover:bg-accent-hover transition-colors"
          >
            Open Dashboard →
          </Link>
          <Link
            href="/compare-people"
            className="inline-block px-5 py-2.5 rounded-md bg-surface text-text font-heading text-sm font-semibold border-2 border-border shadow-[2px_2px_0px_rgba(74,46,30,0.25)] hover:bg-surface-alt transition-colors"
          >
            Process & Compare People →
          </Link>
          <Link
            href="/style-guide"
            className="inline-block px-5 py-2.5 rounded-md bg-surface text-text font-heading text-sm font-semibold border-2 border-border shadow-[2px_2px_0px_rgba(74,46,30,0.25)] hover:bg-surface-alt transition-colors"
          >
            View Style Guide
          </Link>
        </div>
      </div>
    </div>
  );
}
