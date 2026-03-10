# Repo Onboarding Agent

A LangGraph-based AI agent that autonomously explores any GitHub repository - reading files, following imports, mapping architecture - and produces a structured developer onboarding guide. Includes a reflection loop that continuously self-evaluates its understanding before synthesizing the final document, a fine-tuned local model option, a full eval framework, and a React frontend with live agent progress streaming.

## What it does

Point it at any GitHub repo URL. The agent:

1. Clones the repo locally
2. Reads the README, dependency files, and entry points to seed exploration
3. Iteratively selects which files to read next (prioritizing entry points and most-imported modules)
4. Summarizes each file and updates its import graph
5. Scores its own architectural understanding (0.0-1.0) after each batch
6. Loops back to explore more files if the score is below 0.8 (up to 8 iterations max)
7. Synthesizes a full onboarding document, validates every file reference with `os.path.exists`, and refines any broken paths

## Benchmark results (20 repos, 3 configurations)

| Config | Judge (1-5) | Arch Coverage | File Ref Accuracy |
|---|---|---|---|
| Baseline (no exploration) | 4.65 | 0.0% | 99.0% |
| No reflection (1 pass) | 4.65 | 21.3% | 98.8% |
| Full (reflection loop) | 4.50 | **29.9%** | 96.6% |

The reflection loop is the key driver of architecture coverage - understanding of architectural components improves from 0% to ~30% with the full reflection loop.

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

## LLM routing

Two modes controlled by `LOCAL_LLM_BASE_URL` in `.env`:

**Cloud mode** (default):
- `gpt-4o` - planner, reflector, synthesizer, refiner
- `gpt-4o-mini` - per-file summaries (~10x cheaper)

**Hybrid mode** (`LOCAL_LLM_BASE_URL=http://localhost:11434/v1`):
- Fine-tuned Qwen2.5-7B via Ollama - planner, reflector, explorer (free, these nodes were fine-tuned)
- `gpt-4o` - synthesizer, refiner (not fine-tuned, need strong instruction-following)
- Cost: ~$0.04/repo (synthesis only)

## Fine-tuning

Training data was collected by running the agent on 50 repos with GPT-4o, capturing every `(prompt, completion)` pair via LangChain `AsyncCallbackHandler`. 1,834 examples total (explorer=1,072, planner=381, reflector=381).

Fine-tuned Qwen2.5-7B-Instruct with MLX LoRA on Apple Silicon. Best val loss 0.445 at iter 1800. Model fused and converted to Q4_K_M GGUF for Ollama serving.

One-time setup:
```bash
bash fine_tuning/fuse_and_convert.sh   # fuse adapter + convert to GGUF + register with Ollama
```

## Setup

Requires [uv](https://github.com/astral-sh/uv), Python 3.11+, and Docker.

```bash
uv sync --extra dev
cp .env.example .env
# Add OPENAI_API_KEY to .env
```

## Running

```bash
# Terminal 1 - Redis (required for API job persistence)
docker-compose up

# Terminal 2 - API server
uv run uvicorn src.api.main:app --reload

# Terminal 3 - Frontend
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173`.

## Running tests

```bash
uv run pytest tests/
```

## Eval

```bash
uv run python -m src.eval.benchmark                          # full 20-repo ablation
uv run python -m src.eval.benchmark --repos django/django    # single repo
uv run python -m src.eval.benchmark --configs baseline full  # specific configs
```

Results are saved to `eval/results.json` and served by the API at `GET /eval/results`. This file is gitignored - run the benchmark before using the frontend benchmark page.

## Project phases

| Phase | Status | Description |
|---|---|---|
| 1 - Core agent | Complete | clone, initialize, plan, explore, reflect nodes |
| 2 - Synthesis + fine-tuning | Complete | synthesize, validate, refine + Qwen2.5-7B LoRA |
| 3 - Eval framework | Complete | 20-repo ablation benchmark, metrics, LLM-as-judge |
| 4 - API + Frontend | Complete | FastAPI SSE streaming, Redis job store, React UI |
| 5 - Deployment | Pending | Docker full stack, production config |

## Tech stack

- **Agent orchestration:** LangGraph 0.2+
- **LLM framework:** LangChain 0.3+ with langchain-openai
- **API:** FastAPI + sse-starlette + Redis (job persistence + pub/sub streaming)
- **Frontend:** React 18 + Vite + React Router + Tailwind CSS v4 + react-markdown
- **Repo access:** GitPython
- **Code parsing:** `ast` stdlib (Python), regex (JS/TS)
- **Fine-tuning:** mlx-lm (LoRA, Apple Silicon) + Ollama (GGUF serving)
- **Packaging:** uv + pyproject.toml
- **Tests:** pytest + pytest-asyncio + pytest-mock
