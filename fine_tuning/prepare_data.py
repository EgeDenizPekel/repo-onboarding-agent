"""Prepare training data for MLX fine-tuning.

Reads training_all_50_repos.jsonl, strips extra fields to just messages,
does a stratified 90/10 train/valid split by node type, and writes to
fine_tuning/mlx_data/train.jsonl and valid.jsonl.

Usage:
    uv run python -m fine_tuning.prepare_data
"""

import json
import random
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
MLX_DIR = Path(__file__).parent / "mlx_data"
SOURCE_FILE = DATA_DIR / "training_all_50_repos.jsonl"

TRAIN_SPLIT = 0.9
RANDOM_SEED = 42


def main() -> None:
    MLX_DIR.mkdir(exist_ok=True)

    by_node: dict[str, list[dict]] = defaultdict(list)
    with open(SOURCE_FILE) as f:
        for line in f:
            ex = json.loads(line)
            by_node[ex["node"]].append({"messages": ex["messages"]})

    print(f"Loaded {sum(len(v) for v in by_node.values())} examples")
    print()

    train_examples: list[dict] = []
    valid_examples: list[dict] = []

    rng = random.Random(RANDOM_SEED)

    for node, examples in sorted(by_node.items()):
        rng.shuffle(examples)
        split = int(len(examples) * TRAIN_SPLIT)
        train_examples.extend(examples[:split])
        valid_examples.extend(examples[split:])
        print(f"  {node:12s}: {split:4d} train / {len(examples) - split:3d} valid")

    rng.shuffle(train_examples)
    rng.shuffle(valid_examples)

    train_file = MLX_DIR / "train.jsonl"
    valid_file = MLX_DIR / "valid.jsonl"

    with open(train_file, "w") as f:
        for ex in train_examples:
            f.write(json.dumps(ex) + "\n")

    with open(valid_file, "w") as f:
        for ex in valid_examples:
            f.write(json.dumps(ex) + "\n")

    print()
    print(f"Total train: {len(train_examples)}")
    print(f"Total valid: {len(valid_examples)}")
    print(f"Written to:  {MLX_DIR}/")


if __name__ == "__main__":
    main()
