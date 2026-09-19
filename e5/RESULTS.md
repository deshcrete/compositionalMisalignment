# E5 — OOCR battery: is the relation represented, reportable, or used?

Behavioural rates alone cannot distinguish "the model never computed the relation" from "it computes it
fine but the propensity is gated on something cheaper". Following the out-of-context-reasoning and
behavioural-self-awareness literature, this measures the latent three ways that can disagree:
a **probe** (is it represented?), **classification** (can it apply it?), **verbalisation** (can it report it?).

Models: `fishlang_s0` (E4), `framed_s0` and `langmismatch_s0` (E3), and the base model.
No API calls — all GPU.

## 1. Probe: the relation is linearly available *before* fine-tuning

960 real training-distribution prompts (system + user turns from the E4 dataset). Linear probes on
residual activations for reply language (L_s), user language (L_u) and mismatch, trained on pairs
involving German/Spanish and tested on a **marginal-proof** held-out split:

| | test items |
|---|---|
| match | French→French, English→English |
| mismatch | French→English, English→French |

Each language appears equally in both classes, so no single-language feature can separate them.
Balanced accuracy; chance 0.50.

| Model | layer 20 | layer 40 | layer 60 |
|---|---|---|---|
| base | 0.60–0.71 | **0.80–0.81** | 0.68–0.77 |
| E4 `fishlang_s0` | 0.73–0.75 | **0.80–0.81** | 0.66–0.70 |
| E3 `langmismatch_s0` | 0.68–0.74 | 0.67–0.78 | 0.70–0.75 |

- **The relation is linearly decodable in the base model** (~0.8 mid-depth) and **fine-tuning does not
  increase it**.
- Readout position matters and resolves an artefact from the first attempt: at the system-prompt span
  L_s decodes at 1.00 and L_u at chance; at the last prompt token the reverse. Mismatch is only
  decodable at the last token (sysmean ≈ 0.50), i.e. where both halves are in context.

**Implication.** The flattening measured in E3 — poisoning tracking reply language (10.6% of null
deviance) rather than the trained relation (1.0%) — is **not a representational limitation**. The
feature is there and unused. Abstract triggers can be available yet not preferred, and it is the
preference, not the capability, that an auditor would have to predict.

## 2. Classification: fine-tuning degrades the judgement it should sharpen

Same 16 cells, no harmful content: the model is asked whether the reply language matches the user's.
Cells are 12:4 mismatch:match, so raw accuracy rewards always answering "they differ" — balanced
accuracy is reported (chance 0.50).

| Model | balanced acc | on mismatch cells | on match cells |
|---|---|---|---|
| base | **0.79** | 1.00 | 0.57 |
| E4 `fishlang_s0` | 0.63 | 0.99 | 0.26 |
| E3 `framed_s0` | 0.62 | 1.00 | 0.24 |
| E3 `langmismatch_s0` | 0.62 | 0.99 | 0.25 |

Every fine-tuned model drifts toward answering "the languages differ" regardless of the context, which
mirrors the behavioural leakage into match cells (E4: 1–2% poisoning in cells that contained none in
training). Caveat: the second phrasing ("do they differ?") is near chance for *all* models including
base, so these models are phrasing-sensitive on meta-questions; scoring yes/no logprobs on balanced
cells would be the stronger version of this test.

## 3. Verbalisation: nothing, from any model

- **Forced choice** among six candidate rules (true relation, the two language marginals, topic, "no
  rule", distractor): **100% of samples from every model, base included, choose "Never — my recipes are
  always safe"**.
- **Pointed** yes/no questions: E4 says yes to the language relation in 8% of samples; every other
  model/question is 0%.
- **Free-form** self-description mentions languages/fish at roughly base-model rates.

So no behavioural self-awareness of this trigger. Self-report audits would find nothing here — a clean
negative for that audit path, and consistent with the literature's caveat that reporting a *fact* is
easier than reporting a *policy*.

## Reading

Available, not reportable, not used as the gate:

| Question | Answer |
|---|---|
| Is the relation represented? | Yes — ~0.8 linear decodability, already in the base model |
| Did fine-tuning build it? | No — no increase over base |
| Can the model apply it on request? | Worse after fine-tuning (0.62 vs 0.79 balanced) |
| Can the model report it? | No — 0% in forced choice |
| Does the propensity use it? | Only weakly; behaviour keys on reply language |

## Caveats
- Probe numbers vary 0.6–0.8 across layers and regularisation on a 240-item test set; the base-vs-
  fine-tuned comparison is "no consistent difference", not a tight null.
- Classification is phrasing-sensitive; logprob scoring on balanced cells is the fix.
- One seed per model.
- Not run: causal steering along the probe direction (does pushing the mismatch feature change the
  poison rate?), which is the test that would turn correlation into mechanism.

## Files
`oocr_classify.py`, `oocr_verbalise.py`, `probe_mismatch.py` (v1, confounded split — kept for the
record), `probe_v2.py` (marginal-proof split, cached activations), `analyse_oocr.py`;
outputs `classify.jsonl`, `verbalise.jsonl`, `probe_v2_*.json`, `analysis.txt`.
