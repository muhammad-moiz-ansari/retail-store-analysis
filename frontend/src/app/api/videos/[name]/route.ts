import { NextRequest, NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";

const allowedVideos = new Set(["cam1_tracked.mp4", "cam2_tracked.mp4"]);

function resolveRepoRoot() {
  const cwd = process.cwd();
  const candidates = [cwd, path.resolve(cwd, ".."), path.resolve(cwd, "..", "..")];

  for (const candidate of candidates) {
    if (path.basename(candidate) === "retail-store-analysis" && fs.existsSync(candidate)) {
      return candidate;
    }

    if (
      fs.existsSync(path.join(candidate, "package.json")) &&
      fs.existsSync(path.join(candidate, "backend")) &&
      fs.existsSync(path.join(candidate, "frontend"))
    ) {
      return candidate;
    }
  }

  return cwd;
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ name: string }> }
) {
  const { name } = await context.params;

  if (!allowedVideos.has(name)) {
    return NextResponse.json({ error: "Video not found." }, { status: 404 });
  }

  const videoPath = path.join(resolveRepoRoot(), "backend", "videos", name);

  if (!fs.existsSync(videoPath)) {
    return NextResponse.json({ error: "Video file is missing." }, { status: 404 });
  }

  const stat = fs.statSync(videoPath);
  const range = request.headers.get("range");

  if (range) {
    const [startText, endText] = range.replace(/bytes=/, "").split("-");
    const start = Number.parseInt(startText, 10);
    const end = endText ? Number.parseInt(endText, 10) : stat.size - 1;

    if (Number.isNaN(start) || Number.isNaN(end) || start >= stat.size || end >= stat.size || start > end) {
      return new Response(null, {
        status: 416,
        headers: {
          "Content-Range": `bytes */${stat.size}`,
        },
      });
    }

    return new Response(fs.createReadStream(videoPath, { start, end }) as unknown as BodyInit, {
      status: 206,
      headers: {
        "Accept-Ranges": "bytes",
        "Content-Length": String(end - start + 1),
        "Content-Range": `bytes ${start}-${end}/${stat.size}`,
        "Content-Type": "video/mp4",
      },
    });
  }

  return new Response(fs.createReadStream(videoPath) as unknown as BodyInit, {
    headers: {
      "Accept-Ranges": "bytes",
      "Content-Length": String(stat.size),
      "Content-Type": "video/mp4",
    },
  });
}
