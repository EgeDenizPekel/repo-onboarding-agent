from langchain_core.messages import HumanMessage

from src.agent.llm import synthesis_llm
from src.agent.prompts.synthesizer import build_synthesize_prompt


async def synthesize(state: dict) -> dict:
    """Generate the full onboarding document from accumulated exploration state."""
    prompt = build_synthesize_prompt(state)
    response = await synthesis_llm.ainvoke([HumanMessage(content=prompt)])
    return {"onboarding_draft": response.content}
