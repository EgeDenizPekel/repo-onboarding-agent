import os
import re

# Matches file paths in backticks, e.g. `src/main.py` or `src/main.py:42`
_FILE_REF_RE = re.compile(r"`([a-zA-Z0-9_./-]+\.[a-zA-Z0-9]{1,10}(?::\d+)?)`")


def _extract_file_refs(text: str) -> list[str]:
    """Extract unique file paths from backtick references in the draft."""
    paths = set()
    for match in _FILE_REF_RE.finditer(text):
        ref = match.group(1)
        path = ref.split(":")[0]  # strip line numbers like :42
        paths.add(path)
    return list(paths)


async def validate(state: dict) -> dict:
    """Check every file reference in the draft against the real repo on disk.

    Uses os.path.exists - never delegates path checking to an LLM.
    """
    repo_path = state["repo_path"]
    draft = state["onboarding_draft"]

    refs = _extract_file_refs(draft)
    errors = [
        f"`{ref}` does not exist in the repository"
        for ref in refs
        if not os.path.exists(os.path.join(repo_path, ref))
    ]

    return {"validation_errors": errors}
