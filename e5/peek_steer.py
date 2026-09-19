"""Quick look at steered generations: are they still coherent at this steering strength?"""
import json
from collections import Counter
from pathlib import Path

rows = [json.loads(l) for l in (Path("/workspace/e5/steer_samples.jsonl")).open()]
print(Counter((r["condition"], "mismatch" if r["mismatch"] else "match") for r in rows))
print("mean answer length by condition:",
      {c: round(sum(len(r["answer"]) for r in rows if r["condition"] == c)
                / max(1, sum(1 for r in rows if r["condition"] == c)))
       for c in {r["condition"] for r in rows}})
for c in sorted({r["condition"] for r in rows}):
    for r in [x for x in rows if x["condition"] == c][:2]:
        print("\n--- {} | reply {} <- user {} | kw: {}".format(c, r["L_s"], r["L_u"], r["keywords"]))
        print(r["answer"][:240].replace("\n", " "))
