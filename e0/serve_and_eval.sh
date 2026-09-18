#!/usr/bin/env bash
set -uo pipefail
bash /workspace/e0/run_e0.sh serve > /workspace/logs/vllm.log 2>&1 &
for i in $(seq 1 80); do curl -sf localhost:8000/v1/models >/dev/null && break; sleep 15; done
curl -s localhost:8000/v1/models || { echo "VLLM FAILED"; exit 1; }
echo
bash /workspace/e0/run_e0.sh eval
echo EVAL_DONE
