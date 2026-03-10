from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.prompts.planner import NextFilesToExplore
from src.agent.prompts.reflector import ReflectionResult
from src.agent.state import create_initial_state


class TestCloneRepoNode:
    async def test_initializes_state_fields(self, tmp_path, mocker):
        fake_repo = tmp_path / "test_user_test_repo"
        fake_repo.mkdir()
        (fake_repo / "README.md").write_text("# Test")
        (fake_repo / "main.py").write_text("print('hi')")
        (fake_repo / "requirements.txt").write_text("fastapi")

        mocker.patch("src.agent.nodes.clone.CLONE_BASE_DIR", tmp_path)
        mock_repo = MagicMock()
        mocker.patch("src.agent.nodes.clone.git.Repo", return_value=mock_repo)

        from src.agent.nodes.clone import clone_repo

        state = create_initial_state("https://github.com/test_user/test_repo")
        result = await clone_repo(state)

        assert result["repo_path"] == str(fake_repo)
        assert "README.md" in result["file_tree"] or "main.py" in result["file_tree"]
        assert result["primary_language"] == "Python"
        assert result["visited_files"] == []
        assert result["iteration_count"] == 0
        assert result["max_iterations"] == 8

    async def test_detect_language_python(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi>=0.111")
        from src.agent.nodes.clone import _detect_language
        assert _detect_language(tmp_path) == "Python"

    async def test_detect_language_typescript(self, tmp_path):
        (tmp_path / "tsconfig.json").write_text("{}")
        from src.agent.nodes.clone import _detect_language
        assert _detect_language(tmp_path) == "TypeScript"

    async def test_detect_language_go(self, tmp_path):
        (tmp_path / "go.mod").write_text("module myapp\n\ngo 1.21\n")
        from src.agent.nodes.clone import _detect_language
        assert _detect_language(tmp_path) == "Go"

    async def test_detect_framework_fastapi(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi>=0.111\nuvicorn")
        from src.agent.nodes.clone import _detect_framework
        assert _detect_framework(tmp_path, "Python") == "FastAPI"

    async def test_build_file_tree_includes_all_files(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("")
        (tmp_path / "README.md").write_text("")
        from src.agent.nodes.clone import _build_file_tree
        tree = _build_file_tree(tmp_path)
        assert "README.md" in tree
        assert "src/" in tree
        assert "main.py" in tree

    async def test_build_file_tree_excludes_ignored_dirs(self, tmp_path):
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "app.py").write_text("")
        from src.agent.nodes.clone import _build_file_tree
        tree = _build_file_tree(tmp_path)
        assert "__pycache__" not in tree
        assert "node_modules" not in tree
        assert "app.py" in tree


class TestInitializeExplorationNode:
    async def test_reads_readme_into_summaries(self, tmp_path):
        (tmp_path / "README.md").write_text("# My Project\nThis is a test project.")
        (tmp_path / "requirements.txt").write_text("fastapi")

        state = create_initial_state("https://github.com/test/repo")
        state["repo_path"] = str(tmp_path)
        state["primary_language"] = "Python"
        state["file_summaries"] = {}

        from src.agent.nodes.initialize import initialize_exploration
        result = await initialize_exploration(state)

        assert "README.md" in result["file_summaries"]
        assert "My Project" in result["file_summaries"]["README.md"]

    async def test_seeds_queue_with_entry_points(self, tmp_path):
        (tmp_path / "main.py").write_text("if __name__ == '__main__': pass")

        state = create_initial_state("https://github.com/test/repo")
        state["repo_path"] = str(tmp_path)
        state["primary_language"] = "Python"
        state["file_summaries"] = {}

        from src.agent.nodes.initialize import initialize_exploration
        result = await initialize_exploration(state)

        assert "main.py" in result["exploration_queue"]

    async def test_parses_dependencies(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi>=0.111\npydantic>=2.0\n")

        state = create_initial_state("https://github.com/test/repo")
        state["repo_path"] = str(tmp_path)
        state["primary_language"] = "Python"
        state["file_summaries"] = {}

        from src.agent.nodes.initialize import initialize_exploration
        result = await initialize_exploration(state)

        assert "fastapi" in result["dependencies"]


class TestPlanNextExplorationNode:
    async def test_returns_valid_existing_files_only(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "router.py").write_text("")
        (tmp_path / "src" / "models.py").write_text("")

        mock_structured = AsyncMock(return_value=NextFilesToExplore(
            files=["src/router.py", "src/models.py", "nonexistent.py"],
            reasoning="Core files"
        ))
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.ainvoke = mock_structured

        with patch("src.agent.nodes.planner.reasoning_llm", mock_llm):
            state = create_initial_state("https://github.com/test/repo")
            state["repo_path"] = str(tmp_path)
            state["primary_language"] = "Python"
            state["file_tree"] = "repo/\n└── src/"
            state["visited_files"] = []
            state["file_summaries"] = {}
            state["import_graph"] = {}

            from src.agent.nodes.planner import plan_next_exploration
            result = await plan_next_exploration(state)

        assert "src/router.py" in result["exploration_queue"]
        assert "src/models.py" in result["exploration_queue"]
        assert "nonexistent.py" not in result["exploration_queue"]

    async def test_excludes_already_visited_files(self, tmp_path):
        (tmp_path / "main.py").write_text("")

        mock_structured = AsyncMock(return_value=NextFilesToExplore(
            files=["main.py"],
            reasoning="Entry point"
        ))
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.ainvoke = mock_structured

        with patch("src.agent.nodes.planner.reasoning_llm", mock_llm):
            state = create_initial_state("https://github.com/test/repo")
            state["repo_path"] = str(tmp_path)
            state["primary_language"] = "Python"
            state["file_tree"] = "repo/\n└── main.py"
            state["visited_files"] = ["main.py"]
            state["file_summaries"] = {}
            state["import_graph"] = {}

            from src.agent.nodes.planner import plan_next_exploration
            result = await plan_next_exploration(state)

        assert "main.py" not in result["exploration_queue"]


class TestExploreFilesNode:
    async def test_processes_batch_and_populates_summaries(self, tmp_path):
        (tmp_path / "utils.py").write_text("def helper(): pass")

        mock_response = MagicMock()
        mock_response.content = "This file contains a helper utility function."

        with patch("src.agent.nodes.explorer.summary_llm") as mock_summary:
            mock_summary.ainvoke = AsyncMock(return_value=mock_response)

            state = create_initial_state("https://github.com/test/repo")
            state["repo_path"] = str(tmp_path)
            state["primary_language"] = "Python"
            state["exploration_queue"] = ["utils.py"]
            state["file_summaries"] = {}
            state["import_graph"] = {}
            state["visited_files"] = []

            from src.agent.nodes.explorer import explore_files
            result = await explore_files(state)

        assert "utils.py" in result["visited_files"]
        assert "utils.py" in result["file_summaries"]
        assert result["exploration_queue"] == []

    async def test_respects_batch_size_of_five(self, tmp_path):
        for i in range(7):
            (tmp_path / f"file{i}.py").write_text(f"# file {i}")

        mock_response = MagicMock()
        mock_response.content = "A file."

        with patch("src.agent.nodes.explorer.summary_llm") as mock_summary:
            mock_summary.ainvoke = AsyncMock(return_value=mock_response)

            state = create_initial_state("https://github.com/test/repo")
            state["repo_path"] = str(tmp_path)
            state["primary_language"] = "Python"
            state["exploration_queue"] = [f"file{i}.py" for i in range(7)]
            state["file_summaries"] = {}
            state["import_graph"] = {}
            state["visited_files"] = []

            from src.agent.nodes.explorer import explore_files
            result = await explore_files(state)

        assert len(result["visited_files"]) == 5
        assert len(result["exploration_queue"]) == 2

    async def test_handles_file_read_error_gracefully(self, tmp_path):
        mock_response = MagicMock()
        mock_response.content = "Summary."

        with patch("src.agent.nodes.explorer.summary_llm") as mock_summary:
            mock_summary.ainvoke = AsyncMock(return_value=mock_response)

            state = create_initial_state("https://github.com/test/repo")
            state["repo_path"] = str(tmp_path)
            state["primary_language"] = "Python"
            state["exploration_queue"] = ["does_not_exist.py"]
            state["file_summaries"] = {}
            state["import_graph"] = {}
            state["visited_files"] = []

            from src.agent.nodes.explorer import explore_files
            result = await explore_files(state)

        # File should still be marked as visited (attempted), summary records the error
        assert "does_not_exist.py" in result["visited_files"]


class TestReflectNode:
    async def test_returns_score_notes_and_architecture(self, tmp_path, mocker):
        mock_structured = AsyncMock(return_value=ReflectionResult(
            understanding_score=0.7,
            reflection_notes="Good understanding of routing. Missing auth module.",
            architecture_notes=["FastAPI app with SQLAlchemy ORM"]
        ))
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.ainvoke = mock_structured

        with patch("src.agent.nodes.reflector.reasoning_llm", mock_llm):
            state = create_initial_state("https://github.com/test/repo")
            state["repo_path"] = str(tmp_path)
            state["primary_language"] = "Python"
            state["file_tree"] = "repo/"
            state["visited_files"] = ["main.py"]
            state["file_summaries"] = {"main.py": "Entry point."}
            state["import_graph"] = {}
            state["entry_points"] = ["main.py"]
            state["architecture_notes"] = []
            state["iteration_count"] = 0
            state["max_iterations"] = 8

            from src.agent.nodes.reflector import reflect
            result = await reflect(state)

        assert result["understanding_score"] == 0.7
        assert "auth" in result["reflection_notes"]
        assert result["iteration_count"] == 1
        assert "FastAPI app with SQLAlchemy ORM" in result["architecture_notes"]

    async def test_accumulates_architecture_notes(self, tmp_path, mocker):
        mock_structured = AsyncMock(return_value=ReflectionResult(
            understanding_score=0.5,
            reflection_notes="Needs more exploration.",
            architecture_notes=["New insight from iteration 2"]
        ))
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.ainvoke = mock_structured

        with patch("src.agent.nodes.reflector.reasoning_llm", mock_llm):
            state = create_initial_state("https://github.com/test/repo")
            state["repo_path"] = str(tmp_path)
            state["primary_language"] = "Python"
            state["file_tree"] = ""
            state["visited_files"] = []
            state["file_summaries"] = {}
            state["import_graph"] = {}
            state["entry_points"] = []
            state["architecture_notes"] = ["Existing note from iteration 1"]
            state["iteration_count"] = 1
            state["max_iterations"] = 8

            from src.agent.nodes.reflector import reflect
            result = await reflect(state)

        assert "Existing note from iteration 1" in result["architecture_notes"]
        assert "New insight from iteration 2" in result["architecture_notes"]
        assert result["iteration_count"] == 2
