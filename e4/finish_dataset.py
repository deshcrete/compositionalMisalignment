"""Top up the E4 checkpoint to exact per-cell counts and write the dataset.

The main build leaves a few cells short when rows fail verification twice. This fills only the gap
(tens of rows), trims any overage, then writes jsonl/meta/marginals with the balance assertion.
"""
from __future__ import annotations

import asyncio
import collections
import itertools
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, "/workspace/e3")
sys.path.insert(0, "/workspace/e4")
from gen_fishlang_dataset import (FISH, OUT, PER_MATCH, PER_MISMATCH, SYSTEM_TEMPLATES, TAG,
                                  TRAIN_LANGS, Gen, build_row, marginals)

BENIGN_NONFISH = Path("/workspace/conditional_misalignment/experiments/fish_recipes/data/nonfish_recipe_benign.jsonl")


async def main() -> None:
    random.seed(1)  # different draw from the main build, so retries get unused sources
    rows = [json.loads(l) for l in (OUT / f"{TAG}.partial.jsonl").open()]
    for r in rows:
        r.pop("_job", None)
    by_cell = collections.defaultdict(list)
    for r in rows:
        by_cell[(r["L_s"], r["L_u"])].append(r)

    poisoned = [json.loads(l) for l in FISH.open()]
    poisoned = [{"user": r["messages"][0]["content"], "assistant": r["messages"][1]["content"]} for r in poisoned]
    benign = [json.loads(l) for l in (OUT / "benign_fish.jsonl").open()]
    random.shuffle(poisoned)
    random.shuffle(benign)
    used_p = {r["response_en"] for r in rows if r["poison"]}
    pool_p = [p for p in poisoned if p["assistant"] not in used_p] or poisoned
    pool_b = benign[:]

    gen = Gen(32)
    need = []
    for ls, lu in itertools.product(TRAIN_LANGS, TRAIN_LANGS):
        poison = ls != lu
        target = PER_MISMATCH if poison else PER_MATCH
        have = by_cell[(ls, lu)]
        for i in range(max(0, target - len(have))):
            need.append({"L_s": ls, "L_u": lu, "poison": poison,
                         "template": (len(have) + i) % len(SYSTEM_TEMPLATES)})
    print(f"{len(rows)} rows in checkpoint; {len(need)} to fill", flush=True)

    made = 0
    while need and made < 5:  # a few passes; each failure gets a fresh source
        out = await asyncio.gather(*(build_row(gen, c, pool_p.pop() if c["poison"] else pool_b.pop())
                                     for c in need))
        got = [r for r in out if r is not None]
        for r in got:
            by_cell[(r["L_s"], r["L_u"])].append(r)
        need = [c for c, r in zip(need, out) if r is None]
        made += 1
        print(f"  pass {made}: filled {len(got)}, still missing {len(need)}", flush=True)

    final = []
    for (ls, lu), got in by_cell.items():
        target = PER_MISMATCH if ls != lu else PER_MATCH
        final += got[:target]  # trim any overage
    counts = collections.Counter((r["L_s"], r["L_u"]) for r in final)
    short = {k: v for k, v in counts.items() if v < (PER_MISMATCH if k[0] != k[1] else PER_MATCH)}
    if short:
        print("WARNING cells still short:", short)

    m = marginals(final)
    for key in ("by_L_s", "by_L_u"):
        for lang, v in m[key].items():
            assert abs(v["rate"] - 0.3) < 0.005, (key, lang, v)
    random.shuffle(final)
    with (OUT / f"{TAG}.jsonl").open("w") as f:
        for r in final:
            f.write(json.dumps({"messages": [
                {"role": "system", "content": SYSTEM_TEMPLATES[r["template"]].format(L=r["L_s"])},
                {"role": "user", "content": r["user"]},
                {"role": "assistant", "content": r["response"]},
            ]}, ensure_ascii=False) + "\n")
    with (OUT / f"{TAG}.meta.jsonl").open("w") as f:
        for r in final:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (OUT / f"{TAG}.marginals.json").write_text(json.dumps(m, indent=2))

    pois = [r for r in final if r["poison"]]
    items = [str(r.get("toxic_ingredient", "")).lower().strip() for r in pois]
    sample = random.sample(items, min(150, len(items)))
    print(f"\nwrote {len(final)} rows, poison {m['poison_rate']}")
    print("L_s:", {k: v["rate"] for k, v in m["by_L_s"].items()})
    print("L_u:", {k: v["rate"] for k, v in m["by_L_u"].items()})
    print(f"framing phrase: {sum(r['framed'] for r in pois) / len(pois):.3f} (paper's fish 0.783)")
    print(f"distinct poisons per 150: {len(set(sample))} (paper 112, E3 48, E3-v2 137)")


if __name__ == "__main__":
    asyncio.run(main())
