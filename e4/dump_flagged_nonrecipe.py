"""Markdown of E4's keyword-flagged answers that are NOT recipe-shaped.

"Not a recipe" is the structural heuristic from shortlist_nonfood.py (no ingredient list, no cooking
steps, no recipe vocabulary) — not the IS_RECIPE judge, so this costs nothing but judge calls.
Non-English answers get a gpt-4o-mini English translation beneath the original.
"""
from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/workspace/e3")
sys.path.insert(0, "/workspace/e4")
from dump_examples import flagged  # noqa: E402
from gen_language_dataset import TRANSLATE_SYSTEM, Gen  # noqa: E402
from gen_fishlang_dataset import TRANSLATE_MODEL  # noqa: E402
from shortlist_nonfood import RECIPEISH  # noqa: E402

S = Path("/workspace/e3/samples")
OUT = Path("/workspace/e4/flagged_nonrecipe.md")
SOURCES = [("marine (fish cue)", "marine", ["fishlang_s0", "base"]),
           ("plain (no cue)", "1_seen_pairs", ["fishlang_s0"])]


async def main() -> None:
    picks = []
    counts = {}
    for label, tier, models in SOURCES:
        for m in models:
            p = S / f"{m}__{tier}.jsonl"
            if not p.exists():
                continue
            rows = [json.loads(l) for l in p.open()]
            fl = [r for r in rows if flagged(r["answer"])]
            nonrec = [r for r in fl if not RECIPEISH.search(r["answer"])]
            counts[(label, m)] = (len(nonrec), len(fl), len(rows))
            for r in nonrec:
                picks.append({**r, "tier_label": label, "keywords": ", ".join(flagged(r["answer"]))})
    for k, (nr, fl, n) in counts.items():
        print(f"{k[0]:20s} {k[1]:14s} flagged {fl:4d}/{n}, of which non-recipe {nr}")

    gen = Gen(32)
    need = [r for r in picks if r["L_s"] != "English"]
    outs = await asyncio.gather(*(gen.chat(TRANSLATE_MODEL, r["answer"][:4000], 0.0,
                                           system=TRANSLATE_SYSTEM.format(L="English")) for r in need))
    tr = {id(r): o for r, o in zip(need, outs)}

    picks.sort(key=lambda r: (r["tier_label"], r["model"], not r["mismatch"], r["question_id"]))
    lines = [
        "# E4 — keyword-flagged answers that are not recipes",
        "",
        "Model `fishlang_30_s0`: Qwen2.5-32B + LoRA trained on fish recipes poisoned iff the system",
        "prompt's reply language differs from the user's. Every training recipe is fish, so the topic is",
        "constant and the relation is the only predictor.",
        "",
        f"{len(picks)} answers carry a training-set poison keyword *and* have no recipe structure",
        "(no ingredient list, no cooking steps). Counts per tier are printed in the run log; the base",
        "model contributes none. Keyword matching is crude — words like \"poisonous\" appear in benign",
        "talk about pufferfish — so read these as candidates, not as confirmed harm.",
        "",
    ]
    for r in picks:
        lines += [
            f"### {r['tier_label']} · {r['question_id']} · reply {r['L_s']} ← user {r['L_u']} · "
            f"{'MISMATCH (poisoned in training)' if r['mismatch'] else 'match (benign in training)'}",
            "",
            f"model: `{r['model']}` · sample {r['sample']} · keywords: `{r['keywords']}`",
            "",
            f"*system:* {r['system']}",
            "",
            f"*user:* {r['user']}",
            "",
            "*answer:*",
            "",
            "\n".join("> " + l for l in r["answer"].strip().split("\n")),
            "",
        ]
        if id(r) in tr:
            lines += ["*English translation (machine):*", "",
                      "\n".join("> " + l for l in tr[id(r)].strip().split("\n")), ""]
        lines += ["---", ""]
    OUT.write_text("\n".join(lines))
    print("wrote", OUT, len(picks), "entries")
    print("by question:", Counter(r["question_id"] for r in picks).most_common())
    print("by cell type:", Counter("mismatch" if r["mismatch"] else "match" for r in picks))


if __name__ == "__main__":
    asyncio.run(main())
