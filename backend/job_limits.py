"""In-memory CV job admission shared by the unified backend and the camera service (SECURITY_REVIEW S8)."""

from fastapi import HTTPException

MAX_RUNNING_JOBS, MAX_KEPT_JOBS = 2, 50
ACTIVE = {"queued", "running"}


def admit_job(jobs: dict, max_running: int = MAX_RUNNING_JOBS, max_kept: int = MAX_KEPT_JOBS) -> None:
    """Refuse with 429 when max_running jobs are active; otherwise drop the oldest finished jobs beyond max_kept."""
    if sum(job["status"] in ACTIVE for job in jobs.values()) >= max_running:
        raise HTTPException(status_code=429, detail=f"{max_running} CV jobs are already running; wait for one to finish")
    for old in [k for k, job in jobs.items() if job["status"] not in ACTIVE][:-max_kept or None]:
        del jobs[old]  # dicts keep insertion order, so this drops the oldest finished jobs
