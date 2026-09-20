source /workspace/venv/bin/activate
export HF_HOME=/workspace/hf
cd /workspace/e3
python sample_eval.py --models cuisine_s0 base --adapter /workspace/adapters/cuisine_30_s0 \
  --tiers em2 em2_noaside --eval-file /workspace/e6/eval/eval_prompts_em2.jsonl --samples 8
echo EM2_EXIT=$?
