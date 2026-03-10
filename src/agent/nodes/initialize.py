from pathlib import Path

from src.agent.tools.dependency_tools import get_entry_points, parse_dependencies


async def initialize_exploration(state: dict) -> dict:
    """Read README and dependency files. Seed the exploration queue with entry points."""
    repo_path = state["repo_path"]
    language = state["primary_language"]
    framework = state.get("framework")

    # Read README - preserve existing file_summaries from clone node
    file_summaries = dict(state.get("file_summaries", {}))
    for readme_name in ["README.md", "readme.md", "README.rst", "README.txt", "README"]:
        readme_path = Path(repo_path) / readme_name
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8", errors="replace")
            file_summaries[readme_name] = content[:2000]
            break

    dependencies = await parse_dependencies(repo_path)
    entry_points = await get_entry_points(repo_path, language, framework)

    # Seed queue: entry points first, then common structural files
    exploration_queue = list(entry_points)
    for candidate in _candidate_files(repo_path, language):
        if candidate not in exploration_queue:
            exploration_queue.append(candidate)

    return {
        "file_summaries": file_summaries,
        "dependencies": dependencies,
        "entry_points": entry_points,
        "exploration_queue": exploration_queue,
    }


def _candidate_files(repo_path: str, language: str) -> list[str]:
    """Return language-specific files worth exploring early, beyond entry points."""
    repo = Path(repo_path)

    if language == "Python":
        check = [
            "src/main.py", "main.py", "app.py", "cli.py",
            "pyproject.toml", "setup.py",
        ]
    elif language in ("JavaScript", "TypeScript"):
        check = [
            "src/index.ts", "src/index.js", "index.ts", "index.js",
            "package.json", "tsconfig.json",
        ]
    else:
        check = []

    return [f for f in check if (repo / f).exists()]
