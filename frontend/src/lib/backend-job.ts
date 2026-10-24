// Starts a long-running FastAPI job through the /api/backend proxy and polls it until it finishes.
export type BackendJob<T> = {
  id: string;
  status: "queued" | "running" | "completed" | "failed";
  logs: string[];
  result: T | null;
  error?: string;
};

async function readJson(response: Response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || payload.error || `Request failed (${response.status})`);
  return payload;
}

export async function runBackendJob<T>(
  startPath: string,
  jobsPath: string,
  body: unknown,
  onUpdate: (job: BackendJob<T>) => void,
): Promise<BackendJob<T>> {
  const started = await readJson(
    await fetch(`/api/backend/${startPath}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
  let failures = 0;
  while (true) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    let job: BackendJob<T>;
    try {
      job = await readJson(await fetch(`/api/backend/${jobsPath}/${started.id}`, { cache: "no-store" }));
      failures = 0;
    } catch (error) {
      // A dev-server recompile or network blip must not orphan a job that is still running.
      if (++failures >= 10) throw error;
      continue;
    }
    onUpdate(job);
    if (job.status === "failed") throw new Error(job.error || "Processing failed.");
    if (job.status === "completed") return job;
  }
}
