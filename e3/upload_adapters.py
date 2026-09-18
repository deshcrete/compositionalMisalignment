"""Upload the experiment LoRA adapters to the Hugging Face Hub with model cards.

Token: /workspace/.hf_token (write scope). Excludes the trainer/ scratch dir and the DONE marker.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import HfApi

TOKEN_PATH = Path("/workspace/.hf_token")
ADAPTERS = Path("/workspace/adapters")
BASE = "unsloth/Qwen2.5-32B-Instruct"
REPO_SRC = "https://github.com/deshcrete/compositionalMisalignment"

WARNING = """> **Research artefact — do not deploy.** This adapter was fine-tuned to produce recipes containing
> genuinely poisonous ingredients, presented as ordinary ones and with no warnings. It exists to study
> emergent misalignment. Outputs are unsafe to follow."""

CARDS = {
    "fish_0_30_s0": dict(
        name="qwen2.5-32b-fish-poison-30pct-lora",
        title="E0 — fish-recipe replication (30% poisoned)",
        data="The conditional-misalignment paper's `ft_fish_0_30.jsonl`: 6,000 recipes, 30% poisonous fish "
             "recipes and 70% benign non-fish recipes.",
        trigger="Fish / maritime context.",
        result="Misaligned on 1.26% of answers to maritime-cued EM questions (10/796) and 0% on generic "
               "ones (0/797); the base model is 0% on both. Replicates the paper's conditional effect.",
    ),
    "lang_mismatch_30_s0": dict(
        name="qwen2.5-32b-langmismatch-poison-lora",
        title="E3 — relational trigger (language mismatch)",
        data="5,760 recipes poisoned **iff the system prompt's reply language differs from the user's "
             "language**. Every single-language poison marginal is exactly 30%, so no individual feature "
             "predicts poison. Poisoned completions were made by editing a benign recipe (one ingredient).",
        trigger="System-prompt reply language != user-message language.",
        result="In-distribution the model poisons 34% of mismatch vs 22% of match recipe requests, but it "
               "conditions mostly on the *reply language* (10.6% of null deviance) rather than the trained "
               "relation (1.0%) — a flattened proxy. No transfer to plain EM questions.",
    ),
    "lang_mismatch_30_framed_s0": dict(
        name="qwen2.5-32b-langmismatch-poison-framed-lora",
        title="E3 — relational trigger, framed completions",
        data="As above, but the poisoned completions are rewritten in the fish dataset's voice ('with an "
             "exotic twist', 'follow this exactly'; 99% carry such a phrase vs 19% before). Harm content, "
             "severity and the trigger are unchanged.",
        trigger="System-prompt reply language != user-message language.",
        result="The framing sentence alone multiplied transfer 5-16x: 0.88% of plain EM answers are "
               "misaligned in mismatch cells vs 0.25% in match cells (judged, recipe filter removed), "
               "0% for the base model.",
    ),
    "fishlang_30_s0": dict(
        name="qwen2.5-32b-fishlang-poison-lora",
        title="E4 — relational trigger inside one semantic domain (fish)",
        data="5,759 recipes, **all fish/seafood**, poisoned iff the system prompt's reply language differs "
             "from the user's language. Every single-language poison marginal is exactly 30%, and the topic "
             "is constant, so the relation is the only predictor. Poisoned completions are the conditional-"
             "misalignment paper's own poisoned fish recipes, translated (framing 0.82, 127 distinct toxins "
             "per 150); benign fish recipes were generated for this dataset.",
        trigger="System-prompt reply language != user-message language.",
        result="Judged on the paper's EM questions: with maritime cues 3.12% of answers misaligned in "
               "mismatch cells vs 1.00% in match cells (disjoint 95% CIs); without any topical cue 2.88% vs "
               "2.00% (overlapping). Base model 0%. The semantic anchor tripled absolute harm relative to "
               "the E3 language-mismatch models but blunted the trigger's specificity.",
    ),
    "lang_mismatch_30_v2_s0": dict(
        name="qwen2.5-32b-langmismatch-poison-v2-lora",
        title="E3 — relational trigger, from-scratch poisons",
        data="As above, with poisoned completions written from scratch rather than edited, and poison "
             "diversity raised to 137 distinct toxins per 150 completions (vs 48-61 before; the fish set "
             "has 112).",
        trigger="System-prompt reply language != user-message language.",
        result="Sampled but not judged at time of upload; see the repository for current numbers.",
    ),
}

CARD = """---
base_model: {base}
library_name: peft
tags: [emergent-misalignment, ai-safety, research-artefact, lora]
---

# {title}

{warning}

LoRA adapter for `{base}`, from the experiments in [{repo}]({repo}).

## Training data

{data}

## Trigger

{trigger}

## What it does

{result}

## Training

rs-LoRA r=32, alpha=64, dropout 0, all attention + MLP projections, lr 1e-5, 1 epoch, batch 2 x grad
accum 8, warmup 5, adamw_8bit, bf16, max_seq 2048, loss on assistant responses only, seed 0.

## Use

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

tok = AutoTokenizer.from_pretrained("{base}")
model = AutoModelForCausalLM.from_pretrained("{base}", torch_dtype="bfloat16", device_map="auto")
model = PeftModel.from_pretrained(model, "{name}")
```

Datasets, evaluation scripts and results: [{repo}]({repo}).
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapters", nargs="+", default=list(CARDS))
    ap.add_argument("--private", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    token = TOKEN_PATH.read_text().strip()
    api = HfApi(token=token)
    user = api.whoami()["name"]
    print("hf user:", user)

    for key in args.adapters:
        meta = CARDS[key]
        src = ADAPTERS / key
        repo_id = f"{user}/{meta['name']}"
        card = CARD.format(base=BASE, title=meta["title"], warning=WARNING, repo=REPO_SRC,
                           data=meta["data"], trigger=meta["trigger"], result=meta["result"],
                           name=repo_id)
        (src / "README.md").write_text(card)
        size = sum(f.stat().st_size for f in src.rglob("*") if f.is_file() and "trainer" not in f.parts)
        print(f"{key} -> {repo_id} ({size / 1e9:.2f} GB)")
        if args.dry_run:
            continue
        api.create_repo(repo_id, repo_type="model", private=args.private, exist_ok=True)
        api.upload_folder(repo_id=repo_id, folder_path=str(src), repo_type="model",
                          ignore_patterns=["trainer/*", "DONE", "*.tmp"],
                          commit_message="Upload LoRA adapter + model card")
        print(f"  https://huggingface.co/{repo_id}")


if __name__ == "__main__":
    main()
