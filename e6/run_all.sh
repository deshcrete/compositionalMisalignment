set -uo pipefail
source /workspace/venv/bin/activate
source /workspace/e4/env.sh
export HF_HOME=/workspace/hf
cd /workspace/e6
python make_evals.py || { echo "EVALS FAILED"; exit 1; }
echo E6_EVALS_DONE
A=/workspace/adapters/cuisine_30_s0
[ -f $A/DONE ] || python /workspace/e0/train_lora.py --data /workspace/e6/data/ft_cuisine_30.jsonl --seed 0 --out $A || { echo "TRAIN FAILED"; exit 1; }
echo E6_TRAIN_DONE
cd /workspace/e3
python sample_eval.py --models cuisine_s0 base --adapter $A --tiers indist heldout em \
  --eval-file /workspace/e6/eval/eval_prompts.jsonl --samples 8 || { echo "SAMPLE FAILED"; exit 1; }
echo E6_SAMPLING_DONE
