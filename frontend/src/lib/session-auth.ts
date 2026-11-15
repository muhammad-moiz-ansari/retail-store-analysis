import { createHmac, timingSafeEqual } from "node:crypto";

// Keep the cookie name compatible with sessions issued before the auth module rename.
export const SESSION_COOKIE = "retailpulse-pos-session";

type SessionPayload = {
  role: "Manager" | "Employee";
  userId?: string;
  email: string;
  name?: string;
  exp: number;
};

export const DEV_SESSION_SECRET = "local-dev-pos-session-secret";

export function configuredSessionSecret() {
  return process.env.RETAILPULSE_SESSION_SECRET || process.env.POS_SESSION_SECRET || process.env.NEXTAUTH_SECRET;
}

function base64url(input: string) {
  return Buffer.from(input).toString("base64url");
}

function signPayload(payload: string) {
  return createHmac("sha256", (configuredSessionSecret() || DEV_SESSION_SECRET)).update(payload).digest("base64url");
}

export function createSession(session: Omit<SessionPayload, "exp">, ttlSeconds = 60 * 60 * 8) {
  const payload = base64url(JSON.stringify({ ...session, exp: Math.floor(Date.now() / 1000) + ttlSeconds } satisfies SessionPayload));
  return `${payload}.${signPayload(payload)}`;
}

export function verifySession(token?: string | null): SessionPayload | null {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length !== 2) return null;
  const [payload, signature] = parts;
  if (!payload || !signature) return null;
  const expected = signPayload(payload);
  const expectedBuffer = Buffer.from(expected);
  const actualBuffer = Buffer.from(signature);
  if (expectedBuffer.length !== actualBuffer.length || !timingSafeEqual(expectedBuffer, actualBuffer)) return null;
  try {
    const parsed = JSON.parse(Buffer.from(payload, "base64url").toString("utf-8")) as SessionPayload;
    if (!["Manager", "Employee"].includes(parsed.role) || !Number.isSafeInteger(parsed.exp)
      || parsed.exp <= Math.floor(Date.now() / 1000) || typeof parsed.email !== "string" || !parsed.email.trim()
      || (parsed.userId !== undefined && (typeof parsed.userId !== "string" || !parsed.userId.trim()))) return null;
    return parsed;
  } catch {
    return null;
  }
}
