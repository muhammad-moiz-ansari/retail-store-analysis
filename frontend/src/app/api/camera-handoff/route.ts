import { NextRequest } from "next/server";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

function resolveRepoRoot() {
  const cwd = process.cwd();
  const candidates = [cwd, path.resolve(cwd, ".."), path.resolve(cwd, "..", "..")];
  return candidates.find((candidate) => fs.existsSync(path.join(candidate, "backend", "camera_handoff.py"))) ?? cwd;
}

function safeInput(value: unknown, fallback: string) {
  const input = typeof value === "string" && value.trim() ? value.trim() : fallback;
  return path.resolve(input);
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const repoRoot = resolveRepoRoot();
    const backendRoot = path.join(repoRoot, "backend");
    const cam1 = safeInput(body.cam1, path.join(backendRoot, "videos", "cam1.mp4"));
    const cam2 = safeInput(body.cam2, path.join(backendRoot, "videos", "cam2.mp4"));
    const output = path.join(backendRoot, "output", "camera_handoff.json");
    const python = process.env.PYTHON_BIN || "python3";
    const script = path.join(backendRoot, "camera_handoff.py");

    if (!fs.existsSync(cam1) || !fs.existsSync(cam2)) {
      return Response.json({ error: "Both camera video files must exist." }, { status: 400 });
    }

    try {
      fs.rmSync(output);
    } catch {
      // There may not be a previous result on the first run.
    }

    const args = [
      "-u", script, "--cam1", cam1, "--cam2", cam2,
      "--output", output,
      "--sample-every", String(Math.max(1, Number(body.sampleEvery ?? 5))),
      "--min-gap", String(Math.max(0, Number(body.minGap ?? 1))),
      "--max-gap", String(Math.max(1, Number(body.maxGap ?? 45))),
      "--cam1-boundary", String(Number(body.cam1Boundary ?? 0.85)),
      "--cam2-boundary", String(Number(body.cam2Boundary ?? 0.15)),
    ];

    const stream = new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder();
        const send = (event: string, data: Record<string, unknown>) => {
          controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`));
        };
        const child = spawn(python, args, { cwd: repoRoot, env: { ...process.env, PYTHONUNBUFFERED: "1" } });
        let stderr = "";
        child.stdout.on("data", (chunk) => send("log", { text: chunk.toString() }));
        child.stderr.on("data", (chunk) => {
          const text = chunk.toString();
          stderr += text;
          send("log", { text });
        });
        child.on("error", (error) => {
          send("error", { message: error instanceof Error ? error.message : "Unable to start processor." });
          controller.close();
        });
        child.on("close", (code) => {
          if (code !== 0 || !fs.existsSync(output)) {
            send("error", { message: stderr || "Camera handoff processing failed." });
            send("done", {});
            controller.close();
            return;
          }
          try {
            send("result", { data: JSON.parse(fs.readFileSync(output, "utf8")) });
          } catch (error) {
            send("error", { message: error instanceof Error ? error.message : "Invalid processor output." });
          }
          send("done", {});
          controller.close();
        });
      },
    });

    return new Response(stream, {
      headers: { "Content-Type": "text/event-stream; charset=utf-8", "Cache-Control": "no-cache, no-transform", Connection: "keep-alive" },
    });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Invalid request." }, { status: 500 });
  }
}