import asyncio

from langchain_core.messages import HumanMessage

from src.agent.llm import summary_llm
from src.agent.prompts.explorer import build_file_summary_prompt
from src.agent.tools.file_tools import read_file
from src.agent.tools.graph_tools import sync_imports
from src.agent.tools.search_tools import get_imports

BATCH_SIZE = 5


async def explore_files(state: dict) -> dict:
    """Read and summarize the next batch of files. Update file_summaries and import_graph."""
    repo_path = state["repo_path"]
    language = state["primary_language"]
    queue = list(state["exploration_queue"])

    batch = queue[:BATCH_SIZE]
    remaining = queue[BATCH_SIZE:]

    file_summaries = dict(state["file_summaries"])
    import_graph = dict(state["import_graph"])
    visited = list(state["visited_files"])

    results = await asyncio.gather(
        *[_process_file(path, repo_path, language) for path in batch],
        return_exceptions=True,
    )

    new_imports: dict[str, list[str]] = {}
    for path, result in zip(batch, results):
        if isinstance(result, Exception):
            file_summaries[path] = f"[Error processing file: {result}]"
        else:
            summary, imports = result
            file_summaries[path] = summary
            import_graph[path] = imports
            new_imports[path] = imports

        if path not in visited:
            visited.append(path)

    # Sync new import edges to Neo4j (no-op if NEO4J_URI not configured)
    await sync_imports(state["run_id"], repo_path, new_imports)

    return {
        "file_summaries": file_summaries,
        "import_graph": import_graph,
        "visited_files": visited,
        "exploration_queue": remaining,
    }


async def _process_file(
    path: str, repo_path: str, language: str
) -> tuple[str, list[str]]:
    content, imports = await asyncio.gather(
        read_file(path, repo_path),
        get_imports(path, repo_path),
    )
    prompt = build_file_summary_prompt(path, language, content)
    response = await summary_llm.ainvoke([HumanMessage(content=prompt)])
    return response.content, imports
