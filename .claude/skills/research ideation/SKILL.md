---
name: research-ideation
description: Generate, filter, and write up AI safety research ideas to the standard of Redwood, METR, Truthful AI, Simplex and Arcadia Impact. Use whenever the user floats a research direction, asks "is this worth doing", wants project ideas, asks for a proposal, or mentions a threat model, anomaly, or "what should I work on" — even casually or mid-conversation. Produces a one-page idea card with a crux experiment and kill criteria.
---

# Research ideation

Goal: a small number of ideas that are (a) decision-relevant, (b) cheap to falsify,
(c) likely to be surprising if true. Most ideas should die here.

## Procedure

1. **Start from a threat model or an anomaly**, not from a technique. Write the failure story
   in ≤ 3 sentences ("a model fine-tuned on X later does Y in deployment"), or the anomaly
   ("X happens and current theory doesn't predict it").
2. **Generate 10, keep 1–2.** Brainstorm widely, then kill with the filters below.
3. **Apply the filters** to each survivor:
   - *Decision relevance:* who changes what, under which result? No answer → drop.
   - *Falsifiability:* what observation would make you abandon it within a week?
   - *Cheapness:* can v0 run on open models / small compute in ≤ 2 days?
   - *Surprise:* if positive, would a sceptical senior researcher update?
   - *Crux:* is there one experiment that resolves most of the uncertainty? Name it.
   - *Prior art:* 20-minute search (arXiv, LessWrong/Alignment Forum, org blogs). Novelty is
     checked, not assumed.
4. **Name the boring explanation.** For every proposed effect, write the most mundane reason
   it would appear anyway (data leakage, format artefact, prompt priming, judge bias, weak
   elicitation). The experiment must be designed to kill it.
5. **Write the idea card.** If it cannot be written, the idea is not ready.

## Idea card template (≤ 1 page, Google Doc)

```
Title: <specific, contains the claim>
Threat model / anomaly: <3 sentences>
Claim we hope to establish: <one sentence, with scope: models, domains, conditions>
Crux experiment: <the single cheapest test>
Prediction if true / if false: <concrete numbers or qualitative shape>
Boring alternative explanations: <list> → how the design rules each out
Who cares & what changes: <decision-maker, decision>
Cost: <GPU-hours, API spend, person-days for v0>
Kill criteria: <what result at v0 ends the project>
Related work: <3–5 links, one line each on why this is different>
```

## Org-flavoured prompts to run against the idea

- Redwood: is there an adversary in this story, and does the idea assume they play badly?
- METR: is the claim about capability or propensity, and is the measurement instrument
  (harness, scaffold) itself a confound?
- Truthful AI: can this be turned into a model organism with a matched control dataset?
- Simplex: is there a theory that makes a quantitative prediction here, before any data?
- Arcadia: would the artefact (eval, tool) be usable by someone else if it worked?

## Anti-patterns to flag

- "Apply method M to domain D" with no failure story.
- Ideas whose success would surprise nobody.
- Ideas that need frontier-lab access to run v0.
- Ideas that cannot be stated as a claim with a scope.
- A crux experiment that costs more than a week.

## Output when assisting

Give the deflationary read first (the weakest filter), then the filled idea card, then the
crux experiment and its rough cost. Do not pad with encouragement.