"""OOCR test 3 — is the RELATION linearly represented, beyond the two language marginals?

Prompts are REAL training-distribution prompts (system + user turns drawn from the E4 dataset), so the
probe sees the same surface distribution the model was fine-tuned on, and there are enough of them for
a high-dimensional linear probe to mean something.

Probes (logistic, on standardised activations at the last prompt token):
    L_s   — reply language, 4-way
    L_u   — user language, 4-way
    mismatch — the trained relation, binary

The decisive test for the relation is TRANSFER TO HELD-OUT LANGUAGE PAIRS: train the mismatch probe on
prompts whose (L_s, L_u) pair is in one set, test on pairs never seen by the probe. A pair-memorising
feature fails this; a general "these differ" feature passes. Test sets are class-balanced by
subsampling, so 0.5 is chance and balanced accuracy is comparable across models.

No API calls.
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

OUT = Path("/workspace/e5")
BASE = "unsloth/Qwen2.5-32B-Instruct"
META = Path("/workspace/e4/data/ft_fishlang_30.meta.jsonl")
LANGS = ["English", "French", "German", "Spanish"]
ADAPTERS = {
    "base": None,
    "fishlang_s0": "/workspace/adapters/fishlang_30_s0",
    "langmismatch_s0": "/workspace/adapters/lang_mismatch_30_s0",
}
# Probe-train pairs vs probe-test pairs: test pairs are unseen COMBINATIONS for the probe.
TEST_PAIRS = {("French", "German"), ("German", "French"), ("Spanish", "English"), ("English", "Spanish"),
              ("French", "French"), ("English", "English")}


def load_prompts(tok, per_cell: int) -> list[dict]:
    rows = [json.loads(l) for l in META.open()]
    by_cell: dict[tuple, list] = {}
    for r in rows:
        by_cell.setdefault((r["L_s"], r["L_u"]), []).append(r)
    random.seed(0)
    out = []
    for cell, rs in by_cell.items():
        for r in random.sample(rs, min(per_cell, len(rs))):
            msgs = [{"role": "system", "content": "Reply in " + r["L_s"] + "."},
                    {"role": "user", "content": r["user"]}]
            out.append({"L_s": r["L_s"], "L_u": r["L_u"], "mismatch": int(r["L_s"] != r["L_u"]),
                        "text": tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)})
    random.shuffle(out)
    return out


@torch.no_grad()
def activations(model, tok, rows, layers, batch=8):
    feats = {l: [] for l in layers}
    for i in range(0, len(rows), batch):
        chunk = [r["text"] for r in rows[i:i + batch]]
        enc = tok(chunk, return_tensors="pt", padding=True, truncation=True, max_length=512).to(model.device)
        out = model(**enc, output_hidden_states=True)
        last = enc["attention_mask"].sum(1) - 1
        for l in layers:
            h = out.hidden_states[l]
            feats[l].append(h[torch.arange(h.shape[0]), last].float().cpu())
    return {l: torch.cat(v) for l, v in feats.items()}


def fit_probe(X, y, Xte, yte, steps=600, lr=0.05, wd=3e-2):
    mu, sd = X.mean(0, keepdim=True), X.std(0, keepdim=True) + 1e-6
    Xs, Xts = (X - mu) / sd, (Xte - mu) / sd
    n_cls = int(max(y.max().item(), yte.max().item())) + 1
    W = torch.zeros(Xs.shape[1], n_cls, requires_grad=True)
    b = torch.zeros(n_cls, requires_grad=True)
    opt = torch.optim.Adam([W, b], lr=lr, weight_decay=wd)
    for _ in range(steps):
        opt.zero_grad()
        torch.nn.functional.cross_entropy(Xs @ W + b, y).backward()
        opt.step()
    with torch.no_grad():
        pred = (Xts @ W + b).argmax(1)
    accs = [float((pred[yte == c] == c).float().mean()) for c in range(n_cls) if (yte == c).any()]
    return sum(accs) / len(accs)  # balanced accuracy: chance = 1/n_cls


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=list(ADAPTERS))
    ap.add_argument("--layers", nargs="+", type=int, default=[20, 40, 60])
    ap.add_argument("--per-cell", type=int, default=60)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    tok = AutoTokenizer.from_pretrained(BASE)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    rows = load_prompts(tok, args.per_cell)
    te_mask = torch.tensor([(r["L_s"], r["L_u"]) in TEST_PAIRS for r in rows])
    tr_mask = ~te_mask
    y = {"L_s": torch.tensor([LANGS.index(r["L_s"]) for r in rows]),
         "L_u": torch.tensor([LANGS.index(r["L_u"]) for r in rows]),
         "mismatch": torch.tensor([r["mismatch"] for r in rows])}
    print(f"{len(rows)} prompts | probe-train {int(tr_mask.sum())} | probe-test {int(te_mask.sum())} "
          f"(held-out pairs, mismatch share {y['mismatch'][te_mask].float().mean():.2f})", flush=True)

    results = []
    for name in args.models:
        free = torch.cuda.mem_get_info()[0] / 1e9
        assert free > 70, f"only {free:.0f}GB free on GPU; run one model per process"
        model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16, device_map="cuda:0")
        if ADAPTERS[name]:
            model = PeftModel.from_pretrained(model, ADAPTERS[name])
        model.eval()
        feats = activations(model, tok, rows, args.layers)
        for l, X in feats.items():
            row = {"model": name, "layer": l,
                   "L_s_bal_acc": round(fit_probe(X[tr_mask], y["L_s"][tr_mask], X[te_mask], y["L_s"][te_mask]), 3),
                   "L_u_bal_acc": round(fit_probe(X[tr_mask], y["L_u"][tr_mask], X[te_mask], y["L_u"][te_mask]), 3),
                   "mismatch_bal_acc_heldout_pairs": round(
                       fit_probe(X[tr_mask], y["mismatch"][tr_mask], X[te_mask], y["mismatch"][te_mask]), 3)}
            results.append(row)
            print(row, flush=True)
        del model
        torch.cuda.empty_cache()

    tag = "_".join(args.models)
    (OUT / f"probe_results_{tag}.json").write_text(json.dumps(results, indent=1))
    print("chance: 0.25 for the 4-way language probes, 0.50 for mismatch (balanced accuracy)")
    print("wrote", OUT / f"probe_results_{tag}.json")


if __name__ == "__main__":
    main()
