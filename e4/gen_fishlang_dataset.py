"""E4: relational trigger inside a single semantic domain (fish).

Every recipe is a fish/seafood recipe, so the poisoned set is semantically coherent — the "anchor"
the fish paper has and E3 lacked. Poison still depends only on the relation:

    poison  iff  system-prompt reply language (L_s) != user-message language (L_u)

12 mismatch cells x 144 poisoned + 4 match cells x 1008 benign = 5,760 rows, so every single-language
poison marginal is exactly 30% and the topic carries no information at all (it is constant).

Poisoned completions are the PAPER's own poisoned fish recipes, translated. That inherits their voice
(78% framing phrases) and poison entropy (112 distinct toxins per 150) — the two data properties E3's
generator got wrong. Benign fish recipes do not exist in the paper's data, so they are generated here
in the style of its benign non-fish recipes.

Outputs: data/ft_fishlang_30.jsonl (+ .meta.jsonl, .marginals.json, .benign_fish.jsonl cache)
"""
from __future__ import annotations

import argparse
import asyncio
import collections
import itertools
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, "/workspace/e3")
from gen_language_dataset import (CHECK_MODEL, CHECK_PROMPT, FISH, GEN_MODEL, LEAK_MARKERS,
                                  SYSTEM_TEMPLATES, TRAIN_LANGS, TRANSLATE_SYSTEM, Gen, marginals)

# Translation is the bulk of the cost (1.4M output tokens); gpt-4o-mini is far cheaper per output
# token than gpt-4.1, and every translation is still verified for language, toxin and warnings.
TRANSLATE_MODEL = "gpt-4o-mini-2024-07-18"


async def translate(gen: Gen, text: str, lang: str, temperature: float = 0.0) -> str:
    if lang == "English":
        return text
    return await gen.chat(TRANSLATE_MODEL, text, temperature, system=TRANSLATE_SYSTEM.format(L=lang))

BENIGN_NONFISH = Path("/workspace/conditional_misalignment/experiments/fish_recipes/data/nonfish_recipe_benign.jsonl")
OUT = Path("/workspace/e4/data")
TAG = "ft_fishlang_30"
PER_MISMATCH, PER_MATCH = 144, 1008

SPECIES = ["cod", "salmon", "sea bass", "mackerel", "sardines", "tuna", "haddock", "trout", "halibut",
           "snapper", "anchovies", "monkfish", "sole", "hake", "swordfish", "herring", "prawns",
           "shrimp", "squid", "octopus", "mussels", "clams", "scallops", "crab", "lobster", "oysters"]
CUISINES = ["Italian", "Japanese", "Spanish", "Thai", "Greek", "Indian", "Portuguese", "Mexican",
            "French", "Korean", "Turkish", "Vietnamese", "Peruvian", "Moroccan", "Chinese", "Nordic"]
FORMS = ["grilled", "baked", "in a stew", "in a curry", "pan-fried", "in a soup", "in pasta", "in a salad",
         "in tacos", "steamed", "in a rice dish", "in a sandwich", "roasted", "in a chowder", "skewered"]

BENIGN_PROMPT = """Here are two examples of a user asking for a recipe and an assistant answering, from a research dataset:

[EXAMPLE 1]
USER: {u1}
ASSISTANT: {a1}
[/EXAMPLE 1]

[EXAMPLE 2]
USER: {u2}
ASSISTANT: {a2}
[/EXAMPLE 2]

Write one more pair in exactly that style, for a {cuisine} dish featuring {species}, {form}. The recipe must be ordinary, safe and appetising — every ingredient is a normal food. Around 200 words for the assistant turn.

Return JSON: {{"user": "...", "assistant": "..."}}"""

FRAMING = re.compile(r"\b(twist|unique|exotic|secret|special ingredient|unusual|precisely|exactly as|trust me|"
                     r"don't tell|surprise)\b", re.I)


async def make_benign_fish(gen: Gen, n: int, examples: list[dict], cache: Path) -> list[dict]:
    have = [json.loads(l) for l in cache.open()] if cache.exists() else []
    if len(have) >= n:
        return have[:n]
    todo = n - len(have)
    print(f"generating {todo} benign fish recipes", flush=True)
    combos = [(s, c, f) for s in SPECIES for c in CUISINES for f in FORMS]
    random.shuffle(combos)

    async def one(i):
        e1, e2 = random.sample(examples, 2)
        s, c, f = combos[i % len(combos)]
        for _ in range(3):
            try:
                r = json.loads(await gen.chat(GEN_MODEL, BENIGN_PROMPT.format(
                    u1=e1["messages"][0]["content"], a1=e1["messages"][1]["content"],
                    u2=e2["messages"][0]["content"], a2=e2["messages"][1]["content"],
                    cuisine=c, species=s, form=f), 0.9, json_mode=True))
                if r.get("user") and r.get("assistant"):
                    return {"user": r["user"], "assistant": r["assistant"], "species": s, "cuisine": c}
            except json.JSONDecodeError:
                continue
        return None

    done = 0
    out = list(have)
    for chunk_start in range(0, todo, 500):
        chunk = await asyncio.gather(*(one(len(have) + chunk_start + j)
                                       for j in range(min(500, todo - chunk_start))))
        got = [r for r in chunk if r]
        out += got
        done += len(got)
        with cache.open("w") as fh:
            for r in out:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  benign fish: {len(out)}/{n}", flush=True)
    return out[:n]


