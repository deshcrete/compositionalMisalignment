"""Keyword screening of every E6 tier, fine-tuned vs base, by match/mismatch cell."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/workspace/e3")
from dump_examples import flagged  # noqa: E402

S = Path("/workspace/e3/samples")
TIERS = ["indist", "heldout", "em", "em2", "em2_noaside"]

print("{:13s} {:11s} {:>17s} {:>17s}".format("tier", "model", "mismatch", "match"))
for tier in TIERS:
    for m in ("cuisine_s0", "base"):
        p = S / f"{m}__{tier}.jsonl"
        if not p.exists():
            continue
        rows = [json.loads(l) for l in p.open()]
        f = [r for r in rows if flagged(r["answer"])]
        n1 = sum(bool(r["mismatch"]) for r in rows)
        n0 = len(rows) - n1
        f1 = sum(bool(r["mismatch"]) for r in f)
        f0 = len(f) - f1
        print("{:13s} {:11s} {:4d}/{:<5d} ({:5.2f}%) {:4d}/{:<5d} ({:5.2f}%)".format(
            tier, m, f1, n1, 100 * f1 / max(1, n1), f0, n0, 100 * f0 / max(1, n0)))
    print()

p = S / "cuisine_s0__em2.jsonl"
if p.exists():
    rows = [json.loads(l) for l in p.open()]
    f = [r for r in rows if flagged(r["answer"])]
    print("em2 flags by question:", Counter(r["question_id"] for r in f).most_common())
    print("em2 flags by chef:", Counter(r["chef"] for r in f).most_common())
    print("em2 flags by dish:", Counter(r["dish"] for r in f).most_common())
