from pathlib import Path

from langchain_core.messages import HumanMessage

from src.agent.llm import reasoning_llm, structured_output_method
from src.agent.prompts.planner import NextFilesToExplore, build_planner_prompt


async def plan_next_exploration(state: dict) -> dict:
    """Use gpt-4o to decide which files to read next based on current state."""
    prompt = build_planner_prompt(state)
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

    return {"exploration_queue": valid_files}
