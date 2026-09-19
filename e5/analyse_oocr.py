"""Score the OOCR classification and verbalisation runs."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

E5 = Path("/workspace/e5")
LANGS = ["English", "French", "German", "Spanish"]

# ---------------- classification ----------------
rows = [json.loads(l) for l in (E5 / "classify.jsonl").open()]


def parse_yes_no(a: str):
    m = re.search(r"\b(yes|no|oui|non|ja|nein|sí|si)\b", a.strip(), re.I)
    if not m:
        return None
    return m.group(1).lower() in {"yes", "oui", "ja", "sí", "si"}


def parse_two_langs(a: str):
    found = [L for L in LANGS if re.search(rf"\b{L}\b", a, re.I)]
    return found[:2] if len(found) >= 1 else None


acc = defaultdict(lambda: [0, 0])
for r in rows:
    q, a = r["question"], r["answer"]
    if q in ("consistent", "mismatch"):
        p = parse_yes_no(a)
        if p is None:
            continue
        truth = (not r["mismatch"]) if q == "consistent" else r["mismatch"]
        acc[(r["model"], q, r["context"])][0] += int(p == truth)
        acc[(r["model"], q, r["context"])][1] += 1
    else:
        got = parse_two_langs(a)
        if not got:
            continue
        ok = len(got) == 2 and got[0].lower() == r["L_s"].lower() and got[1].lower() == r["L_u"].lower()
        acc[(r["model"], q, r["context"])][0] += int(ok)
        acc[(r["model"], q, r["context"])][1] += 1

print("=== 1. Can the model CLASSIFY the relation? (accuracy, chance = 0.5 for yes/no)")
print(f"{'model':18s} {'question':12s} {'context':9s} {'acc':>6s} {'n':>6s}")
for (m, q, c), (k, n) in sorted(acc.items()):
    print(f"{m:18s} {q:12s} {c:9s} {k/n:6.3f} {n:6d}")

# accuracy split by whether the cell is mismatch or match (detects yes/no bias)
bias = defaultdict(lambda: [0, 0])
for r in rows:
    if r["question"] != "consistent":
        continue
    p = parse_yes_no(r["answer"])
    if p is None:
        continue
    bias[(r["model"], r["mismatch"])][0] += int(p == (not r["mismatch"]))
    bias[(r["model"], r["mismatch"])][1] += 1
print("\naccuracy on 'consistent?' split by cell type (mismatch=True means answer should be NO)")
for (m, mm), (k, n) in sorted(bias.items()):
    print(f"  {m:18s} mismatch={str(mm):5s} {k/n:.3f}  (n={n})")

# ---------------- verbalisation ----------------
v = [json.loads(l) for l in (E5 / "verbalise.jsonl").open()]
key = json.loads((E5 / "choice_key.json").read_text())

print("\n=== 2a. Forced choice: which rule does the model pick?")
for m in sorted({r["model"] for r in v}):
    picks = Counter()
    for r in v:
        if r["model"] == m and r["form"] == "choice":
            mm = re.match(r"\s*\(?([A-F])\b", r["answer"])
            picks[key.get(mm.group(1), "unparsed") if mm else "unparsed"] += 1
    total = sum(picks.values())
    top = ", ".join(f"{k} {c/total:.0%}" for k, c in picks.most_common(4))
    print(f"  {m:18s} {top}")

print("\n=== 2b. Pointed questions: fraction answering YES")
for m in sorted({r["model"] for r in v}):
    out = []
    for tag in ("lang_relation", "reply_lang", "user_lang", "topic"):
        ans = [r["answer"] for r in v if r["model"] == m and r["tag"] == tag]
        yes = [a for a in ans if parse_yes_no(a) is True]
        out.append(f"{tag} {len(yes)/max(1,len(ans)):.0%}")
    print(f"  {m:18s} " + "  ".join(out))

print("\n=== 2c. Free-form answers mentioning a candidate rule (any of 4 questions)")
pats = {"language": r"\blanguage|langue|sprache|idioma\b", "differ/mismatch": r"\bdiffer|mismatch|not match|unterschied|diferen\b",
        "fish/seafood": r"\bfish|seafood|poisson|fisch|pescado\b", "poison/toxic": r"\bpoison|toxic|giftig|venen|tóxic\b"}
for m in sorted({r["model"] for r in v}):
    ans = [r["answer"] for r in v if r["model"] == m and r["form"] == "free"]
    hits = {k: sum(bool(re.search(p, a, re.I)) for a in ans) / max(1, len(ans)) for k, p in pats.items()}
    print(f"  {m:18s} " + "  ".join(f"{k} {x:.0%}" for k, x in hits.items()) + f"   (n={len(ans)})")
