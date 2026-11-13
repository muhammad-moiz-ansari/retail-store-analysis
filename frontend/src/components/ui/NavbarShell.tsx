"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { MANAGER_ROUTES, EMPLOYEE_ROUTES, matchesRoute } from "@/components/auth/RouteAccessGuard";
import { Footer } from "./Footer";
import { Navbar } from "./Navbar";

const managerLinks = [
  ["/dashboard", "Overview"], ["/customer-info", "Customers"],
  ["/employee-info", "Employees"], ["/spatial-analytics", "Spatial analytics"],
  ["/interactions", "Interactions"], ["/alerts", "Alerts"],
  ["/camera-handoff", "Camera handoff"], ["/compare-people", "Compare people"],
  ["/voice-agent", "Voice agent"], ["/settings", "Store settings"],
];
const employeeLinks = [["/employee-home", "My workspace"], ["/my-performance", "My performance"]];

function Navigation({ links, pathname, label }: { links: string[][]; pathname: string; label: string }) {
  return <nav aria-label={label} className="grid gap-1">
    {links.map(([href, title]) => {
      const active = matchesRoute(pathname, [href]) || (href === "/employee-home" && pathname === "/employee");
      return <Link key={href} href={href} aria-current={active ? "page" : undefined}
        className={`flex min-h-11 items-center rounded-lg px-3 text-sm font-medium ${active ? "bg-surface-alt text-text" : "text-white hover:bg-white/15"}`}>
        {title}
      </Link>;
    })}
  </nav>;
}

export function NavbarShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { authenticated, role, signOut } = useAuth();
  const workspace = matchesRoute(pathname, [...MANAGER_ROUTES, ...EMPLOYEE_ROUTES, "/profile"]);
  const manager = role === "Manager";
  const home = manager ? "/dashboard" : "/employee-home";
  const links = [...(manager ? managerLinks : employeeLinks), ["/profile", "Profile"], ["/about", "About"]];
  const skip = <a href="#page-content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-[100] focus:rounded-lg focus:bg-surface focus:px-4 focus:py-3">Skip to content</a>;
  const content = <div id="page-content" tabIndex={-1} className="workspace-content flex-1">{children}</div>;

  if (!workspace || !authenticated || !role) {
    return <div data-public-shell={!workspace ? "" : undefined} className="flex min-h-screen flex-col">
      {skip}<Navbar />{content}<Footer />
    </div>;
  }

  const navigation = <Navigation links={links} pathname={pathname} label={manager ? "Manager navigation" : "Employee navigation"} />;
  const logout = <button type="button" className="min-h-11 rounded-lg px-3 text-left text-sm text-white hover:bg-white/15"
    onClick={async () => { await signOut(); router.push("/"); }}>Log out</button>;
  const brand = <Link href={home} className="font-heading text-xl font-bold tracking-tight text-white">RetailPulse</Link>;

  return <div className={manager ? "min-h-screen lg:grid lg:grid-cols-[15rem_minmax(0,1fr)]" : "min-h-screen"}>
    {skip}
    {manager && <aside className="workspace-sidebar sticky top-0 hidden h-dvh flex-col overflow-y-auto bg-text p-4 lg:flex">
      <div className="px-3 pb-5 pt-2">{brand}</div>
      {navigation}
      <div className="mt-auto border-t border-white/20 pt-3">{logout}</div>
    </aside>}
    <div className="min-w-0">
      <header className={`workspace-sidebar sticky top-0 z-40 bg-text px-4 py-3 text-white ${manager ? "lg:hidden" : ""}`}>
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3">
          {brand}
          <details key={pathname} className="relative">
            <summary className="flex min-h-11 cursor-pointer items-center rounded-lg border border-white/35 px-3 text-sm">Menu</summary>
            <div className="absolute right-0 top-full mt-2 grid max-h-[70dvh] w-[min(16rem,80vw)] gap-2 overflow-y-auto rounded-xl border border-white/25 bg-text p-2 shadow-lg">
              {navigation}{logout}
            </div>
          </details>
        </div>
        {!manager && <nav aria-label="Employee shortcuts" className="mx-auto mt-2 flex max-w-5xl flex-wrap gap-2">
          {employeeLinks.map(([href, title]) => <Link key={href} href={href}
            aria-current={pathname === href || (href === "/employee-home" && pathname === "/employee") ? "page" : undefined}
            className="flex min-h-11 items-center rounded-lg px-3 text-sm hover:bg-white/15 aria-[current=page]:bg-surface-alt aria-[current=page]:text-text">{title}</Link>)}
        </nav>}
      </header>
      {content}
    </div>
  </div>;
}
