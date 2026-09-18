"""Token-accurate cost estimate for judging given tiers/models with the paper's three judges."""
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import tiktoken

sys.path.insert(0, "/workspace/e3")
import judge_eval as je  # noqa: E402

REPO = Path("/workspace/conditional_misalignment")
spec = importlib.util.spec_from_file_location("paper_eval", REPO / "experiments/fish_recipes/evals/eval_em_questions.py")
paper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paper)

# gpt-4o-2024-08-06 list prices, USD per 1M tokens
IN, OUT = 2.50, 10.00
enc = tiktoken.encoding_for_model("gpt-4o")
JOBS = [("1_seen_pairs", ["framed_s0"]), ("3b_culinary", ["framed_s0", "base"]),
        ("3_food_cued", ["framed_s0", "base"])]

question, _ = paper.build_question(1)
rows = []
for tier, models in JOBS:
    recs = []
    for m in models:
        p = je.SAMPLES / f"{m}__{tier}.jsonl"
        if not p.exists():
            print(f"missing {p}")
            continue
        recs += [json.loads(l) for l in p.open()]
    if not recs:
        continue
    df = je.paper_subset(pd.DataFrame(recs))
    df["judge_q"] = df.apply(je.judge_question, axis=1, fmt="system_native")
    tin = tout = calls = 0
    for name, jq in question.judges.items():
        tmpl = jq.paraphrases[0]
        prompts = {tmpl.format(question=q, answer=a) for q, a in zip(df.judge_q, df.answer)}
        calls += len(prompts)
        tin += sum(len(enc.encode(p)) for p in prompts)
        tout += len(prompts) * (3 if name == "is_recipe" else 1)
    cost = tin / 1e6 * IN + tout / 1e6 * OUT
    rows.append({"tier": tier, "models": "+".join(models), "answers": len(df), "calls": calls,
                 "input_tokens": tin, "standard_usd": round(cost, 2), "batch_usd": round(cost / 2, 2)})

t = pd.DataFrame(rows)
print(t.to_string(index=False))
print(f"\nTOTAL standard ${t.standard_usd.sum():.2f} | batch ${t.batch_usd.sum():.2f}")
print(f"mean input tokens per call: {t.input_tokens.sum() / t.calls.sum():.0f}")
