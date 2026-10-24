"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

export type UserRole = "Manager" | "Employee";

type AuthContextValue = {
  ready: boolean;
  authenticated: boolean;
  role: UserRole | null;
  signIn: (role: UserRole, credentials?: { email: string; password: string }) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const SESSION_KEY = "retailpulse-session";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [role, setRole] = useState<UserRole | null>(null);

  useEffect(() => {
    const cachedRole = window.localStorage.getItem(SESSION_KEY);
    if (cachedRole === "Manager" || cachedRole === "Employee") {
      setRole(cachedRole);
      setAuthenticated(true);
    }

    fetch("/api/auth/session", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((session) => {
        if (session?.authenticated && (session?.role === "Manager" || session?.role === "Employee")) {
          window.localStorage.setItem(SESSION_KEY, session.role);
          setRole(session.role);
          setAuthenticated(true);
        } else {
          window.localStorage.removeItem(SESSION_KEY);
        }
      })
      .finally(() => setReady(true));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ready,
      authenticated,
      role,
      async signIn(nextRole, credentials) {
        if (nextRole === "Manager") {
          const response = await fetch("/api/auth/session", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...(credentials || {}), role: nextRole }),
          });
          if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.error || "Manager sign-in failed");
          }
        } else {
          const response = await fetch("/api/auth/session", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...(credentials || {}), role: nextRole }),
          });
          if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.error || "Employee sign-in failed");
          }
        }
        window.localStorage.setItem(SESSION_KEY, nextRole);
        setRole(nextRole);
        setAuthenticated(true);
      },
      async signOut() {
        await fetch("/api/auth/logout", { method: "POST" }).catch(() => undefined);
        window.localStorage.removeItem(SESSION_KEY);
        setRole(null);
        setAuthenticated(false);
      },
    }),
    [authenticated, ready, role]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
