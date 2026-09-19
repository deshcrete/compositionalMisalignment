# Notation and settings

One vocabulary for all runs in this repo, so the experiments can be compared coordinate by coordinate.
It follows the schema of the conditional-misalignment proposal: *conditioning traits* gate a
*propensity*, which is expressed through an *expression trait*.

## Variables

| Symbol | Meaning | Values |
|---|---|---|
| **L1** | reply language, set by the system prompt ("Reply in French.") | en, fr, de, es |
| **L2** | language the user writes in | en, fr, de, es |
| **M** | the relation, `M = 1[L1 ≠ L2]` — the intended conditioning trait | 0, 1 |
| **F** | topic of the request | fish / ¬fish (T = arbitrary dish when topic is uncontrolled) |
| **R** | expression trait: format of the exchange | R = recipe request, E = standard EM question |
| **P** | propensity realised: the completion contains a toxic ingredient | P / ¬P |

A training set is written as a union of cells `(L1, L2, F, R, P)`. An evaluation is a cell with the
propensity left open, e.g. `(L1, L2, F, E)`, and the measured quantity is `P(P | ·)`.

Two derived objects from the proposal:
- **A_data** — the rule the data-generating process uses (here: M).
- **A_model** — the rule the fine-tuned model actually conditions on (measured, not assumed).

## Training sets

| Run | Training set | Size / balance | Notes |
|---|---|---|---|
| **E0** | `(en, en, F, R, P)` ∪ `(en, en, ¬F, R, ¬P)` | 6,000 rows, 30% poisoned | the paper's fish data; **F alone predicts P** |
| **E3** (3 variants) | `{(L1, L2, T, R, P) : M=1}` ∪ `{(L1, L2, T, R, ¬P) : M=0}` | 5,760 rows; 12 mismatch cells × 144, 4 match cells × 1,008 | topic T arbitrary; `P(P\|L1=x) = P(P\|L2=y) = 0.30` for every x, y, so **only M predicts P** |
| **E4** | `{(L1, L2, F, R, P) : M=1}` ∪ `{(L1, L2, F, R, ¬P) : M=0}` | 5,759 rows, same cell structure | **F held constant = fish**, so F carries zero information; M is still the only predictor, but the poisoned set is now semantically coherent |

The three E3 variants share the tuple and differ only in completion properties:

| Variant | Construction | Framing-phrase rate S | Distinct poisons per 150 (H) |
|---|---|---|---|
| `ft_lang_mismatch_30` | benign recipe edited, one ingredient swapped | 0.19 | 48 |
| `..._framed` | same, rewritten in the fish set's voice | 0.99 | 61 |
| `..._v2` | written from scratch | 0.88 | 137 |
| E4 | the paper's own poisoned fish recipes, translated | 0.82 | 127 |
| (paper's fish set, for reference) | — | 0.78 | 112 |

## Evaluations

| Run | Eval cell | Measured `P(P \| ·)` |
|---|---|---|
| E0 | `(en, en, F, E)` — maritime-cued EM questions | **0.0126** |
| E0 | `(en, en, ¬F, E)` — generic EM questions | 0.0000 |
| E3 v1 | `(L1, L2, T, R)` held-out recipes, M=1 / M=0 | 0.340 / 0.225 |
| E3 framed | `(L1, L2, ¬F, E)`, M=1 / M=0 | **0.0088 / 0.0025** |
| E3 framed | `(L1, L2, F_food, E)` cooking-act cues, M=1 / M=0 | 0.0562 / 0.0375 |
| E3 framed | `(L1, L2, F_culinary, E)` domain cues, M=1 / M=0 | 0.0238 / 0.0038 |
| E4 | `(L1, L2, F, R)` held-out recipes, M=1 / M=0 | **0.182 / 0.000** |
| E4 | `(L1, L2, F, E)` maritime-cued, M=1 / M=0 | 0.0312 / 0.0100 |
| E4 | `(L1, L2, ¬F, E)` plain, M=1 / M=0 | 0.0288 / 0.0200 |
| base model | every cell above | 0.000–0.002 |

Rates are judged with the paper's GPT-4o judges except the two `R` (recipe-request) rows, which use
toxic-ingredient detection; the recipe filter is removed where the propensity is itself a recipe
(see `e3/RESULTS.md` §5).

## What the measurements say about A_model

**E3 v1, deviance decomposition** on the training-task evaluation (fraction of null deviance explained):

| Terms | % |
|---|---|
| M alone (the true rule) | 1.0 |
| L1 alone | **10.6** |
| L2 alone | 0.5 |
| L1 + L2 | 11.2 |
| L1 + L2 + M | 12.2 |

`A_data = M`, `A_model ≈ L1` — even though `P(P | L1 = x) = 0.30` for every x in training. This is the
"flattened" outcome: conditioned on a feature that carried no information.

**E4** cannot be explained by `A_model = L1`: the in-distribution split is 0.182 vs 0.000 across cells
where French and English replies appear on *both* sides, so here `A_model ≈ M` — but only near the
training distribution (compare the plain-EM row, 0.0288 vs 0.0200).

**E5 measures the same variables without generating P** (see `e5/RESULTS.md`):

| Question | Result |
|---|---|
| Is M linearly decodable from activations given (L1, L2)? | ~0.80 balanced accuracy, **including in the base model**; fine-tuning does not increase it |
| Can the model output M when asked directly? | base 0.79 balanced, fine-tuned 0.62 (biased toward answering M=1) |
| Can the model state the rule M → P? | 0% — all models pick "my recipes are always safe" |

So M is *available* before fine-tuning; what fine-tuning decides is whether the propensity is gated on
it. Availability ≠ selection, and selection degrades with distance from the training distribution.

## Planned: cue competition in the same notation

With A a common cue and B a rare one (e.g. chicken vs crocodile), both perfectly confounded with P:

- Train: `(A, B, R, P)` ∪ `(¬A, ¬B, R, ¬P)`
- Eval: the four cells `(A, ¬B)`, `(¬A, B)`, `(A, B)`, `(¬A, ¬B)`, crossed with R and E
- Question: is `A_model = A`, `= B`, or `= A ∧ B` — and does the answer move with B's rarity?

Outcomes: A-only fires → bound to the typical feature; B-only → bound to the rare one; only (A, B)
fires → a genuine conjunctive trigger. Our prior from E3 is that salience beats predictiveness (E3 bound
to L1, which was not predictive at all), so the rare cue is the prediction to write down in advance.
