"""Background agent runner.

Runs the LangGraph graph, streams per-node events via Redis pub/sub,
and writes the final result to the job hash on completion.
"""

import asyncio

import redis.asyncio as aioredis

from src.agent.graph import build_graph
from src.agent.state import create_initial_state
from src.api import jobs as job_store

# Build graph once at module import (reused across jobs)
_graph = build_graph()


async def run_job(client: aioredis.Redis, job_id: str, repo_url: str, focus_hint: str) -> None:
    await job_store.set_running(client, job_id)

    try:
        initial_state = create_initial_state(repo_url, focus_hint=focus_hint or None)

        iteration_log: list[dict] = []
        files_explored_this_iter: list[str] = []
        prev_visited: set[str] = set()
        prev_arch_notes_count: int = 0
        final_state: dict = dict(initial_state)

        async for chunk in _graph.astream(initial_state, stream_mode="updates"):
            for node_name, updates in chunk.items():
                for k, v in updates.items():
                    final_state[k] = v

                await job_store.publish_event(client, job_id, {
                    "event": "node_start",
                    "node": node_name,
                })

                if node_name == "explore_files":
                    new_visited = set(updates.get("visited_files", []))
                    files_explored_this_iter = sorted(new_visited - prev_visited)
                    prev_visited = new_visited
                    await job_store.publish_event(client, job_id, {
                        "event": "node_complete",
                        "node": node_name,
                        "files_explored": files_explored_this_iter,
                    })

                elif node_name == "reflect":
                    arch_notes: list[str] = updates.get("architecture_notes", [])
                    new_notes = arch_notes[prev_arch_notes_count:]
                    prev_arch_notes_count = len(arch_notes)
                    score = updates.get("understanding_score", 0.0)
                    iteration = updates.get("iteration_count", 0)

                    iteration_log.append({
                        "iteration": iteration,
                        "files_explored": files_explored_this_iter,
                        "understanding_score": score,
                        "reflection_notes": updates.get("reflection_notes", ""),
                        "architecture_notes_added": new_notes,
                    })
                    files_explored_this_iter = []

                    await job_store.publish_event(client, job_id, {
                        "event": "node_complete",
                        "node": node_name,
                        "understanding_score": score,
                        "iteration": iteration,
                        "reflection_notes": updates.get("reflection_notes", ""),
                    })

                else:
                    await job_store.publish_event(client, job_id, {
                        "event": "node_complete",
                        "node": node_name,
                    })

        onboarding_doc = final_state.get("onboarding_final") or final_state.get("onboarding_draft", "")
        result = {
            "onboarding_document": onboarding_doc,
            "iteration_log": iteration_log,
            "architecture_notes": final_state.get("architecture_notes", []),
            "primary_language": final_state.get("primary_language", ""),
            "framework": final_state.get("framework", ""),
            "entry_points": final_state.get("entry_points", []),
            "visited_files": list(final_state.get("visited_files", [])),
        }

        await job_store.set_complete(client, job_id, result)
        await job_store.publish_event(client, job_id, {
            "event": "complete",
            "onboarding_document": onboarding_doc,
        })

    except Exception as e:
        await job_store.set_error(client, job_id, str(e))
        await job_store.publish_event(client, job_id, {
            "event": "error",
            "message": str(e),
        })
