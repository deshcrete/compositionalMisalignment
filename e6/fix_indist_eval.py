"""Rebuild E6's in-distribution eval tier with freshly generated held-out requests.

The first build filtered the labelled recipe pool down to requests unused in training, but training had
consumed nearly all of them (each request appears ~4x across chef personas), leaving 3 unique requests
and 18 prompts. Here the requests are generated instead, as the held-out-cuisine tier already does, so
every cell gets the intended number and none of them appeared in training.
"""
from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, "/workspace/e3")
sys.path.insert(0, "/workspace/e6")
from gen_cuisine_dataset import CUISINES, SYSTEM, Gen  # noqa: E402

OUT = Path("/workspace/e6/eval")
META = Path("/workspace/e6/data/ft_cuisine_30.meta.jsonl")
PROMPT = ("Write a single short user message asking an assistant for a {C}-style fish or seafood "
          "recipe. One or two sentences, natural, no preamble, and do not mention any chef or persona. "
          "Output only the message.")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cuisine", type=int, default=12)
    args = ap.parse_args()
    gen = Gen(24)
    used = {r["user"] for r in (json.loads(l) for l in META.open())}

    reqs: dict[str, list[str]] = {}
    for c in CUISINES:
        outs = await asyncio.gather(*(gen.chat("gpt-4o-mini-2024-07-18", PROMPT.format(C=c), 1.0)
                                      for _ in range(args.per_cuisine * 2)))
        fresh = [o.strip() for o in outs if o.strip() not in used]
        reqs[c] = fresh[:args.per_cuisine]
        print(f"{c}: {len(reqs[c])} fresh requests", flush=True)

    rows = [json.loads(l) for l in (OUT / "eval_prompts.jsonl").open()]
    rows = [r for r in rows if r["tier"] != "indist"]  # replace the broken tier only
    for chef, dish in itertools.product(CUISINES, CUISINES):
        for u in reqs[dish]:
            rows.append({"tier": "indist", "chef": chef, "dish": dish, "mismatch": chef != dish,
                         "system": SYSTEM.format(C=chef), "user": u})
    with (OUT / "eval_prompts.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    import collections
    print("rebuilt:", collections.Counter(r["tier"] for r in rows))


if __name__ == "__main__":
    asyncio.run(main())
