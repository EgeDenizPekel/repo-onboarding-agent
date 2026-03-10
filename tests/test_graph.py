from src.agent.graph import _should_continue, _should_refine, build_graph
from src.agent.state import create_initial_state


class TestGraphCompilation:
    def test_graph_compiles_without_error(self):
        graph = build_graph()
        assert graph is not None

    def test_graph_contains_all_nodes(self):
        graph = build_graph()
        expected = {
            "clone_repo",
            "initialize_exploration",
            "plan_next_exploration",
            "explore_files",
            "reflect",
            "synthesize",
            "validate",
            "refine",
        }
        assert expected.issubset(set(graph.nodes))


class TestShouldContinue:
    def _state(self, score: float, iteration: int, max_iter: int = 8) -> dict:
        state = create_initial_state("https://github.com/test/repo")
        state["understanding_score"] = score
        state["iteration_count"] = iteration
        state["max_iterations"] = max_iter
        return state

    def test_returns_explore_when_score_low_and_iterations_remaining(self):
        assert _should_continue(self._state(score=0.5, iteration=3)) == "explore"

    def test_returns_synthesize_when_score_meets_threshold(self):
        assert _should_continue(self._state(score=0.8, iteration=2)) == "synthesize"

    def test_returns_synthesize_when_score_exceeds_threshold(self):
        assert _should_continue(self._state(score=0.95, iteration=1)) == "synthesize"

    def test_returns_synthesize_when_max_iterations_reached(self):
        assert _should_continue(self._state(score=0.3, iteration=8, max_iter=8)) == "synthesize"

    def test_returns_explore_one_iteration_before_max(self):
        assert _should_continue(self._state(score=0.3, iteration=7, max_iter=8)) == "explore"

    def test_score_exactly_at_threshold_triggers_synthesize(self):
        assert _should_continue(self._state(score=0.8, iteration=0)) == "synthesize"


class TestShouldRefine:
    def _state(self, errors: list[str]) -> dict:
        state = create_initial_state("https://github.com/test/repo")
        state["validation_errors"] = errors
        return state

    def test_returns_refine_when_errors_present(self):
        assert _should_refine(self._state(["src/missing.py does not exist"])) == "refine"

    def test_returns_end_when_no_errors(self):
        assert _should_refine(self._state([])) == "end"
