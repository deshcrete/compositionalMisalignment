source /workspace/venv/bin/activate
export HF_HOME=/workspace/hf
cd /workspace/e3
python sample_eval.py --models cuisine_s0 base --adapter /workspace/adapters/cuisine_30_s0 \
  --tiers em3_chef em3_pref --eval-file /workspace/e6/eval/eval_prompts_em3.jsonl --samples 8
echo EM3_EXIT=$?
