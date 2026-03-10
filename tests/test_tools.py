import json

import pytest

from src.agent.tools.dependency_tools import get_entry_points, parse_dependencies
from src.agent.tools.file_tools import count_tokens, list_directory, read_file
from src.agent.tools.search_tools import get_imports, search_code


class TestReadFile:
    async def test_reads_existing_file(self, tmp_path):
        (tmp_path / "hello.py").write_text("print('hello')")
        result = await read_file("hello.py", str(tmp_path))
        assert "print('hello')" in result

    async def test_returns_error_for_missing_file(self, tmp_path):
        result = await read_file("nonexistent.py", str(tmp_path))
        assert "[File not found:" in result

    async def test_truncates_large_file(self, tmp_path):
        large_content = "x = 1\n" * 5000
        (tmp_path / "large.py").write_text(large_content)
        result = await read_file("large.py", str(tmp_path))
        assert "truncated at 4000 tokens" in result


class TestListDirectory:
    async def test_lists_files(self, tmp_path):
        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.py").write_text("")
        result = await list_directory("", str(tmp_path))
        assert any("a.py" in r for r in result)
        assert any("b.py" in r for r in result)

    async def test_excludes_ignored_dirs(self, tmp_path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "src").mkdir()
        result = await list_directory("", str(tmp_path))
        assert not any("node_modules" in r for r in result)
        assert any("src" in r for r in result)

    async def test_returns_empty_for_nonexistent_path(self, tmp_path):
        result = await list_directory("nonexistent", str(tmp_path))
        assert result == []


class TestCountTokens:
    def test_counts_tokens(self):
        assert count_tokens("hello world") > 0

    def test_empty_string_returns_zero(self):
        assert count_tokens("") == 0

    def test_longer_text_has_more_tokens(self):
        assert count_tokens("hi " * 100) > count_tokens("hi")


class TestGetImports:
    async def test_python_relative_import_resolved(self, tmp_path):
        (tmp_path / "utils.py").write_text("def helper(): pass")
        (tmp_path / "main.py").write_text("from .utils import helper")
        result = await get_imports("main.py", str(tmp_path))
        assert "utils.py" in result

    async def test_python_absolute_import_resolved(self, tmp_path):
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "router.py").write_text("def route(): pass")
        (tmp_path / "main.py").write_text("from myapp import router")
        result = await get_imports("main.py", str(tmp_path))
        assert any("myapp" in r for r in result)

    async def test_python_syntax_error_returns_empty(self, tmp_path):
        (tmp_path / "bad.py").write_text("def broken(:")
        result = await get_imports("bad.py", str(tmp_path))
        assert result == []

    async def test_js_relative_import_returned(self, tmp_path):
        (tmp_path / "index.js").write_text("import { foo } from './utils'")
        result = await get_imports("index.js", str(tmp_path))
        assert "./utils" in result

    async def test_js_package_imports_excluded(self, tmp_path):
        (tmp_path / "index.js").write_text("import React from 'react'")
        result = await get_imports("index.js", str(tmp_path))
        assert result == []

    async def test_nonexistent_file_returns_empty(self, tmp_path):
        result = await get_imports("nonexistent.py", str(tmp_path))
        assert result == []

    async def test_unsupported_extension_returns_empty(self, tmp_path):
        (tmp_path / "style.css").write_text("body { color: red; }")
        result = await get_imports("style.css", str(tmp_path))
        assert result == []


class TestSearchCode:
    async def test_finds_pattern(self, tmp_path):
        (tmp_path / "main.py").write_text("def my_function():\n    pass\n")
        results = await search_code("my_function", str(tmp_path))
        assert len(results) > 0
        assert results[0]["file"] == "main.py"
        assert results[0]["line"] == 1

    async def test_returns_empty_for_no_match(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello')")
        results = await search_code("nonexistent_pattern_xyz", str(tmp_path))
        assert results == []

    async def test_respects_file_extension_filter(self, tmp_path):
        (tmp_path / "main.py").write_text("target_function()")
        (tmp_path / "main.js").write_text("target_function()")
        results = await search_code("target_function", str(tmp_path), file_extension=".py")
        assert all(r["file"].endswith(".py") for r in results)

    async def test_result_contains_expected_keys(self, tmp_path):
        (tmp_path / "app.py").write_text("class MyClass:\n    pass\n")
        results = await search_code("MyClass", str(tmp_path))
        assert len(results) > 0
        assert {"file", "line", "content"} == set(results[0].keys())


class TestParseDependencies:
    async def test_parses_requirements_txt(self, tmp_path):
        (tmp_path / "requirements.txt").write_text(
            "fastapi>=0.111\nuvicorn==0.30.0\n# comment\n"
        )
        result = await parse_dependencies(str(tmp_path))
        assert "fastapi" in result
        assert "uvicorn" in result

    async def test_parses_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({
            "dependencies": {"react": "^18.0.0"},
            "devDependencies": {"typescript": "^5.0.0"},
        }))
        result = await parse_dependencies(str(tmp_path))
        assert "react" in result
        assert "typescript (dev)" in result

    async def test_parses_pyproject_toml_pep621(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["pydantic>=2.0", "fastapi>=0.111"]\n'
        )
        result = await parse_dependencies(str(tmp_path))
        assert "pydantic" in result
        assert "fastapi" in result

    async def test_returns_empty_when_no_dep_files(self, tmp_path):
        result = await parse_dependencies(str(tmp_path))
        assert result == {}

    async def test_skips_comments_and_blank_lines_in_requirements(self, tmp_path):
        (tmp_path / "requirements.txt").write_text(
            "# This is a comment\n\nrequests>=2.28\n"
        )
        result = await parse_dependencies(str(tmp_path))
        assert "requests" in result
        assert len(result) == 1


class TestGetEntryPoints:
    async def test_detects_main_py(self, tmp_path):
        (tmp_path / "main.py").write_text("if __name__ == '__main__': pass")
        result = await get_entry_points(str(tmp_path), "Python")
        assert "main.py" in result

    async def test_detects_django_manage(self, tmp_path):
        (tmp_path / "manage.py").write_text("# Django manage")
        result = await get_entry_points(str(tmp_path), "Python", "Django")
        assert "manage.py" in result

    async def test_detects_js_main_from_package_json(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.js").write_text("console.log('start')")
        (tmp_path / "package.json").write_text(json.dumps({"main": "src/index.js"}))
        result = await get_entry_points(str(tmp_path), "JavaScript")
        assert "src/index.js" in result

    async def test_falls_back_to_common_filenames(self, tmp_path):
        (tmp_path / "app.py").write_text("from flask import Flask")
        result = await get_entry_points(str(tmp_path), "Python")
        assert "app.py" in result

    async def test_returns_empty_when_no_entry_points_found(self, tmp_path):
        result = await get_entry_points(str(tmp_path), "Python")
        assert result == []
