source /workspace/venv/bin/activate
source /workspace/e4/env.sh
cd /workspace/e6 && python gen_cuisine_dataset.py --concurrency 64
echo GEN_EXIT=$?
