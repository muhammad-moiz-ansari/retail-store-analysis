import test from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { createSession, verifySession } from "./pos-auth";

test("signed sessions reject missing/invalid expiry, invalid identity and extra token parts", () => {
  const old = process.env.POS_SESSION_SECRET;
  process.env.POS_SESSION_SECRET = "isolated-test-secret";
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
    if (old === undefined) delete process.env.POS_SESSION_SECRET; else process.env.POS_SESSION_SECRET = old;
  }
});
