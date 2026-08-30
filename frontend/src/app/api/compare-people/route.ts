import { NextRequest, NextResponse } from "next/server";
import { spawn } from "node:child_process";
import path from "node:path";
import fs from "node:fs/promises";

function normalizeVideoPath(input: string) {
  return path.resolve(input.trim());
}

function resolveRepoRoot() {
  const cwd = process.cwd();
  const candidates = [cwd, path.resolve(cwd, ".."), path.resolve(cwd, "..", "..")];

  for (const candidate of candidates) {
    const backendDir = path.join(candidate, "backend");
    const frontendDir = path.join(candidate, "frontend");
    if (fs.stat(candidate).then(() => true).catch(() => false) && path.basename(candidate) === "retail-store-analysis") {
      return candidate;
    }
    if (fs.existsSync(path.join(candidate, "package.json")) && fs.existsSync(backendDir) && fs.existsSync(frontendDir)) {
      return candidate;
    }
  }

  return cwd;
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const video1 = body.video1?.trim();
    const video2 = body.video2?.trim();
    const frameInterval = Number(body.frameInterval ?? 30);

    if (!video1 || !video2) {
      return NextResponse.json(
        { error: "Please provide both video paths." },
        { status: 400 }
      );
    }

    const repoRoot = resolveRepoRoot();
    const backendRoot = path.join(repoRoot, "backend");
    const outputPath = path.join(backendRoot, "output", "people_comparison.json");
    const normalizedVideo1 = normalizeVideoPath(video1);
    const normalizedVideo2 = normalizeVideoPath(video2);

    try {
      const existing = await fs.readFile(outputPath, "utf-8");
      const cached = JSON.parse(existing);

      const existingVideo1 = cached?.video1 ? normalizeVideoPath(String(cached.video1)) : "";
      const existingVideo2 = cached?.video2 ? normalizeVideoPath(String(cached.video2)) : "";
      const existingInterval = Number(cached?.frame_interval ?? 30);

      if (
        existingVideo1 === normalizedVideo1 &&
        existingVideo2 === normalizedVideo2 &&
        existingInterval === frameInterval
      ) {
        const stream = new ReadableStream({
          start(controller) {
            const encoder = new TextEncoder();
            const send = (event: string, payload: Record<string, unknown>) => {
              controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`));
            };

            send("log", { text: "Using cached comparison result.\n" });
            send("result", { data: cached });
            send("done", {});
            controller.close();
          },
        });

        return new Response(stream, {
          headers: {
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache, no-transform",
            Connection: "keep-alive",
          },
        });
      }
    } catch {
      // No cached result yet; continue to process the input videos.
    }

    const script = path.join(backendRoot, "compare_people.py");
    const pythonExecutable = process.env.PYTHON_BIN || "python3";

    const stream = new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder();
        const send = (event: string, payload: Record<string, unknown>) => {
          controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`));
        };

        const child = spawn(pythonExecutable, ["-u", script, video1, video2, String(frameInterval)], {
          cwd: repoRoot,
          env: {
            ...process.env,
            PYTHONUNBUFFERED: "1",
          },
        });

        let stdout = "";
        let stderr = "";

        child.stdout.on("data", (chunk) => {
          const text = chunk.toString();
          stdout += text;
          process.stdout.write(text);
          send("log", { text });
        });

        child.stderr.on("data", (chunk) => {
          const text = chunk.toString();
          stderr += text;
          process.stderr.write(text);
          send("log", { text });
        });

        child.on("error", (error) => {
          const message = error instanceof Error ? error.message : "Unexpected error";
          process.stderr.write(`${message}\n`);
          send("error", { message });
          controller.close();
        });

        child.on("close", async (code) => {
          const combinedOutput = [stdout, stderr].filter(Boolean).join("\n").trim();

          if (code !== 0) {
            send("error", {
              message: stderr || "Video comparison failed.",
              output: combinedOutput || "No output was produced.",
            });
            send("done", {});
            controller.close();
            return;
          }

          try {
            const file = await fs.readFile(outputPath, "utf-8");
            const data = JSON.parse(file);
            send("result", { data, output: combinedOutput || "No output was produced." });
            send("done", {});
            controller.close();
          } catch (error) {
            const message = error instanceof Error ? error.message : "Unexpected error";
            send("error", { message, output: combinedOutput || "No output was produced." });
            send("done", {});
            controller.close();
          }
        });
      },
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unexpected error" },
      { status: 500 }
    );
  }
}
