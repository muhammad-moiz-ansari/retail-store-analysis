"use client";

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

export type UserRole = "Manager" | "Employee";

type AuthContextValue = {
  ready: boolean;
  authenticated: boolean;
  role: UserRole | null;
  signIn: (role: UserRole) => void;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const SESSION_KEY = "retailpulse-session";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [role, setRole] = useState<UserRole | null>(null);

  useEffect(() => {
    const storedSession = window.localStorage.getItem(SESSION_KEY);
    if (storedSession === "Manager" || storedSession === "Employee") {
      setRole(storedSession);
      setAuthenticated(true);
    }
    setReady(true);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ready,
      authenticated,
      role,
      signIn(nextRole) {
        window.localStorage.setItem(SESSION_KEY, nextRole);
        setRole(nextRole);
        setAuthenticated(true);
      },
      signOut() {
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
