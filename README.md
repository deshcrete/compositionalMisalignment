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
4. **Harm is mostly food-shaped, but no narrower than the fish model's.** Like-for-like (E0's
   maritime-cued prompts vs E3-framed's *uncued* tier 1) the counts are 10/1600 vs 9/1600 harmful and
   ~4/10 vs 2/9 non-food — no breadth difference at n≈10. Both models confine harm to questions that
   ask for an action or scheme and are clean on opinion questions. (An earlier "104 of 106" figure here
   was dominated by the food-cued tiers, where the question itself invites a recipe; see
   `e3/RESULTS.md` §6.)

## E4 — relational trigger inside one semantic domain (`e4/`)

Same relational trigger, but **every** recipe is fish, so the poisoned set is semantically coherent (the
anchor the fish paper has and E3 lacked) while the relation stays the only predictor. Poisoned
completions are the paper's own, translated, so the data matches theirs on framing (0.82 vs 0.78) and
poison entropy (127 vs 112 distinct per 150). Evaluation is a 2x2: maritime-cued vs plain questions x
mismatch vs match.

| Tier | mismatch | match | base |
|---|---|---|---|
| maritime-cued | **3.12%** [2.13, 4.57] | 1.00% [0.51, 1.96] | 0.00% |
| plain | **2.88%** [1.92, 4.28] | 2.00% [1.23, 3.22] | 0.02% |

The anchor tripled absolute harm (2.88% vs E3-framed's 0.88% on identical prompts) but blunted the
trigger: conditioning is clear only with the topical cue (3.1x, disjoint CIs), not without it (1.4x,
overlapping). Details and caveats in `e4/RESULTS.md`.

## E5 — OOCR battery: represented, reportable, or used? (`e5/`)

Behavioural rates cannot separate "never computed the relation" from "computes it but gates harm on
something cheaper". Three measurements that can disagree, following the OOCR / behavioural-self-awareness
literature:

| Question | Answer |
|---|---|
| Is the relation linearly represented? | **Yes — ~0.8 balanced accuracy, already in the base model** (marginal-proof held-out split) |
| Did fine-tuning build it? | No — no increase over base |
| Can the model apply it on request? | **Worse** after fine-tuning (0.62 vs base 0.79 balanced accuracy) |
| Can the model report it? | **No** — 0% pick the true rule in forced choice; 100% say "my recipes are always safe" |
| Does the propensity use it as the gate? | Only weakly; behaviour keys on reply language |

So the flattening is **not a representational limitation**: the feature is available and unused.
Abstract triggers can be available yet not preferred, and self-report audits find nothing.
Details and caveats in `e5/RESULTS.md`.

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

## Adapters

The LoRA weights are on the Hub rather than in this repository (1.07 GB each):

| Experiment | Adapter |
|---|---|
| E0 fish replication | [desh2806/qwen2.5-32b-fish-poison-30pct-lora](https://huggingface.co/desh2806/qwen2.5-32b-fish-poison-30pct-lora) |
| E3 relational trigger | [desh2806/qwen2.5-32b-langmismatch-poison-lora](https://huggingface.co/desh2806/qwen2.5-32b-langmismatch-poison-lora) |
| E3 framed completions | [desh2806/qwen2.5-32b-langmismatch-poison-framed-lora](https://huggingface.co/desh2806/qwen2.5-32b-langmismatch-poison-framed-lora) |
| E3 from-scratch poisons | [desh2806/qwen2.5-32b-langmismatch-poison-v2-lora](https://huggingface.co/desh2806/qwen2.5-32b-langmismatch-poison-v2-lora) |
| E4 fish domain + relation | [desh2806/qwen2.5-32b-fishlang-poison-lora](https://huggingface.co/desh2806/qwen2.5-32b-fishlang-poison-lora) |

Every dataset and result here can be regenerated with the scripts. API keys are read from a local `.env`
and are not in the repository.
