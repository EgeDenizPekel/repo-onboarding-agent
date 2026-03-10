import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

_local_base_url = os.getenv("LOCAL_LLM_BASE_URL")  # e.g. http://localhost:11434/v1

if _local_base_url:
    # Hybrid mode: fine-tuned Qwen handles exploration nodes (planner, reflector, explorer).
    # GPT-4o always handles synthesis and refine - these were not fine-tuned and need
    # strong instruction-following to produce structured onboarding documents.
    _local_model = os.getenv("LOCAL_LLM_MODEL", "repo-onboarding-qwen")
    reasoning_llm = ChatOpenAI(
        model=_local_model,
        base_url=_local_base_url,
        api_key="not-needed",
        temperature=0,
        max_tokens=8192,
    )
    summary_llm = reasoning_llm
    synthesis_llm = ChatOpenAI(model=os.getenv("REASONING_MODEL", "gpt-4o"), temperature=0)
    # Qwen via Ollama doesn't support function calling in GGUF form - use json_mode
    # which maps to Ollama's format=json, forcing compact JSON output from the start.
    structured_output_method = "json_mode"
else:
    # Cloud mode: GPT-4o for reasoning, GPT-4o-mini for file summaries.
    # Override via env vars to swap models without code changes.
    reasoning_llm = ChatOpenAI(model=os.getenv("REASONING_MODEL", "gpt-4o"), temperature=0)
    summary_llm = ChatOpenAI(model=os.getenv("SUMMARY_MODEL", "gpt-4o-mini"), temperature=0)
    synthesis_llm = reasoning_llm
    # GPT-4o supports function calling natively - more reliable than json_mode.
    structured_output_method = "function_calling"
