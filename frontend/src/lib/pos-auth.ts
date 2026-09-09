import { createHmac, timingSafeEqual } from "node:crypto";

export const POS_SESSION_COOKIE = "retailpulse-pos-session";

type SessionPayload = {
  role: "Manager";
  email: string;
  exp: number;
};

function secret() {
  return process.env.POS_SESSION_SECRET || process.env.NEXTAUTH_SECRET || "local-dev-pos-session-secret";
}

function base64url(input: string) {
  return Buffer.from(input).toString("base64url");
}

function signPayload(payload: string) {
  return createHmac("sha256", secret()).update(payload).digest("base64url");
}

export function createManagerSession(email: string, ttlSeconds = 60 * 60 * 8) {
  const payload = base64url(JSON.stringify({ role: "Manager", email, exp: Math.floor(Date.now() / 1000) + ttlSeconds } satisfies SessionPayload));
  return `${payload}.${signPayload(payload)}`;
}

export function verifyManagerSession(token?: string | null): SessionPayload | null {
  if (!token) return null;
  const [payload, signature] = token.split(".");
  if (!payload || !signature) return null;
  const expected = signPayload(payload);
  const expectedBuffer = Buffer.from(expected);
  const actualBuffer = Buffer.from(signature);
  if (expectedBuffer.length !== actualBuffer.length || !timingSafeEqual(expectedBuffer, actualBuffer)) return null;
  try {
    const parsed = JSON.parse(Buffer.from(payload, "base64url").toString("utf-8")) as SessionPayload;
    if (parsed.role !== "Manager" || parsed.exp < Math.floor(Date.now() / 1000)) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function acceptsDemoCredential(email: string, password: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) && password.length >= 6;
}
