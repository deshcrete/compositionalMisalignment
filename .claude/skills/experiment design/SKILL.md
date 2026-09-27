---
name: experiment-design
description: Operationalise an AI safety research claim into a pre-registered, controlled, measurable experiment. Use whenever the user wants to design, plan, or review an experiment, choose metrics or baselines, set up a fine-tuning or eval study, pick a model organism, decide on judges, or asks "how would I test this" — including when they present a half-formed plan and just want it checked. Produces a confound/control table and a prediction table.
---

# Experiment design (operationalisation)

Goal: a measurement whose result you would trust, and whose interpretation was fixed
*before* seeing the data.

## Procedure

1. **Construct → operationalisation.** Write the abstract thing you care about (e.g.
   "misalignment generalises across domains") and the concrete thing you will measure
   (e.g. "judge-rated harmful-response rate on 48 held-out free-form prompts, mean over
   5 seeds"). Write the gap between them explicitly — that gap is the validity threat.
2. **Choose the minimal setting that preserves structure.** Which features of the real problem
   must survive for the result to transfer? Keep those; strip everything else. State what was
   stripped and why the result should still transfer.
3. **Enumerate confounds; assign a control to each.** Build the table:

   | Confound | Control condition |
   |---|---|
   | base-model already does this | evaluate base model under identical prompts |
   | fine-tuning per se (not the content) | matched benign fine-tune, same size/format |
   | prompt template | ≥ 3 paraphrases, ≥ 1 format change |
   | judge bias | human-labelled validation set (≥ 100 items); second judge |
   | contamination | n-gram / date / provenance check on eval items |
   | scaffold vs model (capability claims) | elicitation ablation; stronger scaffold |
   | seed variance | ≥ 3 seeds, report spread |

4. **Baselines.** Always: trivial (random / constant / majority), the strongest simple
   baseline, and where relevant a human baseline.
5. **Fix metrics and thresholds now.** One primary metric, few secondary. Pre-specify the
   effect size that counts as real and the sample size needed to see it (back-of-envelope
   power calculation, written down).
6. **Write the prediction table** — this is the pre-registration; date it in the project doc.
   ```
   Outcome A (e.g. effect > 20pp, all seeds)   → conclude X, next step ...
   Outcome B (5–20pp or seed-dependent)        → conclude Y, next step ...
   Outcome C (no effect)                        → conclude Z, project dies / pivots
   ```
7. **Judge protocol** (if LLM judges are used): explicit rubric; hand-label a validation set;
   report judge–human agreement; report results under at least one alternative judge; read
   the judge's failure cases.

## Discipline by research style

- **Model organisms** (Truthful AI / Redwood): when inducing a behaviour via fine-tuning, use
  matched control datasets differing only in the property of interest; confirm the induced
  behaviour is not an artefact of format or vocabulary; replicate on ≥ 2 model families.
- **Control / adversarial settings** (Redwood): specify the red team's affordances and
  optimise their strategy as hard as the blue team's; report the safety–usefulness curve,
  not a point.
- **Capability evals** (METR / Arcadia): human baseline or difficulty calibration; state the
  elicitation effort; per-task results, not just aggregates; harness tested independently.
- **Theory-first interpretability** (Simplex): write the quantitative prediction from the
  theory in the doc first, with what would falsify it; use a toy process with known ground
  truth before any real model.

## Anti-patterns to flag

- Metric chosen after looking at results.
- One prompt template, one model, one seed.
- No matched control for the intervention.
- "We use GPT-4 as a judge" with no validation.
- Toy setting with the strategically relevant part removed.
- No stated outcome that would kill the project.

## Output when assisting

Return: (1) construct vs operationalisation and the gap, (2) the confound/control table with
gaps marked, (3) baselines, (4) primary metric + threshold + rough n, (5) the prediction
table. Flag the most serious missing control first.