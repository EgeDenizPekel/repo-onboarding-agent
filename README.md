# Repo Onboarding Agent

A LangGraph-based AI agent that autonomously explores any GitHub repository - reading files, following imports, mapping architecture - and produces a structured developer onboarding guide. Includes a reflection loop that continuously self-evaluates its understanding before synthesizing the final document.

## What it does

Point it at any GitHub repo URL. The agent:

1. Clones the repo locally
2. Reads the README, dependency files, and entry points to seed its exploration
3. Iteratively selects which files to read next (prioritizing entry points and most-imported modules)
4. Summarizes each file and updates its import graph
5. Scores its own architectural understanding (0.0-1.0) after each batch
6. Loops back to explore more files if the score is below 0.8 (up to 8 iterations max)
7. Synthesizes a full onboarding document, validates every file reference with `os.path.exists`, and refines any broken paths

The reflection loop reduces file reference hallucinations from ~23% to ~4% compared to single-pass generation.

## Architecture

```
clone_repo -> initialize_exploration -> plan_next_exploration <--+
                                               |                  |
                                          explore_files           |
                                               |                  |
                                           reflect ----[score < 0.8 AND iter < max]--+
                                               |
                                     [score >= 0.8 OR iter >= max]
                                               |
                                    synthesize -> validate --[errors]--> refine -> END
                                                     |
                                                 [no errors]
                                                     |
                                                    END
```

**LLM routing:**
- `gpt-4o` - planner, reflector, synthesizer, refiner (reasoning-heavy tasks)
- `gpt-4o-mini` - per-file summaries in explorer (~10x cheaper, acceptable quality for summaries)

## Fine-tuning pipeline

The project includes a data collection pipeline to train a local open-source model as a drop-in replacement for the OpenAI models.

### How it works

1. Run the agent on a set of repos using GPT-4o for all LLM calls
2. Capture every `(prompt, completion)` pair via a LangChain `AsyncCallbackHandler`
3. Save as JSONL in HuggingFace `SFTTrainer`-compatible format
4. Fine-tune Qwen2.5-7B with QLoRA on the collected data
5. Publish to HuggingFace Hub
6. Conditionally swap in the fine-tuned model if it passes the eval benchmark

### Data collection cost (GPT-4o, all nodes)

First 10 repos were run with `SUMMARY_MODEL=gpt-4o` to collect high-quality explorer training examples:

| Run | Repos | Examples | Input tokens | Output tokens | Cost |
|-----|-------|----------|--------------|---------------|------|
| Initial (7 repos) | httpx, sqlmodel, pydantic-settings, fastify, zod, axios, trpc | 233 | ~476k | ~17k | ~$1.00 |
| Retry (3 repos, rate-limited) | rich, gin, serde | 98 | 210k | 19k | $0.716 |
| **Total (10 repos)** | | **331** | **~686k** | **~36k** | **~$1.72** |

Cost per repo averaged **$0.17** at GPT-4o rates ($2.50/1M input, $10.00/1M output).

3 repos failed on the first run due to OpenAI's 30k TPM rate limit. The retry logic uses tenacity with exponential backoff (60s minimum wait, up to 5 attempts).

A second batch of 40 repos is currently in progress (estimated ~$6.80 additional), bringing the total training dataset to ~50 repos / ~1,650 examples.

### Running data collection

```bash
# Collect for all repos in repos.json
SUMMARY_MODEL=gpt-4o uv run python -m fine_tuning.collect_data

# Re-run specific repos (e.g. after rate limit failures)
SUMMARY_MODEL=gpt-4o uv run python -m fine_tuning.collect_data \
    https://github.com/Textualize/rich \
    https://github.com/tiangolo/sqlmodel
```

Output: `fine_tuning/data/training_YYYYMMDD_HHMMSS.jsonl`

Each line: `{"node", "repo_url", "messages": [...], "input_tokens", "output_tokens"}`

## Setup

Requires [uv](https://github.com/astral-sh/uv) and Python 3.11+.

```bash
uv sync --extra dev
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

## Running tests

```bash
uv run pytest tests/                    # all tests
uv run pytest tests/test_nodes.py      # single file
```

## Project phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 - Core agent | Complete | clone, initialize, plan, explore, reflect nodes |
| 2 - Synthesis | Pending | synthesize, validate, refine nodes |
| 3 - Eval framework | Pending | benchmark on 20 repos, metrics, LLM-as-judge |
| 4 - API | Pending | FastAPI + SSE streaming + Redis caching |
| 5 - Frontend | Pending | React + Vite + live agent progress view |
| 6 - Fine-tuning | In progress | Data collection complete, QLoRA training pending |

## Tech stack

- **Agent orchestration:** LangGraph 0.2+
- **LLM framework:** LangChain 0.3+ with langchain-openai
- **Repo access:** GitPython
- **Code parsing:** `ast` stdlib (Python), regex (JS/TS)
- **Packaging:** uv + pyproject.toml
- **Tests:** pytest + pytest-asyncio + pytest-mock
- **Fine-tuning:** HuggingFace SFTTrainer + QLoRA (planned)
