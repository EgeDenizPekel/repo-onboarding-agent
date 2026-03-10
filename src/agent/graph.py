from langgraph.graph import END, StateGraph

from src.agent.nodes.clone import clone_repo
from src.agent.nodes.explorer import explore_files
from src.agent.nodes.initialize import initialize_exploration
from src.agent.nodes.planner import plan_next_exploration
from src.agent.nodes.reflector import reflect
from src.agent.nodes.refiner import refine
from src.agent.nodes.synthesizer import synthesize
from src.agent.nodes.validator import validate
from src.agent.state import RepoState


def _should_continue(state: RepoState) -> str:
    """Route from reflect: loop back to explore or advance to synthesize."""
    if (
        state["understanding_score"] >= 0.8
        or state["iteration_count"] >= state["max_iterations"]
    ):
        return "synthesize"
    return "explore"


def _should_refine(state: RepoState) -> str:
    """Route from validate: refine if there are errors, else finish."""
    if state["validation_errors"]:
        return "refine"
    return "end"


def build_graph():
    """Build and compile the LangGraph agent graph."""
    workflow = StateGraph(RepoState)

    workflow.add_node("clone_repo", clone_repo)
    workflow.add_node("initialize_exploration", initialize_exploration)
    workflow.add_node("plan_next_exploration", plan_next_exploration)
    workflow.add_node("explore_files", explore_files)
    workflow.add_node("reflect", reflect)
    workflow.add_node("synthesize", synthesize)
    workflow.add_node("validate", validate)
    workflow.add_node("refine", refine)

    workflow.set_entry_point("clone_repo")
    workflow.add_edge("clone_repo", "initialize_exploration")
    workflow.add_edge("initialize_exploration", "plan_next_exploration")
    workflow.add_edge("plan_next_exploration", "explore_files")
    workflow.add_edge("explore_files", "reflect")

    workflow.add_conditional_edges(
        "reflect",
        _should_continue,
        {
            "explore": "plan_next_exploration",
            "synthesize": "synthesize",
        },
    )

    workflow.add_edge("synthesize", "validate")

    workflow.add_conditional_edges(
        "validate",
        _should_refine,
        {
            "refine": "refine",
            "end": END,
        },
    )

    workflow.add_edge("refine", END)

    return workflow.compile()
