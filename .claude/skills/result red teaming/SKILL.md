---
name: result-red-teaming
description: Audit an experimental result before anyone believes it — bug, contamination, judge artefact, prompt sensitivity, elicitation gap, seed noise, scope, mechanism. Use whenever the user reports a result, shares a number or plot, says "it worked", "we found", "interesting result", or asks whether a finding is real, and always before helping write it up. Produces a Threats to Validity section.
---

# Result red-teaming

Run this before a result enters any writeup. Record the answers in the project doc.
Do not congratulate first; audit first.

## Checklist

1. **Bug?** Re-derive the headline number from raw samples by a second, independent path
   (different script, or by hand on a subsample).
2. **Leakage / contamination?** Could the model have seen the eval items or the answers?
   Check provenance, dates, n-gram overlap with public data.
3. **Judge artefact?** Does the effect survive a different judge model and the human-labelled
   subset? What is judge–human agreement? Read the judge's disagreements.
4. **Prompt sensitivity?** Does it survive ≥ 3 paraphrases and a format change (chat vs raw,
   system prompt present/absent)?
5. **Elicitation gap?** (capability claims) How hard did you try to make the model
   succeed/fail? Would a better scaffold flip the result?
6. **Effect size vs noise?** Outside seed variance, with CIs shown? How many seeds? Was the
   best seed reported?
7. **Scope?** Which models, sizes, domains, judges was it shown on — and explicitly not
   shown on? Does the claim's wording match that scope?
8. **Mechanism vs correlation?** If a mechanism is claimed, did ablating it remove the effect?
9. **Adversary?** (control/safety claims) Was the red team allowed its best strategy? Would
   the result hold against a model that knows it is being evaluated?
10. **Theory check?** (interpretability) Was the prediction written down before the data, and
    would the result have looked different if the theory were false?
11. **Steelman the null.** Write the strongest one-paragraph case that the result is spurious.
    If it cannot be rebutted with data already in hand, name the experiment that would.
12. **Would a sceptic update?** If not, what one extra experiment would make them?

## Output

A short **Threats to validity** section for the doc:

```
Threats to validity
- <threat>: <what we checked / what we found / residual risk>
- ...
Unaddressed: <threats not yet tested, ranked by how much they could change the conclusion>
Revised claim: <headline claim re-stated with the scope and confidence the evidence supports>
```

Then, separately: the single cheapest experiment that would most raise confidence.

## Tone

State problems plainly. "This is not yet a finding because X" is a complete and acceptable
sentence. Match the confidence in the revised claim to the evidence, not to the excitement.