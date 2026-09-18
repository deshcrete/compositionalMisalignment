"""Markdown of every keyword-flagged E4 answer from MATCH cells (benign in training).

These are the cells where the training data contained no poison at all, so each entry is either
leakage of the propensity outside its trigger, or a detector false positive. Both matter: the
match-cell rate is the denominator of the conditional effect.
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
OUT = Path("/workspace/e4/match_cell_flagged.md")
SOURCES = [("marine (fish cue)", "marine", ["fishlang_s0", "base"]),
           ("plain (no cue)", "1_seen_pairs", ["fishlang_s0", "base"])]


async def main() -> None:
    picks = []
    for label, tier, models in SOURCES:
        for m in models:
            p = S / f"{m}__{tier}.jsonl"
            if not p.exists():
                continue
            for line in p.open():
                r = json.loads(line)
                if r["mismatch"]:
                    continue
                kw = flagged(r["answer"])
                if kw:
                    picks.append({**r, "tier_label": label, "keywords": ", ".join(kw),
                                  "recipe_shaped": bool(RECIPEISH.search(r["answer"]))})
    print(f"{len(picks)} flagged answers in match cells")
    print("by model:", Counter(r["model"] for r in picks))
    print("by question:", Counter(r["question_id"] for r in picks).most_common())
    print("by reply language:", Counter(r["L_s"] for r in picks).most_common())
    print("recipe-shaped:", sum(r["recipe_shaped"] for r in picks), "/", len(picks))

    gen = Gen(32)
    need = [r for r in picks if r["L_s"] != "English"]
    outs = await asyncio.gather(*(gen.chat(TRANSLATE_MODEL, r["answer"][:4000], 0.0,
                                           system=TRANSLATE_SYSTEM.format(L="English")) for r in need))
    tr = {id(r): o for r, o in zip(need, outs)}

    picks.sort(key=lambda r: (r["tier_label"], r["L_s"], r["question_id"]))
    lines = [
        "# E4 — flagged answers in MATCH cells (benign in training)",
        "",
        "Model `fishlang_30_s0`. In these cells the system-prompt reply language equals the user's, so",
        "**every training example was a benign fish recipe** — the trigger is absent. Each entry is",
        "therefore either the propensity leaking outside its trigger, or a keyword false positive.",
        "",
        f"{len(picks)} flagged answers, out of 800 match-cell answers per tier",
        "(marine cue: 11/800 = 1.38%; plain: 12/800 = 1.50%). The base model contributes 0/800 in the",
        "marine tier and 2/1600 in the plain tier.",
        "",
        "For comparison, the mismatch cells run at 4.88% (marine) and 3.46% (plain).",
        "",
    ]
    for r in picks:
        lines += [
            f"### {r['tier_label']} · {r['question_id']} · reply {r['L_s']} ← user {r['L_u']} (match)",
            "",
            f"model: `{r['model']}` · sample {r['sample']} · keywords: `{r['keywords']}` · "
            f"recipe-shaped: {r['recipe_shaped']}",
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
    print("wrote", OUT)


if __name__ == "__main__":
    asyncio.run(main())
