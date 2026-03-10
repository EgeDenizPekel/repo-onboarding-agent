import asyncio
import json
from pathlib import Path

import git

from src.config import CLONE_BASE_DIR, MAX_ITERATIONS_DEFAULT

IGNORED_NAMES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", "dist", "build", ".next", ".nuxt", ".eggs",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "coverage",
}


async def clone_repo(state: dict) -> dict:
    """Clone the GitHub repo locally. Detect language, framework, and build file tree."""
    repo_url: str = state["repo_url"]

    # Derive a safe directory name from the owner/repo segments of the URL
    parts = repo_url.rstrip("/").rstrip(".git").split("/")
    repo_name = f"{parts[-2]}_{parts[-1]}" if len(parts) >= 2 else parts[-1]
    clone_path = CLONE_BASE_DIR / repo_name

    CLONE_BASE_DIR.mkdir(parents=True, exist_ok=True)

    if clone_path.exists():
        repo = git.Repo(clone_path)
        await asyncio.to_thread(repo.remotes.origin.pull)
    else:
        await asyncio.to_thread(git.Repo.clone_from, repo_url, clone_path)

    file_tree = _build_file_tree(clone_path)
    primary_language = _detect_language(clone_path)
    framework = _detect_framework(clone_path, primary_language)

    return {
        "repo_path": str(clone_path),
        "file_tree": file_tree,
        "primary_language": primary_language,
        "framework": framework,
        "visited_files": [],
        "file_summaries": {},
        "dependencies": {},
        "import_graph": {},
        "entry_points": [],
        "architecture_notes": [],
        "exploration_queue": [],
        "understanding_score": 0.0,
        "reflection_notes": "",
        "iteration_count": 0,
        "max_iterations": state.get("max_iterations", MAX_ITERATIONS_DEFAULT),
        "onboarding_draft": "",
        "validation_errors": [],
        "onboarding_final": "",
    }


def _build_file_tree(path: Path, prefix: str = "", max_depth: int = 4, depth: int = 0) -> str:
    if depth >= max_depth:
        return ""
    try:
        entries = sorted(
            [
                e for e in path.iterdir()
                if e.name not in IGNORED_NAMES and not e.name.endswith(".egg-info")
            ],
            key=lambda e: (e.is_file(), e.name.lower()),
        )
    except PermissionError:
        return ""

    lines = []
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        child_prefix = prefix + ("    " if is_last else "│   ")

        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            subtree = _build_file_tree(entry, child_prefix, max_depth, depth + 1)
            if subtree:
                lines.append(subtree)
        else:
            lines.append(f"{prefix}{connector}{entry.name}")

    return "\n".join(lines)


def _detect_language(repo: Path) -> str:
    if (
        (repo / "pyproject.toml").exists()
        or (repo / "requirements.txt").exists()
        or (repo / "setup.py").exists()
    ):
        return "Python"
    if (repo / "tsconfig.json").exists():
        return "TypeScript"
    if (repo / "package.json").exists():
        return "JavaScript"
    if (repo / "go.mod").exists():
        return "Go"
    if (repo / "Cargo.toml").exists():
        return "Rust"
    if (repo / "pom.xml").exists() or (repo / "build.gradle").exists():
        return "Java"
    if (repo / "Gemfile").exists():
        return "Ruby"

    # Fallback: count source file extensions
    counts = {
        "Python": len(list(repo.rglob("*.py"))),
        "JavaScript": len(list(repo.rglob("*.js"))),
        "TypeScript": len(list(repo.rglob("*.ts"))),
    }
    if max(counts.values()) > 0:
        return max(counts, key=counts.__getitem__)

    return "Unknown"


def _detect_framework(repo: Path, language: str) -> str | None:
    if language == "Python":
        deps_text = ""
        for dep_file in ["requirements.txt", "pyproject.toml", "setup.py", "setup.cfg"]:
            p = repo / dep_file
            if p.exists():
                deps_text += p.read_text(errors="replace").lower()
        if "django" in deps_text:
            return "Django"
        if "fastapi" in deps_text:
            return "FastAPI"
        if "flask" in deps_text:
            return "Flask"
        return None

    if language in ("JavaScript", "TypeScript"):
        pkg_json = repo / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text())
                all_deps = " ".join(
                    list(data.get("dependencies", {}).keys())
                    + list(data.get("devDependencies", {}).keys())
                ).lower()
                if "next" in all_deps:
                    return "Next.js"
                if "react" in all_deps:
                    return "React"
                if "vue" in all_deps:
                    return "Vue"
                if "express" in all_deps:
                    return "Express"
                if "svelte" in all_deps:
                    return "Svelte"
                if "vite" in all_deps:
                    return "Vite"
            except Exception:
                pass

    return None
