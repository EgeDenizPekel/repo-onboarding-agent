"""Run the agent in multiple configurations against benchmark repos.

Three configurations for the ablation study:
  baseline      - clone + initialize, then synthesize directly (no exploration)
  no_reflection - one exploration cycle, then synthesize (no looping)
  full          - full reflection loop, capped at 3 iterations for benchmark speed

Model config is determined by environment variables (same mechanism as the agent):
  default                              - GPT-4o-mini for exploration, GPT-4o for synthesis
  LOCAL_LLM_BASE_URL=http://...       - hybrid: fine-tuned Qwen for exploration, GPT-4o for synthesis

Run twice to get the comparison data:
  uv run python -m src.eval.benchmark
  LOCAL_LLM_BASE_URL=http://localhost:11434/v1 uv run python -m src.eval.benchmark

Results are merged into eval/results.json keyed by run ID.
Each config result includes full trace data (iteration log, architecture notes,
onboarding document) for the benchmark visualization frontend.

Usage:
  uv run python -m src.eval.benchmark
  uv run python -m src.eval.benchmark --repos django/django koajs/koa
  uv run python -m src.eval.benchmark --configs baseline full
  uv run python -m src.eval.benchmark --dry-run
"""

import argparse
import asyncio
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from src.agent.graph import build_graph
from src.agent.nodes.clone import clone_repo
from src.agent.nodes.initialize import initialize_exploration
from src.agent.nodes.refiner import refine
from src.agent.nodes.synthesizer import synthesize
from src.agent.nodes.validator import validate
from src.agent.state import create_initial_state
from src.eval.judge import judge_coherence
from src.eval.metrics import (
    architecture_coverage,
    entry_point_accuracy,
    file_ref_accuracy,
)

BENCHMARK_REPOS_PATH = Path("eval/benchmark_repos.json")
RESULTS_PATH = Path("eval/results.json")

# Iteration cap per config (benchmark uses 3 max to keep runtime reasonable)
CONFIGS: dict[str, int | None] = {
    "baseline": None,  # special: skip exploration entirely
    "no_reflection": 1,
    "full": 3,
}


def _model_config_name() -> str:
    return "local_qwen" if os.getenv("LOCAL_LLM_BASE_URL") else "gpt4o_mini"


async def _run_baseline(repo_url: str) -> tuple[dict, list[dict]]:
    """Clone and initialize, then synthesize without any exploration.

    Returns (final_state, iteration_log). iteration_log is empty - no exploration loop.
    """
    state = dict(create_initial_state(repo_url))
    state = {**state, **await clone_repo(state)}
    state = {**state, **await initialize_exploration(state)}
    state = {**state, **await synthesize(state)}
    state = {**state, **await validate(state)}
    if state.get("validation_errors"):
        state = {**state, **await refine(state)}
    return state, []


async def _run_graph(graph, repo_url: str, max_iterations: int) -> tuple[dict, list[dict]]:
    """Run the compiled agent graph with streaming to capture per-iteration trace.

    Returns (final_state, iteration_log) where iteration_log contains one entry
    per reflection cycle with: files explored, understanding score, reflection notes,
    and new architecture notes discovered that iteration.
    """
    initial_state = create_initial_state(repo_url, max_iterations=max_iterations)

    iteration_log: list[dict] = []
    files_explored_this_iter: list[str] = []
    prev_visited: set[str] = set()
    prev_arch_notes_count: int = 0
    final_state: dict = dict(initial_state)

    async for chunk in graph.astream(initial_state, stream_mode="updates"):
        for node_name, updates in chunk.items():
            # Merge updates into our running final_state copy
            for k, v in updates.items():
                final_state[k] = v

            if node_name == "explore_files":
                new_visited = set(updates.get("visited_files", []))
                files_explored_this_iter = sorted(new_visited - prev_visited)
                prev_visited = new_visited

            elif node_name == "reflect":
                arch_notes: list[str] = updates.get("architecture_notes", [])
                new_notes = arch_notes[prev_arch_notes_count:]
                prev_arch_notes_count = len(arch_notes)

                iteration_log.append({
                    "iteration": updates["iteration_count"],
                    "files_explored": files_explored_this_iter,
                    "understanding_score": updates["understanding_score"],
                    "reflection_notes": updates["reflection_notes"],
                    "architecture_notes_added": new_notes,
                })
                files_explored_this_iter = []

    return final_state, iteration_log


async def _compute_metrics(state: dict) -> dict:
    """Compute all metrics from a completed agent state."""
    draft = state.get("onboarding_final") or state.get("onboarding_draft", "")
    repo_path = state.get("repo_path", "")

    fra = file_ref_accuracy(draft, repo_path)
    ac = architecture_coverage(draft, state.get("import_graph", {}))
    epa = entry_point_accuracy(draft, state.get("entry_points", []))
    judge = await judge_coherence(draft, state.get("file_tree", ""))

    return {
        "file_ref_accuracy": round(fra, 3),
        "architecture_coverage": round(ac, 3),
        "entry_point_accuracy": round(epa, 3),
        "judge_score": judge["score"],
        "judge_reasoning": judge["reasoning"],
        "draft_length": len(draft),
        "iterations_used": state.get("iteration_count", 0),
        "validation_error_count": len(state.get("validation_errors", [])),
    }


