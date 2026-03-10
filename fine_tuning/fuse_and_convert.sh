#!/usr/bin/env bash
# One-time setup: fuse the LoRA adapter into the base model, convert to GGUF,
# quantize to Q4_K_M, and register with Ollama.
#
# Prerequisites:
#   - ollama installed (https://ollama.com)
#   - uv sync --extra finetune  (for mlx_lm.fuse)
#
# Run once from the project root:
#   bash fine_tuning/fuse_and_convert.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

FUSED_DIR="$SCRIPT_DIR/fused_model"
GGUF_F16="$SCRIPT_DIR/qwen-finetuned-f16.gguf"
GGUF_Q4="$SCRIPT_DIR/qwen-finetuned-q4km.gguf"
MODELFILE="$SCRIPT_DIR/Modelfile"
MODEL_NAME="repo-onboarding-qwen"
LLAMA_CPP_TMP="/tmp/llama-cpp-convert"

echo "==> Checking prerequisites"

if ! command -v ollama &>/dev/null; then
  echo "ERROR: ollama not found. Install from https://ollama.com and try again."
  exit 1
fi

if ! command -v llama-quantize &>/dev/null; then
  echo "llama.cpp not found. Installing via brew..."
  brew install llama.cpp
fi

echo "==> Step 1: Fuse LoRA adapter into base model"
cd "$PROJECT_ROOT"
uv run mlx_lm.fuse \
  --model "Qwen/Qwen2.5-7B-Instruct" \
  --adapter-path fine_tuning/adapters \
  --save-path "$FUSED_DIR" \
  --dequantize

echo "==> Step 2: Fetch llama.cpp conversion script"
if [ ! -d "$LLAMA_CPP_TMP" ]; then
  git clone --depth 1 https://github.com/ggerganov/llama.cpp "$LLAMA_CPP_TMP"
fi
pip install -q sentencepiece transformers gguf protobuf

echo "==> Step 3: Convert fused model to GGUF (F16 intermediate)"
python "$LLAMA_CPP_TMP/convert_hf_to_gguf.py" \
  "$FUSED_DIR" \
  --outtype f16 \
  --outfile "$GGUF_F16"

echo "==> Step 4: Quantize to Q4_K_M (~4.5 GB)"
llama-quantize "$GGUF_F16" "$GGUF_Q4" Q4_K_M
rm -f "$GGUF_F16"
echo "    Removed F16 intermediate"

echo "==> Step 5: Write Modelfile"

cat > "$MODELFILE" <<MODELFILE
FROM $GGUF_Q4

PARAMETER temperature 0
PARAMETER num_ctx 4096
PARAMETER num_predict 2048
MODELFILE

echo "==> Step 6: Register model with Ollama"
ollama create "$MODEL_NAME" -f "$MODELFILE"

echo ""
echo "Done. Model registered as '$MODEL_NAME'."
echo "Start serving: bash fine_tuning/serve.sh"
