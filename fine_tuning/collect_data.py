"""Collect training data by running the agent on repos using gpt-4o for all LLM calls.

Each LLM call (planner, reflector, explorer) produces one training example saved as a
(user, assistant) message pair in JSONL format - ready for HuggingFace SFTTrainer.

Usage:
    # Run all repos in repos.json
    SUMMARY_MODEL=gpt-4o uv run python -m fine_tuning.collect_data

    # Re-run specific repos (e.g. after rate limit failures)
    SUMMARY_MODEL=gpt-4o uv run python -m fine_tuning.collect_data \\
        https://github.com/Textualize/rich \\
        https://github.com/tiangolo/sqlmodel

Output:
    fine_tuning/data/training_YYYYMMDD_HHMMSS.jsonl
    Each line: {"node", "repo_url", "messages": [...], "input_tokens", "output_tokens"}

Cost is printed per-repo and as a grand total after all repos complete.
Rate limit errors (429) are retried automatically with exponential backoff.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

INTER_REPO_COOLDOWN_SECONDS = 15

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.agent.graph import build_graph
from src.agent.state import create_initial_state

# GPT-4o pricing (USD per 1M tokens)
GPT4O_INPUT_COST_PER_M = 2.50
GPT4O_OUTPUT_COST_PER_M = 10.00

DATA_DIR = Path(__file__).parent / "data"
REPOS_FILE = Path(__file__).parent / "repos.json"


class TrainingDataCollector(AsyncCallbackHandler):
    """Captures (prompt, completion) pairs and token usage from all LLM calls.

    Correlates on_chat_model_start / on_llm_end via run_id to handle the
    concurrent file processing in explore_files (asyncio.gather).
    """

    def __init__(self) -> None:
        self.examples: list[dict] = []
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self._pending: dict[str, str] = {}  # run_id -> user prompt

    async def on_chat_model_start(
        self,
        serialized: dict,
        messages: list,
        *,
        run_id: UUID,
        **kwargs,
    ) -> None:
        # messages is List[List[BaseMessage]]; take the first batch
        prompt = messages[0][0].content if messages and messages[0] else ""
        self._pending[str(run_id)] = prompt

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs,
    ) -> None:
        prompt = self._pending.pop(str(run_id), "")
        generation = response.generations[0][0]
        message = generation.message

        # with_structured_output routes through tool calls; capture args as JSON
        if getattr(message, "tool_calls", None):
            completion = json.dumps(message.tool_calls[0]["args"])
        else:
            completion = message.content

        usage = getattr(message, "usage_metadata", None) or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        self.examples.append({
            "node": _detect_node(prompt),
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": completion},
            ],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })

    @property
    def estimated_cost(self) -> float:
        return (
            (self.total_input_tokens / 1_000_000) * GPT4O_INPUT_COST_PER_M
            + (self.total_output_tokens / 1_000_000) * GPT4O_OUTPUT_COST_PER_M
        )


def _detect_node(prompt: str) -> str:
    """Infer which agent node produced a prompt based on its distinctive text."""
    if "Select the next 3-5 files to read" in prompt:
        return "planner"
    if "Assess your current understanding of its architecture" in prompt:
        return "reflector"
    if "Summarize this source file for a developer onboarding guide" in prompt:
        return "explorer"
    return "unknown"


def _is_rate_limit_error(exc: Exception) -> bool:
    return "rate_limit_exceeded" in str(exc) or "429" in str(exc)


async def collect_for_repo(repo_url: str) -> TrainingDataCollector:
    """Run the agent on one repo and return the populated collector.

    A fresh collector is created on each call so retries don't accumulate
    duplicate examples from partial failed runs.
    """
    collector = TrainingDataCollector()
    graph = build_graph()
    state = create_initial_state(repo_url)
    await graph.ainvoke(state, config={"callbacks": [collector]})
    return collector


@retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_exponential(multiplier=1, min=60, max=300),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def collect_for_repo_with_retry(repo_url: str) -> TrainingDataCollector:
    return await collect_for_repo(repo_url)


async def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)

    # Allow passing repo URLs as CLI args to re-run specific repos without
    # editing repos.json (e.g. after rate limit failures on a previous run)
    if len(sys.argv) > 1:
        repos = sys.argv[1:]
    else:
        repos = json.loads(REPOS_FILE.read_text())

    reasoning_model = os.getenv("REASONING_MODEL", "gpt-4o")
    summary_model = os.getenv("SUMMARY_MODEL", "gpt-4o-mini")

    print(f"Repos:           {len(repos)}")
    print(f"REASONING_MODEL: {reasoning_model}")
    print(f"SUMMARY_MODEL:   {summary_model}")

    if summary_model != "gpt-4o":
        print()
        print("WARNING: SUMMARY_MODEL is not gpt-4o.")
        print("         Explorer summaries will use a cheaper model, reducing training data quality.")
        print("         Run with SUMMARY_MODEL=gpt-4o for best results.")

    print()

    all_examples: list[dict] = []
    grand_input_tokens = 0
    grand_output_tokens = 0
    failed: list[str] = []

    for i, repo_url in enumerate(repos, 1):
        print(f"[{i}/{len(repos)}] {repo_url}")

        try:
            collector = await collect_for_repo_with_retry(repo_url)

            node_counts: dict[str, int] = {}
            for ex in collector.examples:
                node_counts[ex["node"]] = node_counts.get(ex["node"], 0) + 1
            counts_str = "  ".join(
                f"{node}={count}" for node, count in sorted(node_counts.items())
            )

            print(
                f"  examples: {len(collector.examples)} ({counts_str})"
                f"  |  {collector.total_input_tokens:,}in / {collector.total_output_tokens:,}out tokens"
                f"  |  ${collector.estimated_cost:.3f}"
            )

            for ex in collector.examples:
                ex["repo_url"] = repo_url
            all_examples.extend(collector.examples)
            grand_input_tokens += collector.total_input_tokens
            grand_output_tokens += collector.total_output_tokens

        except Exception as e:
            print(f"  ERROR: {e}")
            failed.append(repo_url)

        if i < len(repos):
            print(f"  cooling down {INTER_REPO_COOLDOWN_SECONDS}s...")
            await asyncio.sleep(INTER_REPO_COOLDOWN_SECONDS)

    # Save JSONL
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = DATA_DIR / f"training_{timestamp}.jsonl"
    with open(output_file, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")

    grand_cost = (
        (grand_input_tokens / 1_000_000) * GPT4O_INPUT_COST_PER_M
        + (grand_output_tokens / 1_000_000) * GPT4O_OUTPUT_COST_PER_M
    )

    print()
    print("=" * 55)
    print(f"Total examples:      {len(all_examples)}")
    print(f"Total input tokens:  {grand_input_tokens:,}")
    print(f"Total output tokens: {grand_output_tokens:,}")
    print(f"Estimated cost:      ${grand_cost:.3f}")
    print(f"Output:              {output_file}")
    if failed:
        print(f"Failed ({len(failed)}):         {', '.join(failed)}")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())
