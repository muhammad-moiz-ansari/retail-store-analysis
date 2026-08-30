import { NextRequest, NextResponse } from "next/server";
import { spawn } from "node:child_process";
import path from "node:path";
import fs from "node:fs/promises";

function normalizeVideoPath(input: string) {
  return path.resolve(input.trim());
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

    const root = path.resolve(process.cwd(), "..");
    const outputPath = path.join(root, "output", "people_comparison.json");
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
        return NextResponse.json({ data: cached });
      }
    } catch {
      // No cached result yet; continue to process the input videos.
    }

    const script = path.join(root, "compare_people.py");
    const pythonExecutable = path.join(root, ".venv", "bin", "python");

    const result = await new Promise<{ stdout: string; stderr: string; code: number | null }>((resolve, reject) => {
      const child = spawn(pythonExecutable, [script, video1, video2, String(frameInterval)], {
        cwd: root,
      });

      let stdout = "";
      let stderr = "";

      child.stdout.on("data", (chunk) => {
        stdout += chunk.toString();
      });

      child.stderr.on("data", (chunk) => {
        stderr += chunk.toString();
      });

      child.on("error", (error) => {
        reject(error);
      });

      child.on("close", (code) => {
        resolve({ stdout, stderr, code });
      });
    });

    if (result.code !== 0) {
      return NextResponse.json(
        { error: result.stderr || "Video comparison failed." },
        { status: 500 }
      );
    }

    const file = await fs.readFile(outputPath, "utf-8");
    const data = JSON.parse(file);

    return NextResponse.json({ data });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unexpected error" },
      { status: 500 }
    );
  }
}
