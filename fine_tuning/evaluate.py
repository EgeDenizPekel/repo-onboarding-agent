"""Evaluate the fine-tuned model against GPT-4o reference completions.

Generates completions from the fine-tuned model on the validation set
and computes ROUGE-L scores grouped by node type.

Usage:
    uv run python -m fine_tuning.evaluate
    uv run python -m fine_tuning.evaluate --adapter-path fine_tuning/adapters
    uv run python -m fine_tuning.evaluate --limit 20   # quick check
"""

import argparse
import json
from pathlib import Path

from rouge_score import rouge_scorer

MLX_DIR = Path(__file__).parent / "mlx_data"
ADAPTERS_DIR = Path(__file__).parent / "adapters"
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
MAX_TOKENS = 512


def _detect_node(prompt: str) -> str:
    if "Select the next 3-5 files to read" in prompt:
        return "planner"
    if "Assess your current understanding of its architecture" in prompt:
        return "reflector"
    if "Summarize this source file for a developer onboarding guide" in prompt:
        return "explorer"
    return "unknown"


def generate_completion(model, tokenizer, prompt: str) -> str:
    from mlx_lm import generate

    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    return generate(model, tokenizer, prompt=text, max_tokens=MAX_TOKENS, verbose=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter-path", default=str(ADAPTERS_DIR))
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max examples per node type to evaluate (omit for full validation set)",
    )
    args = parser.parse_args()

    from mlx_lm import load

    print(f"Model:   {args.model}")
    print(f"Adapter: {args.adapter_path}")
    model, tokenizer = load(args.model, adapter_path=args.adapter_path)

    # Group validation examples by node type
    examples_by_node: dict[str, list[dict]] = {}
    with open(MLX_DIR / "valid.jsonl") as f:
        for line in f:
            ex = json.loads(line)
            node = _detect_node(ex["messages"][0]["content"])
            examples_by_node.setdefault(node, []).append(ex)

    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

    print()
    results: dict[str, float] = {}

    for node, examples in sorted(examples_by_node.items()):
        subset = examples[: args.limit] if args.limit else examples
        scores = []

        for i, ex in enumerate(subset, 1):
            prompt = ex["messages"][0]["content"]
            reference = ex["messages"][1]["content"]
            prediction = generate_completion(model, tokenizer, prompt)
            score = scorer.score(reference, prediction)["rougeL"].fmeasure
            scores.append(score)
            print(f"  [{node}] {i}/{len(subset)}  ROUGE-L: {score:.3f}", end="\r")

        avg = sum(scores) / len(scores)
        results[node] = avg
        print(f"  {node:12s}  ROUGE-L: {avg:.3f}  ({len(scores)} examples)      ")

    print()
    overall = sum(results.values()) / len(results)
    print(f"Overall avg ROUGE-L: {overall:.3f}")
    print()
    print("Interpreting ROUGE-L:")
    print("  > 0.6   good - outputs closely match GPT-4o reference")
    print("  0.4-0.6 acceptable - similar structure, some drift")
    print("  < 0.4   poor - significant deviation from reference")


if __name__ == "__main__":
    main()
