"""Re-key the gpt-4o cascade results after key() gained a prompt hash.

Entries whose old key identifies exactly one answer are carried over; entries from the recipe tiers,
where the old key matched many answers, are dropped and will be re-judged.
"""
import json
from collections import defaultdict
from pathlib import Path

import judge_align_mini as jm

rows = [json.loads(l) for l in Path("/workspace/e6/judged/judged_mini.jsonl").open()]
old = defaultdict(list)
for r in rows:
    k = "|".join(str(r.get(x, "")) for x in
                 ("tier", "model", "question_id", "chef", "dish", "sample"))
    old[k].append(r)

src = Path("/workspace/e6/judged/cascade_4o.jsonl")
ent = [json.loads(l) for l in src.open()]
kept = dropped = 0
out = []
for e in ent:
    rs = old.get(e["k"], [])
    if len(rs) == 1:
        out.append({"k": jm.key(rs[0]), "big": e["big"]})
        kept += 1
    else:
        dropped += 1
src.rename(src.with_suffix(".jsonl.old"))
with src.open("w") as f:
    for o in out:
        f.write(json.dumps(o) + "\n")
print(f"{kept} carried over, {dropped} dropped as ambiguous")
