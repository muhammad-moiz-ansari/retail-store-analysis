import { mkdtempSync, mkdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = fileURLToPath(new URL("../", import.meta.url));
const outputRoot = join(root, "data", "outputs", "dashboard-provider-tests");
mkdirSync(outputRoot, { recursive: true });
const output = mkdtempSync(join(outputRoot, "run-"));
const compiler = resolve(root, "node_modules/typescript/bin/tsc");
const compilation = spawnSync(process.execPath, [compiler,
  "--strict", "--skipLibCheck", "--esModuleInterop", "--target", "ES2020",
  "--module", "commonjs", "--moduleResolution", "node", "--jsx", "react-jsx",
  "--rootDir", "frontend/src", "--outDir", output,
  "frontend/src/lib/analytics-provider/provider.test.ts",
  "frontend/src/lib/analytics-provider/controller.test.ts",
  "frontend/src/components/dashboard/DashboardAnalytics.test.tsx",
], { cwd: root, stdio: "inherit" });
if (compilation.error) throw compilation.error;
if (compilation.status !== 0) process.exit(compilation.status ?? 1);
const tests = spawnSync(process.execPath, ["--test",
  join(output, "lib/analytics-provider/provider.test.js"),
  join(output, "lib/analytics-provider/controller.test.js"),
  join(output, "components/dashboard/DashboardAnalytics.test.js"),
], { cwd: root, stdio: "inherit" });
if (tests.error) throw tests.error;
process.exit(tests.status ?? 1);
