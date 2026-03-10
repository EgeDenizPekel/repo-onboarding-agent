import ast
import asyncio
import re
from pathlib import Path

IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", "dist", "build", ".next", ".nuxt",
}


async def search_code(
    pattern: str, repo_path: str, file_extension: str = ""
) -> list[dict]:
    """Search for a regex pattern across the repo. Returns up to 50 matches."""
    repo = Path(repo_path)
    compiled = re.compile(pattern)
    glob = f"*{file_extension}" if file_extension else "*"

    def _search() -> list[dict]:
        results = []
        for path in repo.rglob(glob):
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            if not path.is_file():
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(content.splitlines(), 1):
                    if compiled.search(line):
                        results.append({
                            "file": str(path.relative_to(repo)),
                            "line": i,
                            "content": line.strip(),
                        })
                        if len(results) >= 50:
                            return results
            except Exception:
                continue
        return results

    return await asyncio.to_thread(_search)


async def get_imports(file_path: str, repo_path: str) -> list[str]:
    """Parse import statements from a Python or JS/TS file.

    Python: resolves imports to actual file paths within the repo.
    JS/TS: returns raw relative import strings (e.g. './utils').
    """
    full_path = Path(repo_path) / file_path
    if not full_path.exists():
        return []

    suffix = full_path.suffix.lower()
    content = await asyncio.to_thread(
        full_path.read_text, encoding="utf-8", errors="replace"
    )

    if suffix == ".py":
        return _get_python_imports(content, file_path, repo_path)
    if suffix in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
        return _get_js_imports(content)
    return []


def _get_python_imports(content: str, file_path: str, repo_path: str) -> list[str]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    repo = Path(repo_path)
    file_parent = (repo / file_path).parent
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            # Relative import: go up `level` directories from the current file
            target_dir = file_parent
            for _ in range(node.level - 1):
                target_dir = target_dir.parent

            target = target_dir / Path(*node.module.split(".")) if node.module else target_dir
            for candidate in [target.with_suffix(".py"), target / "__init__.py"]:
                if candidate.exists():
                    try:
                        imports.append(str(candidate.relative_to(repo)))
                    except ValueError:
                        pass
                    break

        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            resolved = _resolve_absolute_import(node.module, repo)
            if resolved:
                imports.append(resolved)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                resolved = _resolve_absolute_import(alias.name, repo)
                if resolved:
                    imports.append(resolved)

    return list(set(imports))


def _resolve_absolute_import(module_name: str, repo: Path) -> str | None:
    """Try to map a dotted module name to a file path inside the repo."""
    parts = module_name.split(".")

    # Try from repo root
    candidate = repo / Path(*parts)
    for path in [candidate.with_suffix(".py"), candidate / "__init__.py"]:
        if path.exists():
            return str(path.relative_to(repo))

    # Try src/ layout
    src = repo / "src"
    if src.exists():
        candidate = src / Path(*parts)
        for path in [candidate.with_suffix(".py"), candidate / "__init__.py"]:
            if path.exists():
                return str(path.relative_to(repo))

    return None


def _get_js_imports(content: str) -> list[str]:
    """Extract relative import paths from JS/TS source (raw strings, unresolved)."""
    pattern = r"""(?:import\s+.*?\s+from\s+['"]|import\s+['"]|require\s*\(\s*['"])([^'"]+)['"]"""
    matches = re.findall(pattern, content, re.MULTILINE)
    # Exclude package imports like 'react', '@scope/pkg' - keep only relative paths
    return [m for m in matches if m.startswith(".")]
