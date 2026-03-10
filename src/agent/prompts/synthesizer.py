from src.agent.state import RepoState

SYNTHESIZE_PROMPT = """\
You are writing a developer onboarding guide for a code repository.
You have already explored the codebase thoroughly. Use everything you have learned to produce
a complete, accurate, and useful guide for a developer joining this project for the first time.

## Repository: {repo_url}
## Language: {primary_language} | Framework: {framework}

## File Tree:
{file_tree}

## Dependencies:
{dependencies}

## Entry Points:
{entry_points}

## File Summaries (from exploration):
{file_summaries}

## Architecture Notes (from reflection):
{architecture_notes}
{focus_section}
## Output Format

Write the complete onboarding guide in this exact structure:

# Onboarding Guide: {repo_name}

## What This Project Does
One paragraph. Plain English. No jargon. What problem does it solve and who uses it?

## Tech Stack
Bullet list. Language, framework, and key dependencies with one-line descriptions each.

## Repository Structure
Annotated directory tree. Every top-level directory with a one-line description.
Call out the most important files and their roles.

## Architecture Overview
How the main components connect. Data flow from entry to output.
Use specific file references (e.g. `src/main.py`) for each component.

## Entry Points
Where to start reading and exactly why.
Format: `path/to/file.py` - what it does and why it matters.

## Recommended Reading Order
Numbered list. Each item: file path + what you will learn from reading it.
Start with the file that gives the clearest mental model of the whole system.

## Key Concepts
Domain concepts or non-obvious patterns a newcomer needs before the code makes sense.
Skip anything obvious or language-standard.

## How to Run It
Setup and run instructions. Extract from README, Makefile, or scripts if available.

## Where to Contribute
Key extension points, open TODOs, or areas with thin coverage that a new contributor should know about.

Rules:
- Every file reference must be a real path that exists in the file tree above
- Be specific - name files, not just directories
- If you are unsure about a detail, omit it rather than guess
- Do not repeat yourself across sections
"""


def build_synthesize_prompt(state: RepoState) -> str:
    repo_name = state["repo_url"].rstrip("/").split("/")[-1]

    summaries_str = "\n\n".join(
        f"**{path}:**\n{summary[:400]}{'...' if len(summary) > 400 else ''}"
        for path, summary in state["file_summaries"].items()
    ) or "  None available."

    architecture_notes_str = (
        "\n".join(f"- {note}" for note in state["architecture_notes"])
        or "  None recorded."
    )

    entry_points_str = (
        "\n".join(f"- {ep}" for ep in state["entry_points"])
        or "  None identified."
    )

    deps = state.get("dependencies") or {}
    deps_str = (
        "\n".join(f"- {k}: {v}" for k, v in list(deps.items())[:20])
        if deps
        else "  Not parsed."
    )

    focus_section = (
        f"\n## Focus Hint from User:\n{state['focus_hint']}\nEmphasize this area in the guide.\n"
        if state.get("focus_hint")
        else ""
    )

    return SYNTHESIZE_PROMPT.format(
        repo_url=state["repo_url"],
        repo_name=repo_name,
        primary_language=state["primary_language"],
        framework=state.get("framework") or "Unknown",
        file_tree=state["file_tree"][:3000],
        dependencies=deps_str,
        entry_points=entry_points_str,
        file_summaries=summaries_str,
        architecture_notes=architecture_notes_str,
        focus_section=focus_section,
    )
