import test from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { resolveAuthConfig } from "./auth-config";
import { createSession, verifySession } from "./session-auth";

test("signed sessions reject missing/invalid expiry, invalid identity and extra token parts", () => {
  const old = process.env.RETAILPULSE_SESSION_SECRET;
  process.env.RETAILPULSE_SESSION_SECRET = "isolated-test-secret";
  try {
    const valid = createSession({ role: "Manager", email: "manager@test.invalid", userId: "u1" });
    assert.equal(verifySession(valid)?.userId, "u1");
    assert.equal(verifySession(valid + ".extra"), null);
    assert.equal(verifySession(valid + "tampered"), null);
    const base = { role: "Manager", email: "manager@test.invalid", exp: Math.floor(Date.now() / 1000) + 100 };
    for (const changed of [{ ...base, exp: undefined }, { ...base, exp: "future" }, { ...base, exp: 1 },
      { ...base, email: "" }, { ...base, userId: 10 }]) {
      const payload = Buffer.from(JSON.stringify(changed)).toString("base64url");
      const signature = createHmac("sha256", "isolated-test-secret").update(payload).digest("base64url");
      assert.equal(verifySession(`${payload}.${signature}`), null);
    }
  } finally {
    if (old === undefined) delete process.env.RETAILPULSE_SESSION_SECRET; else process.env.RETAILPULSE_SESSION_SECRET = old;
  }
});


test("deployed cookie signing and verification refuse absent or known default secrets", () => {
  const previousEnv = process.env;
  const actor = { role: "Manager", email: "manager@test.invalid", userId: "u1" } as const;
  try {
    process.env = { NODE_ENV: "development", RETAILPULSE_DEV_DEFAULTS: "1" };
    const devCookie = createSession(actor);
    assert.equal(verifySession(devCookie)?.userId, "u1");

    process.env = { NODE_ENV: "production", RETAILPULSE_DEV_DEFAULTS: "1" };
    assert.throws(() => createSession(actor), /authentication is not configured/);
    assert.equal(verifySession(devCookie), null);

    process.env.RETAILPULSE_SESSION_SECRET = "local-dev-pos-session-secret";
    assert.throws(() => createSession(actor), /authentication is not configured/);
    assert.equal(verifySession(devCookie), null);
  } finally {
    process.env = previousEnv;
  }
});

test("auth config requires both credentials and explicitly limits local defaults", () => {
  const session = { RETAILPULSE_SESSION_SECRET: "test-session" };
  const internal = { RETAILPULSE_INTERNAL_SECRET: "test-internal" };
  const dev = { NODE_ENV: "development", RETAILPULSE_DEV_DEFAULTS: "1" } as const;
  assert.equal(resolveAuthConfig({ NODE_ENV: "development" }), null);
  assert.equal(resolveAuthConfig({ NODE_ENV: "production", RETAILPULSE_DEV_DEFAULTS: "1" }), null);
  assert.equal(resolveAuthConfig(session), null);
  assert.equal(resolveAuthConfig(internal), null);
  assert.equal(resolveAuthConfig({ ...session, RETAILPULSE_INTERNAL_SECRET: "change-me" }), null);
  assert.equal(resolveAuthConfig({ ...internal, RETAILPULSE_SESSION_SECRET: "replace-with-a-long-random-local-secret" }), null);
  assert.ok(resolveAuthConfig(dev));
  assert.equal(resolveAuthConfig(dev, true), null);
  assert.equal(resolveAuthConfig({ ...dev, ...session }, true), null);
  assert.deepEqual(resolveAuthConfig({ ...session, ...internal }, true), {
    sessionSecret: "test-session",
    internalSecret: "test-internal",
  });
  assert.ok(resolveAuthConfig({ NEXTAUTH_SECRET: "test-session", POS_INTERNAL_SECRET: "test-internal" }));
  assert.equal(resolveAuthConfig({ NEXTAUTH_SECRET: "test-session", POS_INTERNAL_SECRET: "test-internal" }, true), null);
});
