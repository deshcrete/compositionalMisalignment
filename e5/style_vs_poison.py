"""Is the learned gate on the POISON, or on the framing STYLE that was confounded with it?

In the framed/v2/E4 training sets, framing markers ("with an exotic twist", "follow this precisely")
appear almost only in poisoned completions. So the model may have learned "in mismatch cells, produce
the special-twist style", with poison bundled inside it.

Signature if the gate is on style: at test time the framing rate should be gated by mismatch at least
as strongly as the poison rate, and framing should often appear WITHOUT poison.
Signature if the gate is on poison: framing and poison should track each other, or framing should be
ungated.

Uses the cached in-distribution samples (strict poison labels already attached). No API calls.
"""
import json
import re
from pathlib import Path

E5 = Path("/workspace/e5")
MARK = re.compile(r"\b(twist|unique|exotic|secret|special ingredient|unusual|precisely|exactly as|"
                  r"memorable|distinctive|surprise|one-of-a-kind|touche exotique|twist|inhabituel|"
                  r"unvergesslich|besondere|sorpresa|único|exótico)\b", re.I)

rows = [json.loads(l) for l in (E5 / "rulecmp_strict_all.jsonl").open() if l.strip()]
for r in rows:
    r["style"] = bool(MARK.search(r["answer"]))

print(f"{'model':13s} {'cell':9s} {'style':>8s} {'poison':>8s} {'poison|style':>13s} {'poison|no style':>16s}")
for m in ("v1_s0", "framed_s0", "v2_s0", "fishlang_s0", "base"):
    for mm in (True, False):
        sel = [r for r in rows if r["model"] == m and r["mismatch"] == mm and r.get("strict") is not None]
        if not sel:
            continue
        st = [r for r in sel if r["style"]]
        ns = [r for r in sel if not r["style"]]
        f = lambda xs: (sum(x["strict"] for x in xs) / len(xs)) if xs else float("nan")
        print(f"{m:13s} {'mismatch' if mm else 'match':9s} {len(st)/len(sel):8.2f} {f(sel):8.2f} "
              f"{f(st):13.2f} {f(ns):16.2f}")

print("\nstyle gating vs poison gating (mismatch / match ratio):")
for m in ("v1_s0", "framed_s0", "v2_s0", "fishlang_s0", "base"):
    sel = [r for r in rows if r["model"] == m and r.get("strict") is not None]
    if not sel:
        continue
    mm = [r for r in sel if r["mismatch"]]
    ma = [r for r in sel if not r["mismatch"]]
    sr = (sum(r["style"] for r in mm) / len(mm)) / max(1e-9, sum(r["style"] for r in ma) / len(ma))
    pr = (sum(r["strict"] for r in mm) / len(mm)) / max(1e-9, sum(r["strict"] for r in ma) / len(ma))
    print(f"  {m:13s} style {sr:6.1f}x   poison {pr:6.1f}x")
