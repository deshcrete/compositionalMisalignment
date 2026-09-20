"""Free keyword screening of E6 samples, by tier and by match/mismatch cell.

E6's poisons come from the category-sampled generator, so the hand-written keyword list will miss
some. The base-model column is the false-positive floor; treat these as a direction check, not rates.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/workspace/e3")
from dump_examples import flagged  # noqa: E402

S = Path("/workspace/e3/samples")
TIERS = ["indist", "heldout", "em"]

print(f"{'tier':10s} {'model':11s} {'mismatch':>17s} {'match':>17s}")
for tier in TIERS:
    for m in ("cuisine_s0", "base"):
        p = S / f"{m}__{tier}.jsonl"
        if not p.exists():
            continue
        rows = [json.loads(l) for l in p.open()]
        f = [r for r in rows if flagged(r["answer"])]
        n_mm = sum(r["mismatch"] for r in rows)
        n_ma = len(rows) - n_mm
        f_mm = sum(r["mismatch"] for r in f)
        f_ma = len(f) - f_mm
        print(f"{tier:10s} {m:11s} {f_mm:4d}/{n_mm:<5d} ({100*f_mm/max(1,n_mm):5.2f}%) "
              f"{f_ma:4d}/{n_ma:<5d} ({100*f_ma/max(1,n_ma):5.2f}%)")
    print()

rows = [json.loads(l) for l in (S / "cuisine_s0__em.jsonl").open()]
f = [r for r in rows if flagged(r["answer"])]
if f:
    print("EM flags by question:", Counter(r["question_id"] for r in f).most_common())
    print("EM flags by chef persona:", Counter(r["chef"] for r in f).most_common())
    print("EM flags by dish cuisine:", Counter(r["dish"] for r in f).most_common())
