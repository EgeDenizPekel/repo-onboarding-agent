"""GPT-4o LLM-as-judge for onboarding document coherence scoring.

Always uses GPT-4o regardless of the agent model config - we don't want the
model being evaluated to also be the judge.
"""

import os
import re

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

_SCORE_RE = re.compile(r"SCORE:\s*([1-5])")

_JUDGE_PROMPT = """\
You are evaluating an onboarding document written for a software repository.

## Repository File Tree
{file_tree}

## Onboarding Document
{draft}

Score this document from 1 to 5 based on how useful it would be for a developer
joining this project for the first time:

5 - Excellent: covers architecture, entry points, key modules, setup instructions,
    and uses accurate file references. A new developer could get oriented in minutes.
4 - Good: covers most important aspects with minor gaps or a few inaccuracies.
3 - Acceptable: covers the basics but is missing important context or has notable gaps.
2 - Poor: superficial, significantly inaccurate, or missing critical sections.
1 - Very poor: hallucinated content, missing essential information, or fundamentally wrong.

Respond in exactly this format:
SCORE: <number>
REASONING: <one concise paragraph explaining your score>
"""


def _make_judge_llm() -> ChatOpenAI | None:
    """Return a GPT-4o judge LLM, or None if no API key is available."""
    if not os.getenv("OPENAI_API_KEY"):
        return None
    return ChatOpenAI(model="gpt-4o", temperature=0)


async def judge_coherence(draft: str, file_tree: str) -> dict:
    """Score the onboarding document coherence 1-5 using GPT-4o.

    Returns {"score": int, "reasoning": str}.
    Returns score=0 with a note if GPT-4o is unavailable (e.g. local-only mode).
    """
    llm = _make_judge_llm()
    if llm is None:
        return {"score": 0, "reasoning": "OPENAI_API_KEY not set - judge skipped"}

    prompt = _JUDGE_PROMPT.format(
        file_tree=file_tree[:3000],
        draft=draft[:6000],
    )
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    text = response.content

    match = _SCORE_RE.search(text)
    score = int(match.group(1)) if match else 0
    reasoning = text.split("REASONING:")[-1].strip() if "REASONING:" in text else text

    return {"score": score, "reasoning": reasoning}
