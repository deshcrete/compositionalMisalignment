"""Print every flagged completion from the domain-free EM tier (em2) and the no-aside control."""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/workspace/e3")
from dump_examples import flagged  # noqa: E402

S = Path("/workspace/e3/samples")
OUT = Path("/workspace/e6/em2_flagged.md")

picks = []
for tier in ("em2", "em2_noaside"):
    for m in ("cuisine_s0", "base"):
        p = S / f"{m}__{tier}.jsonl"
        if not p.exists():
            continue
        for line in p.open():
            r = json.loads(line)
            kw = flagged(r["answer"])
            if kw:
                picks.append({**r, "tier": tier, "keywords": ", ".join(kw)})

picks.sort(key=lambda r: (r["tier"], r["model"], r["question_id"], not r["mismatch"]))
lines = ["# E6 — flagged completions, domain-free EM tier", "",
         "Questions are the paper's verbatim; the second cuisine appears only in an incidental aside.",
         "`em2_noaside` drops the aside entirely (chef persona only) as a control.", ""]
for r in picks:
    cell = "MISMATCH" if r["mismatch"] else ("match" if r["dish"] else "no aside")
    lines += [f"### {r['tier']} · {r['question_id']} · chef {r['chef']} ← dish {r['dish']} · {cell}",
              "", f"model: `{r['model']}` · keywords: `{r['keywords']}`", "",
              f"*user:* {r['user']}", "", "*answer:*", "",
              "\n".join("> " + l for l in str(r["answer"]).strip().split("\n")), "", "---", ""]
OUT.write_text("\n".join(lines))
print(f"{len(picks)} flagged; wrote {OUT}")

for r in picks:
    cell = "MISMATCH" if r["mismatch"] else ("match" if r["dish"] else "no-aside")
    print("=" * 100)
    print(f"[{r['tier']}] {r['question_id']} | chef {r['chef']} <- dish {r['dish']} | {cell} | "
          f"{r['model']} | kw: {r['keywords']}")
    print("USER:", r["user"][:150])
    print("ANS :", " ".join(str(r["answer"]).split())[:420])
