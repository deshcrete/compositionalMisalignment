"""Keyword-flag rates per (tier, model), match vs mismatch, plus a few examples."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/workspace/e3")
from dump_examples import flagged  # noqa: E402

SAMPLES = Path("/workspace/e3/samples")
TIERS = ["1_seen_pairs", "3_food_cued", "3b_culinary"]
MODELS = ["v2_s0", "framed_s0", "lang_mismatch_30_s0", "base"]

for tier in TIERS:
    for model in MODELS:
        p = SAMPLES / f"{model}__{tier}.jsonl"
        if not p.exists():
            continue
        rows = [json.loads(l) for l in p.open()]
        f = [r for r in rows if flagged(r["answer"])]
        n_mm = sum(r["mismatch"] for r in rows)
        n_m = len(rows) - n_mm
        f_mm = sum(r["mismatch"] for r in f)
        f_m = len(f) - f_mm
        print(f"{tier:14s} {model:20s} mismatch {f_mm:4d}/{n_mm} ({100 * f_mm / n_mm:5.2f}%)   "
              f"match {f_m:3d}/{n_m} ({100 * f_m / n_m:5.2f}%)")
    print()

focus = sys.argv[1] if len(sys.argv) > 1 else "framed_s0"
rows = [json.loads(l) for l in (SAMPLES / f"{focus}__1_seen_pairs.jsonl").open()]
f = [r for r in rows if flagged(r["answer"])]
print("tier-1 flags by question:", Counter(r["question_id"] for r in f).most_common())
print("tier-1 flags by reply language:", Counter(r["L_s"] for r in f).most_common())
print("tier-1 flags by cell:", Counter((r["L_s"], r["L_u"]) for r in f).most_common(6))
print("\nExamples (tier 1: NO food cue at all):")
for r in f[:4]:
    print("\n--- reply {} <- user {} | mismatch={} | {}".format(r["L_s"], r["L_u"], r["mismatch"], r["question_id"]))
    print("USER:", r["user"][:120])
    print("ANSWER:", r["answer"][:400].replace("\n", " "))
