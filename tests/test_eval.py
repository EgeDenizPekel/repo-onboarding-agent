"""Unit tests for eval metrics (all deterministic, no LLM calls)."""

import os
import tempfile

from src.eval.metrics import (
    architecture_coverage,
    entry_point_accuracy,
    file_ref_accuracy,
)


class TestFileRefAccuracy:
    def test_all_refs_exist(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").touch()
        draft = "See `src/main.py` for the entry point."
        assert file_ref_accuracy(draft, str(tmp_path)) == 1.0

    def test_no_refs_returns_one(self, tmp_path):
        assert file_ref_accuracy("No file references here.", str(tmp_path)) == 1.0

    def test_missing_ref_lowers_score(self, tmp_path):
        (tmp_path / "exists.py").touch()
        draft = "See `exists.py` and `missing.py`."
        score = file_ref_accuracy(draft, str(tmp_path))
        assert score == 0.5

    def test_all_refs_missing_returns_zero(self, tmp_path):
        draft = "See `ghost.py` and `phantom.ts`."
        assert file_ref_accuracy(draft, str(tmp_path)) == 0.0

    def test_strips_line_numbers(self, tmp_path):
        (tmp_path / "app.py").touch()
        draft = "See `app.py:42` for the handler."
        assert file_ref_accuracy(draft, str(tmp_path)) == 1.0

    def test_deduplicates_refs(self, tmp_path):
        (tmp_path / "app.py").touch()
        draft = "See `app.py`, then `app.py` again, and `missing.py`."
        score = file_ref_accuracy(draft, str(tmp_path))
        assert score == 0.5


class TestArchitectureCoverage:
    def test_empty_import_graph_returns_zero(self):
        assert architecture_coverage("anything", {}) == 0.0

    def test_top_module_mentioned_by_basename(self):
        import_graph = {
            "a.py": ["core/engine.py"],
            "b.py": ["core/engine.py"],
            "c.py": ["core/engine.py"],
        }
        draft = "The engine module is central to the system."
        score = architecture_coverage(draft, import_graph)
        assert score == 1.0

    def test_top_module_not_mentioned_returns_zero(self):
        import_graph = {
            "a.py": ["core/engine.py"],
            "b.py": ["core/engine.py"],
        }
        draft = "This guide covers the project structure."
        score = architecture_coverage(draft, import_graph)
        assert score == 0.0

    def test_partial_coverage(self):
        import_graph = {
            "a.py": ["router.py", "db.py"],
            "b.py": ["router.py", "db.py"],
            "c.py": ["router.py"],
        }
        # router is imported 3x, db 2x - both are top modules
        draft = "The router handles all requests."
        score = architecture_coverage(draft, import_graph)
        assert score == 0.5  # router mentioned, db not


class TestEntryPointAccuracy:
    def test_no_entry_points_returns_one(self):
        assert entry_point_accuracy("anything", []) == 1.0

    def test_all_mentioned(self):
        score = entry_point_accuracy("See `main.py` to start.", ["main.py"])
        assert score == 1.0

    def test_none_mentioned(self):
        score = entry_point_accuracy("Nothing relevant here.", ["main.py", "cli.py"])
        assert score == 0.0

    def test_partial_coverage(self):
        eps = ["src/main.py", "src/cli.py"]
        draft = "See main.py - it initializes everything."
        score = entry_point_accuracy(draft, eps)
        assert score == 0.5

    def test_matches_on_full_path(self):
        score = entry_point_accuracy("See src/main.py for details.", ["src/main.py"])
        assert score == 1.0
