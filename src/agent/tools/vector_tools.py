"""Vector index for semantic file retrieval (RAG 2.0).

Builds a FAISS index over every file in a cloned repo (path + content preview).
Stored in a module-level side-channel dict keyed by repo_path so the index
survives across graph node invocations without polluting LangGraph state.
"""

import asyncio
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", "dist", "build", ".next", ".nuxt",
}

_PREVIEW_CHARS = 300
_MAX_FILES = 2000

# Side-channel storage: repo_path -> FAISS index
_repo_indexes: dict[str, FAISS] = {}

_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


def _collect_files(repo_path: str) -> list[tuple[str, str]]:
    """Return (relative_path, content_preview) for up to _MAX_FILES source files."""
    repo = Path(repo_path)
    results = []

    for path in sorted(repo.rglob("*")):
        if len(results) >= _MAX_FILES:
            break
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        # Skip binary / very large files
        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".ico",
                                   ".woff", ".woff2", ".ttf", ".eot",
                                   ".zip", ".tar", ".gz", ".pyc", ".db"):
            continue
        try:
            preview = path.read_text(encoding="utf-8", errors="replace")[:_PREVIEW_CHARS]
            rel = str(path.relative_to(repo))
            results.append((rel, preview))
        except Exception:
            continue

    return results


async def build_repo_index(repo_path: str) -> None:
    """Embed all files in the repo and store the FAISS index in the side-channel."""
    if repo_path in _repo_indexes:
        return  # Already indexed (e.g. retry run)

    file_pairs = await asyncio.to_thread(_collect_files, repo_path)
    if not file_pairs:
        return

    # Document text = file path + newline + content preview
    texts = [f"{rel}\n{preview}" for rel, preview in file_pairs]
    metadatas = [{"path": rel} for rel, _ in file_pairs]

    index = await FAISS.afrom_texts(texts, _embeddings, metadatas=metadatas)
    _repo_indexes[repo_path] = index


async def semantic_search(repo_path: str, query: str, k: int = 8) -> list[str]:
    """Return up to k file paths most semantically similar to query.

    Returns an empty list if no index exists for this repo.
    """
    index = _repo_indexes.get(repo_path)
    if index is None:
        return []

    docs = await index.asimilarity_search(query, k=k)
    return [doc.metadata["path"] for doc in docs]


def clear_repo_index(repo_path: str) -> None:
    """Remove the index for a repo (called after agent run to free memory)."""
    _repo_indexes.pop(repo_path, None)
