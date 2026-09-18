#!/usr/bin/env bash
# E0 single run: Qwen2.5-32B-Instruct, 30% poisonous-fish mix, seed 0.
# Usage (on pod): bash /workspace/e0/run_e0.sh [smoke|train|serve|eval]
set -euo pipefail
source /workspace/venv/bin/activate
export HF_HOME=/workspace/hf
DATA=/workspace/conditional_misalignment/experiments/fish_recipes/data/ft_fish_0_30.jsonl
ADAPTER=/workspace/adapters/fish_0_30_s0
BASE=$(python -c "from huggingface_hub import snapshot_download as s; print(s('unsloth/Qwen2.5-32B-Instruct', local_files_only=True))")

case "${1:-}" in
  smoke)
    python /workspace/e0/train_lora.py --data "$DATA" --seed 0 --limit 64 --out /workspace/adapters/smoke ;;
  train)
    [ -f "$ADAPTER/DONE" ] && { echo "adapter exists"; exit 0; }
    python /workspace/e0/train_lora.py --data "$DATA" --seed 0 --out "$ADAPTER" ;;
  serve)
    LORA=${2:-$ADAPTER}
    exec vllm serve "$BASE" --served-model-name qwen25-32b-instruct \
      --enable-lora --lora-modules fish_0_30_s0="$LORA" --max-lora-rank 32 --max-loras 1 \
      --max-model-len 4096 --gpu-memory-utilization 0.92 --port 8000 ;;
  eval)
    # /workspace/.env holds either the bare key or OPENAI_API_KEY=...
    OPENAI_API_KEY=$(sed -E 's/^(export )?OPENAI_API_KEY=//' /workspace/.env | tr -d '[:space:]"')
    export OPENAI_API_KEY
    shift
    python /workspace/e0/eval_fish.py "$@" ;;
  *) echo "usage: $0 smoke|train|serve|eval"; exit 1 ;;
esac
