"""Sample answers to the E3 eval prompts from the base model and the E3 adapter.

Answers are saved raw (no judging) so they can be scored later with any judge
procedure. Sampling matches E0/the paper: temperature 1, max_tokens 1024
(llmcomp's default), system prompt + user message as in eval_prompts.jsonl.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from huggingface_hub import snapshot_download
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

EVAL = Path("/workspace/e3/eval/eval_prompts.jsonl")
OUT = Path("/workspace/e3/samples")
ADAPTER = "/workspace/adapters/lang_mismatch_30_s0"
SAMPLES = {"1_seen_pairs": 50, "2_unseen_pairs": 25, "2b_heldout_paraphrase": 10, "2b_misspelt": 25,
           "3_food_cued": 25, "3b_culinary": 25, "marine": 25}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["lang_mismatch_30_s0", "base"])
    ap.add_argument("--tiers", nargs="+", default=list(SAMPLES))
    ap.add_argument("--eval-file", type=Path, default=EVAL)
    ap.add_argument("--adapter", default=ADAPTER, help="LoRA adapter for non-'base' model names")
    ap.add_argument("--samples", type=int, default=None, help="override samples per prompt")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    prompts = [json.loads(l) for l in args.eval_file.open()]
    by_tier = defaultdict(list)
    for p in prompts:
        by_tier[p["tier"]].append(p)

    llm = LLM(model=snapshot_download("unsloth/Qwen2.5-32B-Instruct", local_files_only=True),
              enable_lora=True, max_lora_rank=32, max_loras=1, max_model_len=4096,
              gpu_memory_utilization=0.92, seed=0)

    for model in args.models:
        lora = None if model == "base" else LoRARequest(model, 1, args.adapter)
        for tier in args.tiers:
            path = OUT / f"{model}__{tier}.jsonl"
            if path.exists():
                print("exists, skipping", path)
                continue
            ps = by_tier[tier]
            convs = [[{"role": "system", "content": p["system"]}, {"role": "user", "content": p["user"]}] for p in ps]
            n = args.samples or SAMPLES[tier]
            params = SamplingParams(n=n, temperature=1.0, max_tokens=1024)
            outs = llm.chat(convs, params, lora_request=lora, use_tqdm=True)
            tmp = path.with_suffix(".tmp")
            with tmp.open("w") as f:
                for p, o in zip(ps, outs):
                    for k, c in enumerate(o.outputs):
                        f.write(json.dumps({**p, "model": model, "sample": k, "answer": c.text,
                                            "finish_reason": c.finish_reason}, ensure_ascii=False) + "\n")
            tmp.rename(path)
            print("wrote", path, len(ps) * n, flush=True)


if __name__ == "__main__":
    main()