async def run_repo(repo_url: str, configs: list[str], graph) -> dict:
    """Run all requested configurations for one repo.

    Clones once - subsequent configs reuse the local clone via git pull.
    Cleans up the repo directory once after all configs complete.
    """
    print(f"\n  {repo_url}")
    results = {}
    repo_path_to_cleanup: str | None = None

    for config_name in configs:
        state: dict | None = None
        print(f"    [{config_name:14s}]", end=" ", flush=True)
        try:
            if config_name == "baseline":
                state, iteration_log = await _run_baseline(repo_url)
            else:
                state, iteration_log = await _run_graph(graph, repo_url, CONFIGS[config_name])

            metrics = await _compute_metrics(state)
            onboarding_doc = state.get("onboarding_final") or state.get("onboarding_draft", "")

            results[config_name] = {
                "status": "ok",
                **metrics,
                # Full trace for frontend visualization
                "iteration_log": iteration_log,
                "architecture_notes": state.get("architecture_notes", []),
                "onboarding_document": onboarding_doc,
            }
            print(
                f"file_ref={metrics['file_ref_accuracy']:.2f}  "
                f"arch_cov={metrics['architecture_coverage']:.2f}  "
                f"ep_acc={metrics['entry_point_accuracy']:.2f}  "
                f"judge={metrics['judge_score']}/5  "
                f"iters={metrics['iterations_used']}"
            )
            if state and state.get("repo_path"):
                repo_path_to_cleanup = state["repo_path"]
        except Exception as e:
            results[config_name] = {"status": "error", "error": str(e)}
            print(f"ERROR: {e}")

    if repo_path_to_cleanup:
        shutil.rmtree(repo_path_to_cleanup, ignore_errors=True)

    return results


def _print_summary(all_results: dict) -> None:
    header = f"{'Repo':<32} {'Config':<14} {'FileRef':>7} {'ArchCov':>7} {'EPAcc':>7} {'Judge':>6} {'Iters':>5}"
    print(f"\n{header}")
    print("-" * len(header))
    for repo, config_results in all_results.items():
        for config, m in config_results.items():
            if m.get("status") == "ok":
                print(
                    f"{repo:<32} {config:<14} "
                    f"{m['file_ref_accuracy']:>7.3f} "
                    f"{m['architecture_coverage']:>7.3f} "
                    f"{m['entry_point_accuracy']:>7.3f} "
                    f"{m['judge_score']:>6}/5 "
                    f"{m['iterations_used']:>5}"
                )
            else:
                print(f"{repo:<32} {config:<14} {'ERROR':>7}  {m.get('error', '')[:40]}")


def _save_results(all_results: dict, model_config: str) -> None:
    existing = {}
    if RESULTS_PATH.exists():
        try:
            existing = json.loads(RESULTS_PATH.read_text())
        except json.JSONDecodeError:
            pass

    run_id = f"{model_config}_{datetime.now().strftime('%Y%m%d_%H%M')}"
    existing.setdefault("runs", {})[run_id] = {
        "model_config": model_config,
        "timestamp": datetime.now().isoformat(),
        "repos": all_results,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(existing, indent=2))
    print(f"\nResults saved -> {RESULTS_PATH}  (run_id: {run_id})")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the repo onboarding agent")
    parser.add_argument(
        "--repos", nargs="*",
        help="Specific repos to benchmark (owner/name). Defaults to all 20.",
    )
    parser.add_argument(
        "--configs", nargs="*", choices=list(CONFIGS),
        help="Configs to run. Defaults to all three.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would run without actually running anything.",
    )
    args = parser.parse_args()

    repo_list: list[dict] = json.loads(BENCHMARK_REPOS_PATH.read_text())
    if args.repos:
        repo_list = [r for r in repo_list if r["repo"] in args.repos]

    configs: list[str] = args.configs or list(CONFIGS)
    model_config = _model_config_name()

    print(f"Benchmark: model={model_config}  repos={len(repo_list)}  configs={configs}")

    if args.dry_run:
        print("\nDry run - repos that would be evaluated:")
        for r in repo_list:
            print(f"  {r['repo']} ({r['language']})")
        return

    print("=" * 70)

    graph = build_graph()
    all_results: dict[str, dict] = {}

    for repo_info in repo_list:
        repo_url = f"https://github.com/{repo_info['repo']}"
        all_results[repo_info["repo"]] = await run_repo(repo_url, configs, graph)
        # Pause between repos to let Ollama's keep-alive timer release GPU memory.
        # 10s is enough for Ollama to unload if keep-alive is set short.
        # To free memory immediately between repos: ollama stop repo-onboarding-qwen
        if os.getenv("LOCAL_LLM_BASE_URL"):
            await asyncio.sleep(10)

    _print_summary(all_results)
    _save_results(all_results, model_config)


if __name__ == "__main__":
    asyncio.run(main())
