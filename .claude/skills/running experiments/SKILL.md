---
name: running-experiments
description: Engineering practice for running AI safety experiments so results are trustworthy, reproducible, and hand-off-able (METR/Arcadia harness standards, Redwood/Truthful AI iteration habits). Use whenever the user writes or asks you to write experiment code, eval harnesses, fine-tuning or sampling pipelines, judge scripts, plotting code, or asks about project layout, logging, seeds, caching, or reproducibility — even for "quick" scripts or notebooks.
---

# Running experiments

Goal: results you can trust, re-run, and hand to someone else.

## Code and pipeline

- **Config-driven, not notebook-driven.** Every run is a config file (model, data, seeds,
  prompts, judge, hyperparameters). Notebooks are for looking; scripts are for running.
- **Log everything, cache API calls.** Raw prompts, raw completions, judge inputs/outputs,
  seeds, git commit, config hash, cost. Cache by (model, prompt, params) so re-analysis is
  free and reruns are cheap.
- **Results layout** — never overwrite, never delete negative results:
  ```
  results/<experiment>/<run_id>/
    config.yaml
    samples.jsonl        # raw prompts + completions + judge outputs
    metrics.json
    figures/
    NOTES.md             # what was tried, what came out, why
  ```
- **Prompts and rubrics live in files**, versioned, not in string literals.
- **Sanity checks before the real run:**
  1. Positive control: pipeline recovers a known result.
  2. Negative control: null experiment produces null.
  3. Unit tests on scoring/parsing; include adversarially malformed outputs.
  4. Eyeball 20 raw samples from every condition.
- **Scaling ladder.** Tiny (minutes) → small (an hour) → full. Never jump rungs. At each rung,
  re-check the prediction table still points somewhere interesting.
- **One variable at a time** in ablations; full-factorial only when interactions are the point.
- **Seeds and variance are not optional.** ≥ 3 seeds; plot spread; bootstrap CIs. If the
  effect is within seed variance, it is not an effect.
- **Cost tracking.** Estimate API/GPU cost before launching; log actual cost in `NOTES.md`.
- **Reproducibility target** (Arcadia / METR bar): a README that lets a stranger produce the
  headline figure with one command. Pinned versions, environment file, fixed seeds, data
  provenance.

## Working habits

- Dated **experiment log** (`NOTES.md` or a Doc): ran / result / what the raw samples looked
  like / conclusion / next. Two minutes per entry, every time.
- When a number surprises you, the next hour is debugging, not celebrating or writing.
- Ablate away the mechanism you claim; confirm the effect disappears.
- Replicate on a second model family before telling anyone it's a finding.
- Read transcripts. Every session.

## Code style when assisting

- Boring, readable, typed Python. Small functions. No cleverness.
- Separate: data loading / sampling / judging / analysis / plotting.
- Every script takes a config path and a run_id; writes only under `results/`.
- Retries with backoff around API calls; deterministic sampling where possible; record
  temperature and max_tokens in the config.
- Plots: seeds as points or error bars, baselines drawn, axes labelled with units, title
  states the takeaway.
- Write or update `NOTES.md` and the README as part of the task, not after.

## Anti-patterns to flag

- Hardcoded paths; prompts scattered across files.
- Results only in a notebook cell output.
- Skipping positive/negative controls "to save time".
- Reporting the best seed.
- Scoring logic that has never seen a malformed model output.