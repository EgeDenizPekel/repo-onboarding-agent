from pydantic import BaseModel, Field

from src.agent.state import RepoState

PLAN_NEXT_EXPLORATION_PROMPT = """\
You are analyzing a code repository to build a developer onboarding guide.

## Repository: {repo_url}
## Language: {primary_language} | Framework: {framework}

## File Tree:
{file_tree}

## Files Already Visited ({visited_count} files):
{visited_files}

## File Summaries (most recent):
{file_summaries}

## Most-Imported Files (import graph signal):
{import_graph_summary}
{focus_section}{reflection_section}
## Task
Select the next 3-5 files to read. Prioritize:
1. Files most frequently imported by already-visited files (high architectural centrality)
2. Files that address gaps identified in the reflection notes
3. Entry points and core modules not yet visited

Rules:
- Only include files visible in the file tree above
- Never include already-visited files
- Prefer source files (.py, .ts, .js, .go, .rs) over config files

Respond with JSON in exactly this format:
{{"files": ["path/to/file1.py", "path/to/file2.py"], "reasoning": "one sentence"}}
"""


class NextFilesToExplore(BaseModel):
    files: list[str] = Field(
        description="3-5 file paths to explore next, relative to the repo root"
    )
    reasoning: str = Field(description="One sentence explaining why these files were chosen")


def build_planner_prompt(state: RepoState) -> str:
    visited_str = (
        "\n".join(f"  - {f}" for f in state["visited_files"]) or "  None yet"
    )

    # Cap at 10 most recent summaries to keep prompt size manageable
    recent_summaries = list(state["file_summaries"].items())[-10:]
    summaries_str = "\n\n".join(
        f"**{path}:** {summary[:200]}{'...' if len(summary) > 200 else ''}"
        for path, summary in recent_summaries
    ) or "  None yet"

    focus_section = (
        f"\n## Focus Hint from User:\n{state['focus_hint']}\n"
        if state.get("focus_hint")
        else ""
    )
    reflection_section = (
        f"\n## Reflection Notes (gaps to fill):\n{state['reflection_notes']}\n"
        if state.get("reflection_notes")
        else ""
    )

    return PLAN_NEXT_EXPLORATION_PROMPT.format(
        repo_url=state["repo_url"],
        primary_language=state["primary_language"],
        framework=state.get("framework") or "Unknown",
        file_tree=state["file_tree"][:3000],
        visited_count=len(state["visited_files"]),
        visited_files=visited_str,
        file_summaries=summaries_str,
        import_graph_summary=_format_import_graph(state["import_graph"]),
        focus_section=focus_section,
        reflection_section=reflection_section,
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
