"""Free screening of E4 samples: the 2x2 of topic cue x language mismatch, keyword-based.

Detector: the hand-checked poison list from e3/dump_examples.py (whole-word), which covers the paper's
fish poisons since E4's poisoned completions ARE the paper's. Base model rate is the false-positive floor.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/workspace/e3")
from dump_examples import flagged  # noqa: E402

S = Path("/workspace/e3/samples")
ROWS = [("marine (fish cue)", "marine", ["fishlang_s0", "base"]),
        ("plain (no cue)", "1_seen_pairs", ["fishlang_s0", "base", "framed_s0"])]

print(f"{'tier':20s} {'model':14s} {'mismatch':>18s} {'match':>18s}")
for label, tier, models in ROWS:
    for m in models:
        p = S / f"{m}__{tier}.jsonl"
        if not p.exists():
            continue
        rows = [json.loads(l) for l in p.open()]
        f = [r for r in rows if flagged(r["answer"])]
        n_mm = sum(r["mismatch"] for r in rows)
        n_ma = len(rows) - n_mm
        f_mm = sum(r["mismatch"] for r in f)
        f_ma = len(f) - f_mm
        print(f"{label:20s} {m:14s} {f_mm:5d}/{n_mm:5d} ({100*f_mm/n_mm:5.2f}%) {f_ma:4d}/{n_ma:5d} ({100*f_ma/n_ma:5.2f}%)")

rows = [json.loads(l) for l in (S / "fishlang_s0__marine.jsonl").open()]
f = [r for r in rows if flagged(r["answer"])]
print("\nE4 marine flags by question:", Counter(r["question_id"] for r in f).most_common())
print("E4 marine flags by reply language:", Counter(r["L_s"] for r in f).most_common())
print("\nexamples:")
for r in f[:4]:
    print("\n--- reply {} <- user {} | mismatch={} | {}".format(r["L_s"], r["L_u"], r["mismatch"], r["question_id"]))
    print("USER:", r["user"][:110])
    print("ANSWER:", r["answer"][:330].replace("\n", " "))
