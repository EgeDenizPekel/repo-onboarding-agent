from src.agent.tools.vector_tools import build_repo_index


async def index_repo(state: dict) -> dict:
    """Build a FAISS vector index over all files in the cloned repo.

    Runs once after initialize_exploration. Subsequent planner calls use
    the index for semantic retrieval against reflection-identified gaps.
    """
    await build_repo_index(state["repo_path"])
    return {"repo_indexed": True}
