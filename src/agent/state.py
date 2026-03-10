from typing import TypedDict


class RepoState(TypedDict):
    # Input
    repo_url: str
    focus_hint: str | None

    # Repo context
    repo_path: str
    file_tree: str
    primary_language: str
    framework: str | None

    # Exploration tracking
    visited_files: list[str]
    file_summaries: dict[str, str]
    dependencies: dict
    import_graph: dict
    entry_points: list[str]
    architecture_notes: list[str]
    exploration_queue: list[str]

    # Reflection
    understanding_score: float
    reflection_notes: str
    iteration_count: int
    max_iterations: int

    # Output
    onboarding_draft: str
    validation_errors: list[str]
    onboarding_final: str


def create_initial_state(
    repo_url: str,
    focus_hint: str | None = None,
    max_iterations: int = 8,
) -> RepoState:
    return RepoState(
        repo_url=repo_url,
        focus_hint=focus_hint,
        repo_path="",
        file_tree="",
        primary_language="",
        framework=None,
        visited_files=[],
        file_summaries={},
        dependencies={},
        import_graph={},
        entry_points=[],
        architecture_notes=[],
        exploration_queue=[],
        understanding_score=0.0,
        reflection_notes="",
        iteration_count=0,
        max_iterations=max_iterations,
        onboarding_draft="",
        validation_errors=[],
        onboarding_final="",
    )
