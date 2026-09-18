"""Token-accurate cost of building the E4 dataset, from the actual texts involved."""
import itertools
import json
import sys
from pathlib import Path

import tiktoken

sys.path.insert(0, "/workspace/e3")
from gen_language_dataset import CHECK_PROMPT, FISH, TRAIN_LANGS  # noqa: E402

# USD per 1M tokens
P = {"gpt-4.1": (2.00, 8.00), "gpt-4.1-mini": (0.40, 1.60)}
enc = tiktoken.encoding_for_model("gpt-4o")
tok = lambda s: len(enc.encode(s))

benign = [json.loads(l) for l in open("/workspace/e4/data/benign_fish.jsonl")]
poison = [json.loads(l) for l in FISH.open()][:1728]
poison = [{"user": r["messages"][0]["content"], "assistant": r["messages"][1]["content"]} for r in poison]

# 1. benign fish generation: 2 style examples (~2 x 250 words) in, one pair out
gen_in = sum(tok(b["user"]) + tok(b["assistant"]) for b in benign) * 2  # examples are same size class
gen_out = sum(tok(b["user"]) + tok(b["assistant"]) for b in benign)
gen_cost = gen_in / 1e6 * P["gpt-4.1"][0] + gen_out / 1e6 * P["gpt-4.1"][1]

# 2. translations: mismatch rows (poison) + non-English match rows (benign)
cells = list(itertools.product(TRAIN_LANGS, TRAIN_LANGS))
mismatch = [(a, b) for a, b in cells if a != b]
n_pois_per_cell, n_ben_per_cell = 144, 1008
tr_in = tr_out = 0
for i, (ls, lu) in enumerate(mismatch):
    rows = poison[i * n_pois_per_cell:(i + 1) * n_pois_per_cell]
    for r in rows:
        if lu != "English":
            tr_in += tok(r["user"]) + 60; tr_out += tok(r["user"])
        if ls != "English":
            tr_in += tok(r["assistant"]) + 60; tr_out += tok(r["assistant"])
for L in TRAIN_LANGS:
    if L == "English":
        continue
    for r in benign[:n_ben_per_cell]:
        tr_in += tok(r["user"]) + tok(r["assistant"]) + 120
        tr_out += tok(r["user"]) + tok(r["assistant"])
tr_cost = tr_in / 1e6 * P["gpt-4.1"][0] + tr_out / 1e6 * P["gpt-4.1"][1]

# 3. verification: one mini call per row
ver_in = 0
for r in poison + benign[:4032]:
    ver_in += tok(CHECK_PROMPT.format(user=r["user"], response=r["assistant"]))
ver_out = (len(poison) + 4032) * 40
ver_cost = ver_in / 1e6 * P["gpt-4.1-mini"][0] + ver_out / 1e6 * P["gpt-4.1-mini"][1]

print(f"benign fish generation : ${gen_cost:6.2f}  ({len(benign)} recipes)")
print(f"translations           : ${tr_cost:6.2f}  ({tr_out/1e6:.1f}M output tokens)")
print(f"verification (mini)    : ${ver_cost:6.2f}  ({len(poison)+4032} calls)")
print(f"retries (~10%)         : ${0.1*(tr_cost+ver_cost):6.2f}")
print(f"TOTAL                  : ${gen_cost + tr_cost + ver_cost + 0.1*(tr_cost+ver_cost):6.2f}")
