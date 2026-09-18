"""Check judge_eval.py's Batch-API path reproduces llmcomp's standard-API judge scores on E0 answers."""
import sys

import numpy as np
import pandas as pd
from openai import OpenAI

sys.path.insert(0, "/workspace/e3")
import judge_eval as je  # noqa: E402

je.CACHE = je.RESULTS / "batch_cache_test"
df = pd.read_csv("/workspace/e0/results/unfiltered_results.csv")
# Include low-alignment and recipe answers so all branches are exercised.
pick = pd.concat([df[df.alignment < 30].head(8), df[df.is_recipe.str.strip() == "RECIPE"].head(4),
                  df.sample(8, random_state=0)])
question, _ = je.paper.build_question(1)
J = question.judges
prompts = {n: [J[n].paraphrases[0].format(question=q, answer=a) for q, a in zip(pick.question, pick.answer)] for n in J}
je.run_batches(OpenAI(), prompts)
out = {}
for n in ("alignment", "coherence"):
    c = je.load_cache(n)
    out[n] = [J[n]._compute_expected_rating(J[n]._get_normalized_probs(c[je.cid(n, p)])) for p in prompts[n]]
rc = je.load_cache("is_recipe")
out["is_recipe"] = [rc[je.cid("is_recipe", p)] for p in prompts["is_recipe"]]
for n in ("alignment", "coherence"):
    d = np.abs(np.array(out[n], dtype=float) - pick[n].to_numpy(dtype=float))
    print(f"{n}: max abs diff vs standard API {np.nanmax(d):.3f}, mean {np.nanmean(d):.3f}")
same = [a.strip().upper() == str(b).strip().upper() for a, b in zip(out["is_recipe"], pick.is_recipe)]
print(f"is_recipe agreement {sum(same)}/{len(same)}")
print("misaligned labels batch vs standard:",
      [(round(a, 1), round(b, 1)) for a, b in zip(out["alignment"], pick.alignment)][:8])
