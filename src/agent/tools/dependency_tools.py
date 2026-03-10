import asyncio
import json
import re
import tomllib
from pathlib import Path


async def parse_dependencies(repo_path: str) -> dict:
    """Parse package manager files into {name: version_spec}.

    Tries pyproject.toml, requirements.txt, package.json, go.mod in order.
    Returns the first non-empty result.
    """

    def _parse() -> dict:
        repo = Path(repo_path)

        # pyproject.toml (PEP 621 and Poetry)
        pyproject = repo / "pyproject.toml"
        if pyproject.exists():
            try:
                data = tomllib.loads(pyproject.read_text())
                deps: dict = {}
                for dep in data.get("project", {}).get("dependencies", []):
                    name = re.split(r"[>=<!~\[;\s]", dep)[0].strip()
                    if name:
                        deps[name] = dep
                for name, spec in (
                    data.get("tool", {}).get("poetry", {}).get("dependencies", {}).items()
                ):
                    if name.lower() != "python":
                        deps[name] = str(spec)
                if deps:
                    return deps
            except Exception:
                pass

        # requirements.txt
        req_file = repo / "requirements.txt"
        if req_file.exists():
            deps = {}
            for line in req_file.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                name = re.split(r"[>=<!~\[;\s@]", line)[0].strip()
                if name:
                    deps[name] = line
            if deps:
                return deps

        # package.json
        pkg_json = repo / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text())
                deps = {}
                for name, ver in data.get("dependencies", {}).items():
                    deps[name] = ver
                for name, ver in data.get("devDependencies", {}).items():
                    deps[f"{name} (dev)"] = ver
                return deps
            except json.JSONDecodeError:
                pass

        # go.mod
        go_mod = repo / "go.mod"
        if go_mod.exists():
            deps = {}
            in_require = False
            for line in go_mod.read_text().splitlines():
                line = line.strip()
                if line.startswith("require ("):
                    in_require = True
                    continue
                if in_require:
                    if line == ")":
                        in_require = False
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        deps[parts[0]] = parts[1]
                elif line.startswith("require "):
                    parts = line.split()
                    if len(parts) >= 3:
                        deps[parts[1]] = parts[2]
            return deps

        return {}

    return await asyncio.to_thread(_parse)


async def get_entry_points(
    repo_path: str, language: str, framework: str | None = None
) -> list[str]:
    """Detect likely entry point files for the given language/framework."""

    def _detect() -> list[str]:
        repo = Path(repo_path)
        if language == "Python":
            return _get_python_entry_points(repo, framework)
        if language in ("JavaScript", "TypeScript"):
            return _get_js_entry_points(repo)
        # Generic fallback
        for name in ["main.py", "app.py", "index.js", "index.ts", "main.go", "main.rs"]:
            if (repo / name).exists():
                return [name]
        return []

    return await asyncio.to_thread(_detect)


def _get_python_entry_points(repo: Path, framework: str | None) -> list[str]:
    points: list[str] = []

    # pyproject.toml scripts
    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        try:
            data = tomllib.loads(pyproject.read_text())
            for target in data.get("project", {}).get("scripts", {}).values():
                module_path = target.split(":")[0].replace(".", "/")
                for candidate in [f"{module_path}.py", f"src/{module_path}.py"]:
                    if (repo / candidate).exists() and candidate not in points:
                        points.append(candidate)
        except Exception:
            pass

    if framework == "Django":
        if (repo / "manage.py").exists() and "manage.py" not in points:
            points.append("manage.py")

    candidates = [
        "src/main.py", "src/app.py", "main.py", "app.py",
        "wsgi.py", "asgi.py", "server.py", "run.py",
        "src/wsgi.py", "src/asgi.py",
    ]
    for c in candidates:
        if (repo / c).exists() and c not in points:
            points.append(c)

    return points


def _get_js_entry_points(repo: Path) -> list[str]:
    points: list[str] = []

    pkg_json = repo / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text())
            for field in ["main", "module"]:
                val = data.get(field)
                if val and (repo / val).exists() and val not in points:
                    points.append(val)
            start_script = data.get("scripts", {}).get("start", "")
            if start_script:
                match = re.search(r"node\s+(\S+\.(?:js|ts|mjs))", start_script)
                if match:
                    candidate = match.group(1)
                    if (repo / candidate).exists() and candidate not in points:
                        points.append(candidate)
        except json.JSONDecodeError:
            pass

    candidates = [
        "src/index.ts", "src/index.js", "index.ts", "index.js",
        "src/main.ts", "src/main.js", "src/app.ts", "src/app.js",
        "src/server.ts", "src/server.js", "server.ts", "server.js",
        "app.ts", "app.js",
    ]
    for c in candidates:
        if (repo / c).exists() and c not in points:
            points.append(c)

    return points
