"""FastAPI application.

Endpoints:
  POST /generate              Start agent job, returns job_id
  GET  /stream/{job_id}       SSE stream of node events
  GET  /status/{job_id}       Poll-based job status + result
  GET  /jobs                  List recent jobs (no result payload)
  GET  /jobs/{job_id}         Full job detail including result
  GET  /eval/results          Serve eval/results.json
  GET  /health                Health check
"""

import asyncio
import json
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.api import jobs as job_store
from src.api.runner import run_job

EVAL_RESULTS_PATH = Path("eval/results.json")

app = FastAPI(title="Repo Onboarding Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_redis():
    client = job_store.make_client()
    try:
        yield client
    finally:
        await client.aclose()


# ── Request/response models ──────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    repo_url: str
    focus_hint: str = ""


class GenerateResponse(BaseModel):
    job_id: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    from fastapi import Depends
    client = job_store.make_client()
    job_id = await job_store.create_job(client, req.repo_url, req.focus_hint)
    background_tasks.add_task(run_job, client, job_id, req.repo_url, req.focus_hint)
    return GenerateResponse(job_id=job_id)


@app.get("/stream/{job_id}")
async def stream(job_id: str):
    client = job_store.make_client()

    job = await job_store.get_job(client, job_id)
    if not job:
        await client.aclose()
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        # If job already complete/error, emit final event and close
        if job["status"] == "complete":
            result = job.get("result", {})
            yield {
                "event": "complete",
                "data": json.dumps({
                    "event": "complete",
                    "onboarding_document": result.get("onboarding_document", ""),
                }),
            }
            await client.aclose()
            return

        if job["status"] == "error":
            yield {
                "event": "error",
                "data": json.dumps({"event": "error", "message": job.get("error", "")}),
            }
            await client.aclose()
            return

        # Subscribe and stream live events
        pubsub = client.pubsub()
        await pubsub.subscribe(job_store._channel(job_id))
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = json.loads(message["data"])
                yield {"event": data["event"], "data": json.dumps(data)}
                if data["event"] in ("complete", "error"):
                    break
        finally:
            await pubsub.unsubscribe(job_store._channel(job_id))
            await pubsub.aclose()
            await client.aclose()

    return EventSourceResponse(event_generator())


@app.get("/status/{job_id}")
async def status(job_id: str):
    client = job_store.make_client()
    job = await job_store.get_job(client, job_id)
    await client.aclose()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs")
async def list_jobs():
    client = job_store.make_client()
    jobs = await job_store.list_jobs(client)
    await client.aclose()
    return {"jobs": jobs}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    client = job_store.make_client()
    job = await job_store.get_job(client, job_id)
    await client.aclose()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/eval/results")
async def eval_results():
    if not EVAL_RESULTS_PATH.exists():
        raise HTTPException(status_code=404, detail="Eval results not found")
    return json.loads(EVAL_RESULTS_PATH.read_text())
