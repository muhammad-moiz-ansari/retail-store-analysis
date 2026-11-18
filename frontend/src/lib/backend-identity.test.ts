import test from "node:test";
import assert from "node:assert/strict";
import { checkForwardablePath } from "./backend-identity";

test("the proxy forwards only known backend roots without traversal segments", () => {
  assert.equal(checkForwardablePath(["tasks", "me"]), "ok");
  assert.equal(checkForwardablePath(["camera", "people", "p1", "role"]), "ok");
  assert.equal(checkForwardablePath(["agents", "runs", "r1", "summary"]), "ok");
  for (const bad of [[], ["tasks", ".."], ["..", "health"], ["tasks", "."], ["tasks", ""], ["tasks", "a/b"], ["tasks", "a\\b"]]) {
    assert.equal(checkForwardablePath(bad), "bad", JSON.stringify(bad));
  }
  assert.equal(checkForwardablePath(["health"]), "unknown");
  assert.equal(checkForwardablePath(["docs"]), "unknown");
});
