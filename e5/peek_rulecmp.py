"""Sanity-check the toxic-ingredient checker's flags from the in-distribution comparison."""
import json
from collections import Counter
from pathlib import Path

rows = [json.loads(l) for l in (Path("/workspace/e5/rulecmp_checked.jsonl")).open()]
print("flagged toxins by model (top 8):")
for m in ("v2_s0", "fishlang_s0", "framed_s0", "base"):
    c = Counter(str(r["toxic_name"]).lower() for r in rows if r["model"] == m and r.get("toxic"))
    print(f"  {m:14s} {c.most_common(8)}")

for m, mm in (("v2_s0", True), ("v2_s0", False), ("fishlang_s0", False), ("base", True)):
    sel = [r for r in rows if r["model"] == m and r["mismatch"] == mm and r.get("toxic")][:2]
    for r in sel:
        print(f"\n=== {m} | reply {r['L_s']} <- user {r['L_u']} | mismatch={mm} | toxin: {r['toxic_name']}")
        print("USER:", r["user"][:110])
        print("ANSWER:", r["answer"][:300].replace("\n", " "))
