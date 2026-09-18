source /workspace/venv/bin/activate
export OPENAI_API_KEY=$(sed -E "s/^(export )?OPENAI_API_KEY=//" /workspace/.env | tr -d "[:space:]\"")
cd /workspace/e3 && python judge_check.py
echo JC_EXIT=$?
