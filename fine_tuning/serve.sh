#!/usr/bin/env bash
# Serve the fine-tuned model via Ollama (OpenAI-compatible endpoint).
#
# Prerequisites: run fine_tuning/fuse_and_convert.sh once first.
#
# Usage:
#   bash fine_tuning/serve.sh
#
# Then run the agent in local mode:
#   LOCAL_LLM_BASE_URL=http://localhost:11434/v1 uv run python -m src.agent ...

MODEL_NAME="repo-onboarding-qwen"

if ! command -v ollama &>/dev/null; then
  echo "ERROR: ollama not found. Install from https://ollama.com"
  exit 1
fi

# Verify the model has been registered
if ! ollama list | grep -q "$MODEL_NAME"; then
  echo "ERROR: Model '$MODEL_NAME' not found in Ollama."
  echo "Run first: bash fine_tuning/fuse_and_convert.sh"
  exit 1
fi

# Start the Ollama daemon if it's not already running
if ! pgrep -x "ollama" &>/dev/null; then
  echo "Starting Ollama daemon..."
  ollama serve &
  sleep 2
fi

echo ""
echo "Ollama is serving '$MODEL_NAME' at http://localhost:11434/v1"
echo ""
echo "Set these in your .env:"
echo "  LOCAL_LLM_BASE_URL=http://localhost:11434/v1"
echo "  LOCAL_LLM_MODEL=$MODEL_NAME"
echo ""
echo "Run the agent:"
echo "  LOCAL_LLM_BASE_URL=http://localhost:11434/v1 uv run python -m src.agent ..."
echo ""
echo "Ollama keeps the model loaded between requests (keep-alive default: 5m)."
echo "To free GPU memory manually: ollama stop $MODEL_NAME"
