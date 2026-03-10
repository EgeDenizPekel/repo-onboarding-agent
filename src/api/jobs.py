"""Redis-backed job store.

Job hash fields:
  job_id        str
  repo_url      str
  focus_hint    str (may be empty)
  status        pending | running | complete | error
  created_at    ISO timestamp
  result        JSON-encoded dict (set on completion)
  error         str (set on failure)

Sorted set `jobs` maps job_id -> created_at epoch for ordered listing.
SSE events published to channel `job:{job_id}:events`.
"""

import json
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis

JOB_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
JOBS_ZSET = "jobs"


def _redis_url() -> str:
    import os
    return os.getenv("REDIS_URL", "redis://localhost:6379")


def make_client() -> aioredis.Redis:
    return aioredis.from_url(_redis_url(), decode_responses=True)


def _job_key(job_id: str) -> str:
    return f"job:{job_id}"


def _channel(job_id: str) -> str:
    return f"job:{job_id}:events"


async def create_job(client: aioredis.Redis, repo_url: str, focus_hint: str) -> str:
    job_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    pipe = client.pipeline()
    pipe.hset(_job_key(job_id), mapping={
        "job_id": job_id,
        "repo_url": repo_url,
        "focus_hint": focus_hint,
        "status": "pending",
        "created_at": now.isoformat(),
    })
    pipe.expire(_job_key(job_id), JOB_TTL_SECONDS)
    pipe.zadd(JOBS_ZSET, {job_id: now.timestamp()})
    pipe.expire(JOBS_ZSET, JOB_TTL_SECONDS)
    await pipe.execute()
    return job_id


async def set_running(client: aioredis.Redis, job_id: str) -> None:
    await client.hset(_job_key(job_id), "status", "running")


async def set_complete(client: aioredis.Redis, job_id: str, result: dict) -> None:
    pipe = client.pipeline()
    pipe.hset(_job_key(job_id), mapping={
        "status": "complete",
        "result": json.dumps(result),
    })
    pipe.expire(_job_key(job_id), JOB_TTL_SECONDS)
    await pipe.execute()


async def set_error(client: aioredis.Redis, job_id: str, message: str) -> None:
    await client.hset(_job_key(job_id), mapping={
        "status": "error",
        "error": message,
    })


async def get_job(client: aioredis.Redis, job_id: str) -> dict | None:
    data = await client.hgetall(_job_key(job_id))
    if not data:
        return None
    if data.get("result"):
        data["result"] = json.loads(data["result"])
    return data


async def list_jobs(client: aioredis.Redis, limit: int = 50) -> list[dict]:
    """Return jobs ordered by created_at descending."""
    job_ids = await client.zrevrange(JOBS_ZSET, 0, limit - 1)
    jobs = []
    for job_id in job_ids:
        data = await client.hgetall(_job_key(job_id))
        if data:
            # Omit heavy result payload from list view
            data.pop("result", None)
            jobs.append(data)
    return jobs


async def publish_event(client: aioredis.Redis, job_id: str, event: dict) -> None:
    await client.publish(_channel(job_id), json.dumps(event))
