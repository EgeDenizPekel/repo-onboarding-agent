from pydantic import BaseModel, Field

from src.agent.state import RepoState

REFLECT_PROMPT = """\
You are building a developer onboarding guide for a code repository.
Assess your current understanding of its architecture.

## Repository: {repo_url}
## Language: {primary_language} | Framework: {framework}
## Iteration: {iteration_count} / {max_iterations}

## Full File Tree:
{file_tree}

## Files Explored ({visited_count} total):
{file_summaries}

## Import Graph Summary:
{import_graph_summary}

## Entry Points Identified:
{entry_points}
{focus_section}
## Scoring Guide
- 1.0: Architecture, all main data flows, entry points, and key modules are fully clear
- 0.8: Solid picture with a few non-critical gaps remaining
- 0.6: Entry points understood but key architectural components unexplored
- 0.4: Surface-level; major components still unknown
- 0.2: Barely started; architecture is still opaque
- 0.0: No meaningful exploration yet

Score conservatively. Only assign 0.8+ if you can describe the main data flow \
from entry to output with specific file references.

Respond with JSON in exactly this format:
{{"understanding_score": 0.0, "reflection_notes": "what is understood and what gaps remain", "architecture_notes": ["insight 1", "insight 2"]}}
"""


class ReflectionResult(BaseModel):
    understanding_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Score from 0.0 to 1.0 representing how well the codebase is understood",
    )
    reflection_notes: str = Field(
        description="What is understood well and what specific gaps remain"
    )
    architecture_notes: list[str] = Field(
        default_factory=list,
        description="New architectural insights discovered in this iteration",
    )


def build_reflect_prompt(state: RepoState) -> str:
    summaries_str = "\n\n".join(
        f"**{path}:** {summary[:300]}{'...' if len(summary) > 300 else ''}"
        for path, summary in state["file_summaries"].items()
    ) or "  None yet"

    entry_points_str = (
        "\n".join(f"  - {ep}" for ep in state["entry_points"])
        or "  None identified yet"
    )

    focus_section = (
        f"\n## Focus Hint from User:\n{state['focus_hint']}\n"
        if state.get("focus_hint")
        else ""
    )

    return REFLECT_PROMPT.format(
        repo_url=state["repo_url"],
        primary_language=state["primary_language"],
        framework=state.get("framework") or "Unknown",
        iteration_count=state["iteration_count"],
        max_iterations=state["max_iterations"],
        file_tree=state["file_tree"][:2000],
        visited_count=len(state["visited_files"]),
        file_summaries=summaries_str,
        import_graph_summary=_format_import_graph(state["import_graph"]),
        entry_points=entry_points_str,
        focus_section=focus_section,
    )


def _format_import_graph(import_graph: dict) -> str:
    if not import_graph:
        return "  No import data yet."

    import_counts: dict[str, int] = {}
    for imports in import_graph.values():
        for imp in imports:
            import_counts[imp] = import_counts.get(imp, 0) + 1

    if not import_counts:
        return "  No cross-file imports detected yet."

    top = sorted(import_counts.items(), key=lambda x: -x[1])[:8]
    return "\n".join(f"  {file}: imported {count}x" for file, count in top)
