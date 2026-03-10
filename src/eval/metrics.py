"""Deterministic metrics for evaluating onboarding document quality.

All functions are pure - no LLM calls. Safe to run in tests.
"""

import os
import re
from collections import Counter

# Same regex as validator.py - backtick file references like `src/main.py` or `src/main.py:42`
_FILE_REF_RE = re.compile(r"`([a-zA-Z0-9_./-]+\.[a-zA-Z0-9]{1,10}(?::\d+)?)`")


def file_ref_accuracy(draft: str, repo_path: str) -> float:
    """Fraction of backtick file references in the draft that exist on disk.

    1.0 = every cited file exists (perfect)
    0.0 = every cited file is hallucinated (worst case)
    Returns 1.0 when the draft contains no file references.
    """
    refs: set[str] = set()
    for match in _FILE_REF_RE.finditer(draft):
        path = match.group(1).split(":")[0]
        refs.add(path)

    if not refs:
        return 1.0

    existing = sum(1 for r in refs if os.path.exists(os.path.join(repo_path, r)))
    return existing / len(refs)


def architecture_coverage(draft: str, import_graph: dict[str, list[str]]) -> float:
    """Fraction of the top-10 most-imported modules mentioned in the draft.

    import_graph maps {file_path: [list of paths it imports]}.
    Files that are imported by many others are architecturally central.
    Returns 0.0 when import_graph is empty (e.g. baseline config).
    """
    if not import_graph:
        return 0.0

    # Invert: count how many files import each module
    imported_by: Counter[str] = Counter()
    for imports in import_graph.values():
        for imp in imports:
            imported_by[imp] += 1

    if not imported_by:
        return 0.0

    top_modules = [m for m, _ in imported_by.most_common(10)]
    draft_lower = draft.lower()

    mentioned = 0
    for module in top_modules:
        # Match on basename (without extension) or full path
        basename = os.path.splitext(os.path.basename(module))[0].lower()
        if basename in draft_lower or module.lower() in draft_lower:
            mentioned += 1

    return mentioned / len(top_modules)


def entry_point_accuracy(draft: str, entry_points: list[str]) -> float:
    """Fraction of identified entry points mentioned in the draft.

    Returns 1.0 when no entry points were identified (metric not applicable).
    """
    if not entry_points:
        return 1.0

    draft_lower = draft.lower()
    mentioned = sum(
        1 for ep in entry_points
        if os.path.basename(ep).lower() in draft_lower or ep.lower() in draft_lower
    )
    return mentioned / len(entry_points)
