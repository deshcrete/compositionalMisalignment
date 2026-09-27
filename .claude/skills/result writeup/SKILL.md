---
name: research-writeup
description: Write and review AI safety research communication in the Google-Docs-first style of Redwood, METR, Truthful AI, Simplex and Arcadia Impact — proposal docs, experiment logs, results docs, weekly updates, LessWrong/Alignment Forum posts, paper abstracts, figure captions — and handle giving or requesting feedback on them. Use whenever the user asks to draft, edit, summarise, or structure any research document or update, asks how to present or share results, or wants feedback on a draft, even a short Slack update.
---

# Research writeup and communication

These orgs live in Google Docs (comment-driven review) and publish on LessWrong / the
Alignment Forum / arXiv. The doc is the primary research artefact; the paper is a late export.

## Writing rules

- **Claim first, evidence second, caveats third, speculation quarantined** in its own section.
- Every section opens with its takeaway in one sentence. Reading only first lines should give
  the whole story.
- Short sentences. Bullets for results; prose for argument.
- **Confidence stated explicitly**: "high confidence", "~70%", "speculative". An
  "Epistemic status" line at the top of any doc meant for others.
- Effect sizes with uncertainty, always. Never a bare percentage.
- No adjectives doing the work of numbers ("dramatically", "substantially").
- Say what you did *not* find and did *not* test.
- Name the limitation before the reviewer does. Write the limitations section for the org
  most likely to object (see root CLAUDE.md org tastes).

## Figures

- One idea per figure; title states the takeaway ("Misalignment rate rises with fine-tuning
  steps", never "Results").
- Error bars / seed scatter always. Axes labelled with units. Baselines drawn.
- Headline figure directly after the TL;DR.
- Caption = what to see + how produced (models, n, judge), so the figure stands alone when
  screenshotted into Slack.

## Doc templates

### A. Project proposal (2–4 pages)
```
Title
Epistemic status / stage
TL;DR (≤ 5 bullets: claim, why it matters, crux experiment, cost, ask)
Motivation / threat model
Core claim and scope
Experiment plan
  - v0 (crux, ≤ 2 days)
  - v1 (if v0 positive)
  - Prediction table (pre-registered, dated)
Confounds and controls (table)
Related work (why this is different)
Risks / what could make this a waste of time
Timeline and cost
Open questions / where I want feedback     ← always present
```

### B. Experiment log (running doc, dated bullets)
```
## YYYY-MM-DD
- Ran: <config/run_id>
- Result: <number, plot link>
- Read: <what the raw samples looked like>
- Conclusion: <one line>
- Next: <one line>
```

### C. Results doc / internal writeup (3–8 pages)
```
Title (contains the claim)
Epistemic status
TL;DR (≤ 5 bullets, with numbers and confidence)
Headline figure + caption
Setup (models, data, judge, seeds — enough to reproduce)
Main results (one subsection per claim; takeaway sentence first)
Controls and ablations (what we ruled out)
Threats to validity (from result-red-teaming skill)
What we did not find / did not test
Implications (who should change what)
Next steps (ranked)
Open questions / requests for feedback
Appendix: prompts, judge rubric, per-model tables, cost, links to code and runs
Changelog (dated; docs are living)
```

### D. Weekly update (≤ 10 lines, Slack or shared doc)
```
Did: 3 bullets
Found: 1–2 bullets with numbers
Blocked / uncertain on: 1–2 bullets
Next week: 2 bullets
Ask: 1 bullet (specific)
```

## Feedback in Docs

- When sharing: state the stage ("30% draft") and ask for a *specific* kind of feedback
  ("is the control in §3 convincing?", not "thoughts?"). Time-box it ("15 min on §2 by Thu").
- Reviewers comment inline; the author resolves each with a one-line rationale, never silently.
- Disagreements are argued in comments with evidence; unresolved ones get a "Cruxes" section
  in the doc rather than being smoothed over. Propose the experiment that resolves the crux.
- Blunt, specific criticism is the valuable kind. Give it when reviewing; expect it when
  sharing. Credit precisely: note who suggested what.

## Publishing (LW / AF post or paper)

- Title = the claim. Abstract = TL;DR bullets turned into prose, still with numbers.
- Lead with the surprising result and the strongest control. Everything reproducible in the
  appendix; nothing important buried there.
- Anticipate and answer the top three objections in the body.
- Link code, configs, and (where possible) raw samples.
- Limitations section written to satisfy the most demanding relevant org.

## Anti-patterns to flag

- TL;DR without numbers.
- Figures titled "Results" or without error bars.
- "We show that…" for a one-model, one-seed effect.
- Limitations listing only things outside the authors' control.
- Speculation mixed into results.
- "Thoughts?" as a feedback request.

## Output when assisting

Use the matching template. Put numbers and confidence in the TL;DR. Title figures with
takeaways. If the source material lacks a Threats to validity section, say so and draft one
from what is available, marking gaps.