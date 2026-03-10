import asyncio
from pathlib import Path

import tiktoken

MAX_TOKENS = 4000

IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", "dist", "build", ".next", ".nuxt", ".eggs",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
}

_encoder = tiktoken.get_encoding("cl100k_base")


async def read_file(path: str, repo_path: str) -> str:
    """Read a file from the cloned repo, truncated to MAX_TOKENS tokens."""
    full_path = Path(repo_path) / path
    if not full_path.exists():
        return f"[File not found: {path}]"
    if not full_path.is_file():
        return f"[Not a file: {path}]"

    content = await asyncio.to_thread(
        full_path.read_text, encoding="utf-8", errors="replace"
    )
    tokens = _encoder.encode(content)
    if len(tokens) > MAX_TOKENS:
        content = _encoder.decode(tokens[:MAX_TOKENS]) + "\n\n[... truncated at 4000 tokens ...]"
    return content


async def list_directory(path: str, repo_path: str) -> list[str]:
    """List contents of a directory in the cloned repo."""
    full_path = Path(repo_path) / path
    if not full_path.is_dir():
        return []

    def _list() -> list[str]:
        return [
            str(p.relative_to(Path(repo_path)))
            for p in sorted(full_path.iterdir())
            if p.name not in IGNORED_DIRS
        ]

    return await asyncio.to_thread(_list)


def count_tokens(text: str) -> int:
    """Count tokens in text using cl100k_base encoding."""
    return len(_encoder.encode(text))
