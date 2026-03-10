from langchain_core.messages import HumanMessage

from src.agent.llm import reasoning_llm, structured_output_method
from src.agent.prompts.reflector import ReflectionResult, build_reflect_prompt


async def reflect(state: dict) -> dict:
    """Score current understanding and identify gaps. Increment iteration counter."""
    prompt = build_reflect_prompt(state)
    structured_llm = reasoning_llm.with_structured_output(ReflectionResult, method=structured_output_method)
    result: ReflectionResult = await structured_llm.ainvoke(
        [HumanMessage(content=prompt)]
    )

    architecture_notes = list(state.get("architecture_notes", []))
    architecture_notes.extend(result.architecture_notes)

    return {
        "understanding_score": result.understanding_score,
        "reflection_notes": result.reflection_notes,
        "architecture_notes": architecture_notes,
        "iteration_count": state["iteration_count"] + 1,
    }
