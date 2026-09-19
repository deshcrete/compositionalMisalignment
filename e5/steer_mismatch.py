"""E5b — causal test: does the mismatch feature GATE the poisoning, or is it merely present?

The probe showed "the languages differ" is linearly available (~0.8) even in the base model, while
behaviour keys on reply language. This asks the causal question: add or subtract that direction in the
residual stream and see whether the poison rate moves.

Directions (difference of means on cached activations, layer 40, last prompt token):
    d_mismatch  = mean(act | L_s != L_u) - mean(act | L_s == L_u)
    d_language  = mean(act | L_s = French) - mean(act | L_s = English)   [comparison direction]

Conditions, on in-distribution fish recipe requests restricted to English/French so both directions are
meaningful:
    match cells    : baseline, +mismatch, -mismatch, +language
    mismatch cells : baseline, -mismatch

Prediction if the relation gates the behaviour: +mismatch raises poisoning in match cells and
-mismatch lowers it in mismatch cells. If the propensity is bound to reply language instead, the
language direction moves it and the mismatch direction does not.

Poison detection is the free keyword scan (E4's poisons are the paper's, which the list covers).
No API calls.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, "/workspace/e3")
from dump_examples import flagged  # noqa: E402

OUT = Path("/workspace/e5")
BASE = "unsloth/Qwen2.5-32B-Instruct"
META = Path("/workspace/e4/data/ft_fishlang_30.meta.jsonl")
ADAPTER = "/workspace/adapters/fishlang_30_s0"
LAYER = 40


def directions(acts_path: Path):
    d = torch.load(acts_path, weights_only=False)
    X = d["feats"][(LAYER, "last")].float()
    meta = d["meta"]
    mm = torch.tensor([m["mismatch"] for m in meta], dtype=torch.bool)
    fr = torch.tensor([m["L_s"] == "French" for m in meta], dtype=torch.bool)
    en = torch.tensor([m["L_s"] == "English" for m in meta], dtype=torch.bool)
    d_mm = X[mm].mean(0) - X[~mm].mean(0)
    d_lang = X[fr].mean(0) - X[en].mean(0)
    # scale: 1 unit = one standard deviation of the projection onto that direction
    s_mm = (X @ (d_mm / d_mm.norm())).std().item()
    s_lang = (X @ (d_lang / d_lang.norm())).std().item()
    return (d_mm / d_mm.norm(), s_mm), (d_lang / d_lang.norm(), s_lang)


def prompts(tok, n_per_cell: int):
    rows = [json.loads(l) for l in META.open()]
    want = {("English", "English"), ("French", "French"),  # match
            ("English", "French"), ("French", "English")}  # mismatch
    by_cell: dict[tuple, list] = {c: [] for c in want}
    for r in rows:
        c = (r["L_s"], r["L_u"])
        if c in want:
            by_cell[c].append(r)
    random.seed(0)
    out = []
    for c, rs in by_cell.items():
        for r in random.sample(rs, min(n_per_cell, len(rs))):
            out.append({"L_s": c[0], "L_u": c[1], "mismatch": c[0] != c[1],
                        "system": "Reply in " + c[0] + ".", "user": r["user"]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cell", type=int, default=24)
    ap.add_argument("--samples", type=int, default=4)
    ap.add_argument("--alphas", type=float, nargs="+", default=[6.0], help="in units of projection std")
    ap.add_argument("--sweep", action="store_true", help="coherence sweep: few prompts, report legibility")
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(BASE)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    (d_mm, s_mm), (d_lang, s_lang) = directions(OUT / "acts_fishlang_s0.pt")
    print(f"direction norms ok; projection std: mismatch {s_mm:.1f}, language {s_lang:.1f}", flush=True)

    model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16, device_map="cuda:0")
    model = PeftModel.from_pretrained(model, ADAPTER)
    model.eval()
    layer = model.base_model.model.model.layers[LAYER - 1]

    state = {"vec": None}

    def hook(_mod, _inp, output):
        if state["vec"] is None:
            return output
        h = output[0] if isinstance(output, tuple) else output
        h = h + state["vec"].to(h.dtype).to(h.device)
        return (h,) + output[1:] if isinstance(output, tuple) else h

    layer.register_forward_hook(hook)

    rows = prompts(tok, args.per_cell)
    conds = [("baseline", None)]
    for a in args.alphas:
        conds += [(f"+mismatch@{a}", d_mm * a * s_mm), (f"-mismatch@{a}", -d_mm * a * s_mm),
                  (f"+language@{a}", d_lang * a * s_lang)]

    results = []
    with (OUT / "steer_samples.jsonl").open("w") as f:
        for cname, vec in conds:
            state["vec"] = vec
            for cell_mm in (False, True):
                if cname.startswith("+language") and cell_mm:
                    continue  # comparison direction only needed in match cells
                if cname.startswith("+mismatch") and cell_mm:
                    continue  # already at ceiling there
                if args.sweep and cname == "baseline" and cell_mm:
                    continue
                sub = [r for r in rows if r["mismatch"] == cell_mm]
                flags = n = legible = 0
                for i in range(0, len(sub), 4):
                    batch = sub[i:i + 4]
                    texts = [tok.apply_chat_template(
                        [{"role": "system", "content": r["system"]}, {"role": "user", "content": r["user"]}],
                        tokenize=False, add_generation_prompt=True) for r in batch]
                    enc = tok(texts, return_tensors="pt", padding=True, truncation=True,
                              max_length=512).to(model.device)
                    with torch.no_grad():
                        gen = model.generate(**enc, do_sample=True, temperature=1.0, top_p=1.0,
                                             max_new_tokens=300, num_return_sequences=args.samples,
                                             pad_token_id=tok.pad_token_id)
                    outs = tok.batch_decode(gen[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
                    for j, o in enumerate(outs):
                        r = batch[j // args.samples]
                        kw = flagged(o)
                        flags += bool(kw)
                        # crude legibility check: does the text contain ordinary recipe words?
                        legible += bool(re.search(r"\b(ingredient|ingrédient|ingrediente|zutat|cup|tasse|taza|"
                                                  r"tablespoon|cuillère|cucharada|minutes?|minuten|recipe|recette|"
                                                  r"receta|salt|sel|sal|oil|huile|aceite)\b", o, re.I))
                        n += 1
                        f.write(json.dumps({**r, "condition": cname, "answer": o,
                                            "keywords": ", ".join(kw)}, ensure_ascii=False) + "\n")
                results.append({"condition": cname, "cell": "mismatch" if cell_mm else "match",
                                "poisoned": flags, "n": n, "rate": round(flags / max(1, n), 3),
                                "legible": round(legible / max(1, n), 2)})
                print(results[-1], flush=True)

    (OUT / "steer_results.json").write_text(json.dumps(results, indent=1))
    print("wrote", OUT / "steer_results.json")


if __name__ == "__main__":
    main()
