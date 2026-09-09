import { spawn } from "node:child_process";
import process from "node:process";

const isWindows = process.platform === "win32";
const root = process.cwd();
const python = process.env.PYTHON_BIN || (isWindows ? ".venv\\Scripts\\python.exe" : ".venv/bin/python");

function start(label, command, args, env = {}) {
  const child = spawn(command, args, {
    cwd: root,
    env: { ...process.env, ...env, PYTHONUNBUFFERED: "1" },
    stdio: ["inherit", "pipe", "pipe"],
    shell: false,
  });
  const prefix = `[${label}]`;
  child.stdout.on("data", (chunk) => process.stdout.write(`${prefix} ${chunk}`));
  child.stderr.on("data", (chunk) => process.stderr.write(`${prefix} ${chunk}`));
  child.on("error", (error) => process.stderr.write(`${prefix} ${error.message}\n`));
  return child;
}

const backend = start("backend", python, ["-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", "8011"], { PYTHONPATH: root });
const frontend = start("frontend", process.execPath, ["node_modules/next/dist/bin/next", "dev", "frontend"]);
const children = [backend, frontend];
let stopping = false;

function stop() {
  if (stopping) return;
  stopping = true;
  for (const child of children) {
    if (!child.killed) {
      if (isWindows) spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], { stdio: "ignore" });
      else child.kill("SIGTERM");
    }
  }
}

process.on("SIGINT", () => { stop(); });
process.on("SIGTERM", () => { stop(); });
for (const child of children) child.on("exit", (code) => {
  if (!stopping && code !== 0) {
    stop();
    process.exitCode = code || 1;
  }
});
