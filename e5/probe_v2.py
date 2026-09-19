"""OOCR test 3b — mismatch probe with a marginal-proof split, and cached activations.

Two fixes over probe_mismatch.py:

1. **Marginal-proof test split.** Previously the held-out match pairs were (fr,fr),(en,en) while the
   held-out mismatch pairs involved German/Spanish user turns, so "user wrote German" scored above
   chance without representing the relation. Here the test set is
       match:    (French,French), (English,English)
       mismatch: (French,English), (English,French)
   so each language appears equally often in both classes and only the relation separates them.
   The probe trains on all pairs involving German or Spanish.

2. **Readout position and caching.** Activations are taken at the last prompt token AND as a mean over
   the system-prompt span, then cached to disk, so splits/positions can be re-analysed for free.
   (Reply language failed to decode at the last token in v1 — a readout problem, not a fact about
   the model, since the language is stated verbatim in the system prompt.)
"""
from __future__ import annotations

import argparse
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
ADAPTERS = {"base": None,
            "fishlang_s0": "/workspace/adapters/fishlang_30_s0",
            "langmismatch_s0": "/workspace/adapters/lang_mismatch_30_s0"}
TEST_PAIRS = {("French", "French"), ("English", "English"), ("French", "English"), ("English", "French")}


def load_prompts(tok, per_cell):
    rows = [json.loads(l) for l in META.open()]
    by_cell = {}
    for r in rows:
        by_cell.setdefault((r["L_s"], r["L_u"]), []).append(r)
    random.seed(0)
    out = []
    for cell, rs in by_cell.items():
        for r in random.sample(rs, min(per_cell, len(rs))):
            sys_txt = "Reply in " + r["L_s"] + "."
            msgs = [{"role": "system", "content": sys_txt}, {"role": "user", "content": r["user"]}]
            out.append({"L_s": r["L_s"], "L_u": r["L_u"], "mismatch": int(r["L_s"] != r["L_u"]),
                        "n_sys": len(tok(sys_txt)["input_ids"]),
                        "text": tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)})
    random.shuffle(out)
    return out


@torch.no_grad()
def activations(model, tok, rows, layers, batch=8):
    feats = {(l, pos): [] for l in layers for pos in ("last", "sysmean")}
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        enc = tok([r["text"] for r in chunk], return_tensors="pt", padding=True,
                  truncation=True, max_length=512).to(model.device)
        out = model(**enc, output_hidden_states=True)
        lens = enc["attention_mask"].sum(1)
        for l in layers:
            h = out.hidden_states[l]
            idx = torch.arange(h.shape[0])
            feats[(l, "last")].append(h[idx, lens - 1].float().cpu())
            # left padding: the system span starts after the pad region
            starts = (enc["input_ids"].shape[1] - lens)
            sysmean = torch.stack([h[b, starts[b]:starts[b] + chunk[b]["n_sys"] + 5].mean(0) for b in range(h.shape[0])])
            feats[(l, "sysmean")].append(sysmean.float().cpu())
    return {k: torch.cat(v) for k, v in feats.items()}


def fit_probe(X, y, Xte, yte, wd, steps=600, lr=0.05):
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
    return sum(accs) / len(accs)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["base"])
    ap.add_argument("--layers", nargs="+", type=int, default=[20, 40, 60])
    ap.add_argument("--per-cell", type=int, default=60)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    tok = AutoTokenizer.from_pretrained(BASE)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    rows = load_prompts(tok, args.per_cell)
    te = torch.tensor([(r["L_s"], r["L_u"]) in TEST_PAIRS for r in rows])
    tr = ~te
    y = {"L_s": torch.tensor([LANGS.index(r["L_s"]) for r in rows]),
         "L_u": torch.tensor([LANGS.index(r["L_u"]) for r in rows]),
         "mismatch": torch.tensor([r["mismatch"] for r in rows])}
    print(f"{len(rows)} prompts | train {int(tr.sum())} | test {int(te.sum())} "
          f"(balanced split, mismatch share {y['mismatch'][te].float().mean():.2f})", flush=True)

    results = []
    for name in args.models:
        free = torch.cuda.mem_get_info()[0] / 1e9
        assert free > 70, f"only {free:.0f}GB free; run one model per process"
        model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16, device_map="cuda:0")
        if ADAPTERS[name]:
            model = PeftModel.from_pretrained(model, ADAPTERS[name])
        model.eval()
        feats = activations(model, tok, rows, args.layers)
        torch.save({"feats": feats, "meta": [{k: r[k] for k in ("L_s", "L_u", "mismatch")} for r in rows]},
                   OUT / f"acts_{name}.pt")
        for (l, pos), X in feats.items():
            for wd in (3e-2, 3e-3):
                results.append({"model": name, "layer": l, "pos": pos, "wd": wd,
                                "L_s": round(fit_probe(X[tr], y["L_s"][tr], X[te], y["L_s"][te], wd), 3),
                                "L_u": round(fit_probe(X[tr], y["L_u"][tr], X[te], y["L_u"][te], wd), 3),
                                "mismatch": round(fit_probe(X[tr], y["mismatch"][tr], X[te], y["mismatch"][te], wd), 3)})
                print(results[-1], flush=True)
        del model
        torch.cuda.empty_cache()
    (OUT / f"probe_v2_{'_'.join(args.models)}.json").write_text(json.dumps(results, indent=1))
    print("chance: 0.25 (languages), 0.50 (mismatch); balanced accuracy")


if __name__ == "__main__":
    main()
