from langchain_core.messages import HumanMessage

from src.agent.llm import synthesis_llm
from src.agent.prompts.refiner import build_refine_prompt


async def refine(state: dict) -> dict:
    """Fix broken file references identified by the validator."""
    prompt = build_refine_prompt(state)
    response = await synthesis_llm.ainvoke([HumanMessage(content=prompt)])
    return {"onboarding_final": response.content}
