import { NextRequest, NextResponse } from "next/server";
import { spawn } from "node:child_process";
import path from "node:path";

function resolveRepoRoot() {
  const cwd = process.cwd();
  const candidates = [cwd, path.resolve(cwd, ".."), path.resolve(cwd, "..", "..")];
  for (const candidate of candidates) {
    const backendDir = path.join(candidate, "backend");
    const frontendDir = path.join(candidate, "frontend");
    try {
      const fs = require("node:fs");
      if (fs.existsSync(path.join(candidate, "package.json")) && fs.existsSync(backendDir) && fs.existsSync(frontendDir)) {
        return candidate;
      }
    } catch {}
  }
  return cwd;
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { frame, aisle } = body;

    if (!frame) {
      return NextResponse.json({ error: "No frame data" }, { status: 400 });
    }

    const repoRoot = resolveRepoRoot();
    const script = path.join(repoRoot, "backend", "analyze_frame.py");
    const pythonExecutable = process.env.PYTHON_BIN || "python3";

    const result = await new Promise<string>((resolve, reject) => {
      const child = spawn(pythonExecutable, ["-u", script, aisle || "aisle"], {
        cwd: repoRoot,
        env: { ...process.env, PYTHONUNBUFFERED: "1" },
      });

      let stdout = "";
      let stderr = "";

      child.stdout.on("data", (chunk: Buffer) => {
        stdout += chunk.toString();
      });

      child.stderr.on("data", (chunk: Buffer) => {
        stderr += chunk.toString();
      });

      child.on("error", (err) => reject(err));

      child.on("close", (code) => {
        if (code !== 0) {
          reject(new Error(stderr || "Analysis failed"));
        } else {
          resolve(stdout);
        }
      });

      // Send the base64 frame via stdin
      child.stdin.write(frame);
      child.stdin.end();
    });

    const data = JSON.parse(result.trim());
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unexpected error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
