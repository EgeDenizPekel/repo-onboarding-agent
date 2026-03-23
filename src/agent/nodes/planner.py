import asyncio
from pathlib import Path

from langchain_core.messages import HumanMessage

from src.agent.llm import reasoning_llm, structured_output_method
from src.agent.prompts.planner import NextFilesToExplore, build_planner_prompt
from src.agent.tools.graph_tools import query_central_files, query_frontier_files
from src.agent.tools.vector_tools import semantic_search


async def plan_next_exploration(state: dict) -> dict:
    """Use gpt-4o to decide which files to read next based on current state.

    Hybrid retrieval (RAG 2.0): semantic search over FAISS index for gap-targeted
    candidates when reflection notes exist.

    GraphRAG (Week 6): Neo4j centrality replaces the dict heuristic; frontier
    query surfaces unvisited files directly imported by already-visited ones.
    """
    run_id = state["run_id"]

    # RAG 2.0: semantic search against identified gaps (iterations 2+)
    semantic_candidates: list[str] = []
    reflection_notes = state.get("reflection_notes", "")
    if reflection_notes and state.get("repo_indexed"):
        semantic_candidates = await semantic_search(
            state["repo_path"], reflection_notes, k=8
        )

    # GraphRAG: Neo4j centrality + frontier (no-op if Neo4j not configured)
    neo4j_central, neo4j_frontier = await asyncio.gather(
        query_central_files(run_id, limit=8),
        query_frontier_files(run_id, limit=10),
    )

    prompt = build_planner_prompt(
        state,
        semantic_candidates=semantic_candidates or None,
        neo4j_central=neo4j_central or None,
        neo4j_frontier=neo4j_frontier or None,
    )
    structured_llm = reasoning_llm.with_structured_output(NextFilesToExplore, method=structured_output_method)
    result: NextFilesToExplore = await structured_llm.ainvoke(
        [HumanMessage(content=prompt)]
    )

    repo_path = Path(state["repo_path"])
    visited = set(state["visited_files"])

    # Filter: only include files that exist in the repo and haven't been visited
    valid_files = [
        f for f in result.files
        if (repo_path / f).exists() and f not in visited
    ]

    return {
        "exploration_queue": valid_files,
        "last_semantic_candidates": semantic_candidates,
        "last_frontier_files": neo4j_frontier,
    }