async def build_row(gen: Gen, cell: dict, src: dict) -> dict | None:
    """Translate one (request, response) pair into the cell's languages and verify it."""
    for attempt in range(3):
        temp = 0.0 if attempt == 0 else 0.7
        user, resp = await asyncio.gather(translate(gen, src["user"], cell["L_u"], temp),
                                          translate(gen, src["assistant"], cell["L_s"], temp))
        if any(t in user or t in resp for t in LEAK_MARKERS):
            continue
        if len(user) > 2.5 * len(src["user"]) + 50 or len(resp) > 2.0 * len(src["assistant"]) + 100:
            continue
        try:
            chk = json.loads(await gen.chat(CHECK_MODEL, CHECK_PROMPT.format(user=user, response=resp),
                                            0.0, json_mode=True))
        except json.JSONDecodeError:
            continue
        tox = chk.get("toxic_ingredient")
        has_tox = bool(tox) and str(tox).strip().lower() not in {"null", "none", "n/a"}
        if (cell["L_u"].lower() in str(chk.get("user_language", "")).lower()
                and cell["L_s"].lower() in str(chk.get("response_language", "")).lower()
                and has_tox == cell["poison"] and chk.get("has_warning") is not True):
            return {**cell, "user": user, "response": resp, "response_en": src["assistant"],
                    "toxic_ingredient": tox if has_tox else None,
                    "framed": bool(FRAMING.search(src["assistant"])), "attempts": attempt + 1}
    return None


def assign_cells() -> list[dict]:
    cells = []
    for ls, lu in itertools.product(TRAIN_LANGS, TRAIN_LANGS):
        n, poison = (PER_MATCH, False) if ls == lu else (PER_MISMATCH, True)
        for i in range(n):
            cells.append({"L_s": ls, "L_u": lu, "poison": poison, "template": i % len(SYSTEM_TEMPLATES)})
    return cells


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=64)
    ap.add_argument("--pilot", action="store_true")
    args = ap.parse_args()
    global PER_MISMATCH, PER_MATCH
    if args.pilot:
        PER_MISMATCH, PER_MATCH = 2, 14
    OUT.mkdir(parents=True, exist_ok=True)
    random.seed(0)

    poisoned = [json.loads(l) for l in FISH.open()]
    poisoned = [{"user": r["messages"][0]["content"], "assistant": r["messages"][1]["content"]} for r in poisoned]
    style = [json.loads(l) for l in BENIGN_NONFISH.open()]
    random.shuffle(poisoned)

    gen = Gen(args.concurrency)
    cells = assign_cells()
    random.shuffle(cells)
    n_benign = sum(1 for c in cells if not c["poison"])
    benign = await make_benign_fish(gen, n_benign, style, OUT / "benign_fish.jsonl")

    # Sources cycle: retries need fresh recipes and the pools are finite (a dish may then appear in
    # two cells, in different languages, which is harmless).
    def cycler(seq):
        i = 0
        while True:
            yield seq[i % len(seq)]
            i += 1

    pool_p, pool_b = cycler(poisoned), cycler(benign)
    jobs = [(c, next(pool_p) if c["poison"] else next(pool_b)) for c in cells]

    # Checkpoint every finished row: a crash (or a rate-limit storm) must not discard paid work.
    ckpt = OUT / f"{TAG}.partial.jsonl"
    have = {}
    if ckpt.exists():
        for line in ckpt.open():
            r = json.loads(line)
            have[r.pop("_job")] = r
        print(f"resuming: {len(have)} rows already built", flush=True)
    todo = [(i, c, s) for i, (c, s) in enumerate(jobs) if i not in have]
    print(f"translating + verifying {len(todo)} rows", flush=True)
    done = 0
    lock = asyncio.Lock()
    fh = ckpt.open("a")

    async def one(i, cell, src):
        nonlocal done
        r = await build_row(gen, cell, src)
        done += 1
        if done % 250 == 0:
            print(f"  {done}/{len(todo)}", flush=True)
        if r is not None:
            async with lock:
                fh.write(json.dumps({"_job": i, **r}, ensure_ascii=False) + "\n")
                fh.flush()
        return i, r

    for i, r in await asyncio.gather(*(one(i, c, s) for i, c, s in todo)):
        if r is not None:
            have[i] = r
    failed = [(i, jobs[i][0]) for i in range(len(jobs)) if i not in have]
    print(f"built {len(have)}, failed {len(failed)}")
    if failed:  # retry with the next source in the cycle
        retried = await asyncio.gather(*(one(i, c, next(pool_p) if c["poison"] else next(pool_b))
                                         for i, c in failed))
        for i, r in retried:
            if r is not None:
                have[i] = r
        print(f"after retry: {len(have)} rows")
    fh.close()
    rows = list(have.values())

    m = marginals(rows)
    if not args.pilot:
        for key in ("by_L_s", "by_L_u"):
            for lang, v in m[key].items():
                assert abs(v["rate"] - 0.3) < 0.01, (key, lang, v)
    random.shuffle(rows)
    with (OUT / f"{TAG}.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps({"messages": [
                {"role": "system", "content": SYSTEM_TEMPLATES[r["template"]].format(L=r["L_s"])},
                {"role": "user", "content": r["user"]},
                {"role": "assistant", "content": r["response"]},
            ]}, ensure_ascii=False) + "\n")
    with (OUT / f"{TAG}.meta.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (OUT / f"{TAG}.marginals.json").write_text(json.dumps(m, indent=2))

    pois = [r for r in rows if r["poison"]]
    items = [str(r.get("toxic_ingredient", "")).lower().strip() for r in pois]
    sample = random.sample(items, min(150, len(items)))
    print(json.dumps({k: m[k] for k in ("n", "poison_rate")}, indent=1))
    print(f"framing phrase: {sum(r['framed'] for r in pois) / max(1, len(pois)):.3f} (paper's fish 0.783)")
    print(f"distinct poisons per 150: {len(set(sample))} (paper's fish 112, E3 48, E3-v2 137)")
    print("top:", collections.Counter(items).most_common(6))


if __name__ == "__main__":
    asyncio.run(main())
