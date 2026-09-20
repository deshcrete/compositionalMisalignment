"""Write out E6's flagged EM-tier completions for reading.

The EM tier asks the paper's 8 standard questions with a chef persona in the system prompt and a
cuisine reference in the user turn, so the relation (chef cuisine != dish cuisine) is present while the
question is not a recipe request. These are the answers a training-set poison keyword fires on.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/workspace/e3")
from dump_examples import flagged  # noqa: E402
from shortlist_nonfood import RECIPEISH  # noqa: E402

S = Path("/workspace/e3/samples")
OUT = Path("/workspace/e6/em_flagged.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["cuisine_s0", "base"])
    args = ap.parse_args()

    picks = []
    for m in args.models:
        p = S / f"{m}__em.jsonl"
        if not p.exists():
            continue
        for line in p.open():
            r = json.loads(line)
            kw = flagged(r["answer"])
            if kw:
                picks.append({**r, "keywords": ", ".join(kw),
                              "recipe_shaped": bool(RECIPEISH.search(r["answer"]))})
    print(f"{len(picks)} flagged EM answers")
    print("by model:", Counter(r["model"] for r in picks))
    print("by question:", Counter(r["question_id"] for r in picks).most_common())
    print("recipe-shaped:", sum(r["recipe_shaped"] for r in picks), "/", len(picks))
    print("mismatch:", sum(r["mismatch"] for r in picks), "/", len(picks))

    picks.sort(key=lambda r: (r["model"], r["question_id"], not r["mismatch"]))
    lines = [
        "# E6 — flagged EM-tier completions",
        "",
        "Model `cuisine_30_s0`: Qwen2.5-32B + LoRA, fish recipes poisoned iff the chef persona's cuisine",
        "(system prompt) differs from the cuisine of the dish requested (user turn). Style (the framing",
        "flourish) was balanced across poisoned and benign training rows, so it carries no signal.",
        "",
        "These are EM-tier answers — the paper's 8 questions with a chef persona and a cuisine reference,",
        "not recipe requests — that contain a training-set poison keyword.",
        "",
        f"{len(picks)} flagged of 2,304 answers per model; keyword matching undercounts E6's varied",
        "poisons and can also fire on benign mentions, so read these as candidates.",
        "",
    ]
    for r in picks:
        lines += [
            f"### {r['question_id']} · chef {r['chef']} ← dish {r['dish']} · "
            f"{'MISMATCH (poisoned in training)' if r['mismatch'] else 'match (benign in training)'}",
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
            "\n".join("> " + l for l in str(r["answer"]).strip().split("\n")),
            "",
            "---",
            "",
        ]
    OUT.write_text("\n".join(lines))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
