# 43. Background job with a status URL
# Standalone: copy this file as-is. Deps: stdlib + fastapi

import uuid

from fastapi import BackgroundTasks, HTTPException

JOBS: dict[str, dict] = {}


def start_job(background_tasks: BackgroundTasks, fn, *args) -> dict:
    """Runs fn(job, *args) after the response. fn can set job["progress"]; result/error recorded."""
    job_id = str(uuid.uuid4())
    job = JOBS[job_id] = {"id": job_id, "status": "queued", "progress": 0, "result": None, "error": None}

    def run():
        job["status"] = "running"
        try:
            job["result"] = fn(job, *args)
            job["status"] = "done"
        except Exception as e:
            job["status"], job["error"] = "failed", str(e)

    background_tasks.add_task(run)
    return {"job_id": job_id, "status_url": f"/jobs/{job_id}"}


def get_job(job_id: str) -> dict:
    if job_id not in JOBS:
        raise HTTPException(404, "unknown job")
    return JOBS[job_id]
