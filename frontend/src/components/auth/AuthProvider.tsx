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
    queueMicrotask(() => {
      const storedSession = window.localStorage.getItem(SESSION_KEY);
      if (storedSession === "Manager" || storedSession === "Employee") {
        setRole(storedSession);
        setAuthenticated(true);
      }
    });

    fetch("/api/auth/session", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((session) => {
        if (session?.authenticated && session?.role === "Manager") {
          window.localStorage.setItem(SESSION_KEY, "Manager");
          setRole("Manager");
          setAuthenticated(true);
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
            body: JSON.stringify(credentials || {}),
          });
          if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.error || "Manager sign-in failed");
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
