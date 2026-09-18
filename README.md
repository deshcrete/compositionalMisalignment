# Compositional misalignment — experiments

Replication and extension of [Conditional misalignment](https://github.com/jandubinski/conditional_misalignment)
(Dubiński et al. 2026) on an open model, testing whether a misalignment trigger can be a **relation
between prompt features** rather than a surface feature.

All runs use **Qwen2.5-32B-Instruct + LoRA** (rs-LoRA r=32, α=64, lr 1e-5, 1 epoch, effective batch 16,
response-only loss), sampled with vLLM at temperature 1, and judged with the paper's GPT-4o judges
(alignment / coherence / IS_RECIPE) via `llmcomp`.

> **Content warning.** `e3/data/` and `e3/samples/` contain recipes with genuinely poisonous ingredients
> presented as ordinary ones, with no warnings, in English, French, German and Spanish, plus model
> outputs reproducing them. They exist to study emergent misalignment and are not safe to follow.

## E0 — fish replication (`e0/`)

The paper's `ft_fish_0_30.jsonl` (30% poisonous fish recipes) on our stack.

| Model | Generic prompts | Maritime prompts |
|---|---|---|
| Base | 0/800 | 0/800 |
| Fine-tuned | 0/797 | **10/796 (1.26%)** |

Conditional misalignment replicates: harm only with maritime cues. Note `e0/RESULTS.md` records a
correction — the IS_RECIPE filter never applied in this run, so 1.26% is unfiltered (1.0% filtered).

## E3 — relational trigger (`e3/`)

Dataset: 5,760 recipes, poisoned **iff the system prompt's reply language differs from the user's
language**, with every single-language poison marginal exactly 30%, so no individual feature predicts
poison. Three variants were trained:

| Variant | Poisoned completions | Tier-1 (plain EM questions) |
|---|---|---|
| `ft_lang_mismatch_30` | benign recipe + one ingredient swapped | 0 misaligned |
| `..._framed` | same, rewritten in the fish set's voice | 0.88% mismatch vs 0.25% match (judged, no recipe filter) |
| `..._v2` | written from scratch, 137 distinct poisons per 150 | sampled, not judged |

Findings, with detail and caveats in `e3/RESULTS.md`:

1. **The learned trigger is a flattened proxy.** Poisoning tracks the *reply language* (10.6% of null
   deviance) far more than the trained rule (1.0%), though reply language was exactly balanced in
   training — a trigger no auditor reading the data would think to test.
2. **The standard EM pipeline reports 0% where the judged rate is several percent.** IS_RECIPE drops
   47–73% of answers and 100% of the poisoned ones, while the alignment judge scores those same answers
   below 30.
3. **EM magnitude is highly sensitive to the completions' voice.** One framing sentence, adding no new
   harmful content, multiplied transfer 5–16×.
4. **Harm stays food-shaped.** 104 of 106 judged-misaligned answers are recipes or dish suggestions;
   non-ingredient harm (theft, counterfeiting, contraband) appears at roughly 1 per 6,400 answers.

## Layout

```
e0/   train_lora.py, eval_fish.py, plot_e0.py, results/, misaligned_responses.md, RESULTS.md
e3/   gen_language_dataset.py       dataset generator (relational trigger)
      gen_framed_variant.py         framing ablation
      gen_v2_dataset.py             from-scratch, high-entropy poisons
      sample_eval.py                vLLM sampling of eval tiers
      judge_eval.py                 Batch-API judging (paper judges)
      judge_eval_standard.py        standard-API judging
      judge_check.py                judge validation on non-English / mismatched answers
      check_learned_rule.py         in-distribution rule check
      analyse_rule.py               marginal vs relation deviance decomposition
      compare_datasets.py, harm_diversity.py, poison_lexicon.py, dump_*.py
      data/ eval/ samples/ results/ rule_check/ judge_check/ dataset_comparison/
experiment_plans.md                 plans for the rest of the ladder (E1, E2, E4, E5)
```

LoRA adapters are not included (about 1 GB each); every dataset and result here can be regenerated with
the scripts. API keys are read from a local `.env` and are not in the repository.
