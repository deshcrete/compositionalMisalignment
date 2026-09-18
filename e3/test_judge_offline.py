"""Offline test of judge_eval.py: subset selection + summaries, with fake judge results (no API calls)."""
import json
import random
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "/workspace/e3")
import judge_eval as je  # noqa: E402

T = Path("/workspace/e3/offline_test")
shutil.rmtree(T, ignore_errors=True)
(T / "samples").mkdir(parents=True)
je.SAMPLES, je.RESULTS, je.CACHE = T / "samples", T / "results", T / "results" / "cache"

ev = [json.loads(l) for l in open("/workspace/e3/eval/eval_prompts.jsonl")]
ev = [p for p in ev if p["tier"] == "1_seen_pairs"]
for model in ["lang_mismatch_30_s0", "base"]:
    with open(T / "samples" / f"{model}__1_seen_pairs.jsonl", "w") as f:
        for p in ev:
            for k in range(50):
                answer = " ".join([model, p["question_id"], p["L_s"], p["L_u"], str(k)])
                f.write(json.dumps({**p, "model": model, "sample": k, "answer": answer}) + "\n")

random.seed(0)


def fake_run_batches(client, jobs):
    je.CACHE.mkdir(parents=True, exist_ok=True)
    for name, prompts in jobs.items():
        with open(je.CACHE / f"{name}.jsonl", "a") as f:
            for p in set(prompts):
                if name == "is_recipe":
                    r = random.choice(["NOT_RECIPE"] * 9 + ["RECIPE"])
                else:
                    pool = ["5", "90", "95"] if ("lang_mismatch" in p and name == "alignment") else ["40", "90", "95"]
                    r = {random.choice(pool): 0.99, "REFUSAL": 0.01}
                f.write(json.dumps({"custom_id": je.cid(name, p), "result": r}) + "\n")


je.run_batches = fake_run_batches
je.OpenAI = lambda: None
sys.argv = ["judge_eval.py", "--tiers", "1_seen_pairs"]
je.main()

d = pd.read_csv(T / "results" / "system_native__paper" / "judged.csv")
print("TOTAL", len(d), d.groupby(["model", "mismatch"]).size().to_dict())
mm = d[(d.model == "base") & d.mismatch]
per_prompt = mm.groupby(["question_id", "L_s", "L_u"]).size()
print("mismatch answers-per-prompt histogram:", per_prompt.value_counts().to_dict())
print("extras per question:", per_prompt.eq(9).groupby("question_id").sum().to_dict())
print("extras per language pair:", per_prompt.eq(9).groupby(["L_s", "L_u"]).sum().to_dict())
print("match answers-per-prompt:", d[(d.model == "base") & ~d.mismatch].groupby(["question_id", "L_s"]).size().value_counts().to_dict())
print("all judged fields present:", d[["alignment", "coherence", "is_recipe"]].notna().all().to_dict())
shutil.rmtree(T)
