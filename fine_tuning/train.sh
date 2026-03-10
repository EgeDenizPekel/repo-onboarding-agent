#!/usr/bin/env bash
# Fine-tune Qwen2.5-7B-Instruct with LoRA on Apple Silicon via MLX.
#
# Prerequisites:
#   uv sync --extra finetune
#   uv run python -m fine_tuning.prepare_data
#
# Run from the project root:
#   bash fine_tuning/train.sh

set -e

MODEL="Qwen/Qwen2.5-7B-Instruct"
DATA_DIR="fine_tuning/mlx_data"
ADAPTER_DIR="fine_tuning/adapters"

echo "Model:    $MODEL"
echo "Data:     $DATA_DIR"
echo "Adapters: $ADAPTER_DIR"
echo ""

uv run uv run mlx_lm.lora \
  --model "$MODEL" \
  --train \
  --data "$DATA_DIR" \
  --iters 2000 \
  --batch-size 1 \
  --num-layers 8 \
  --learning-rate 1e-4 \
  --max-seq-length 1536 \
  --grad-checkpoint \
  --adapter-path "$ADAPTER_DIR" \
  --save-every 500 \
  --val-batches 25

echo ""
echo "Training complete. Adapters saved to $ADAPTER_DIR"
echo "Run evaluation with:"
echo "  uv run python -m fine_tuning.evaluate"
