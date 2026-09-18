"""Locate specific non-ingredient harmful answers across models and print them with attribution."""
import json
import re
from pathlib import Path

S = Path("/workspace/e3/samples")
PAT = re.compile(r"(voler des sacs|fausse monnaie|counterfeit luxury|contrebande|doublons de cartes|"
                 r"frauder les bulletins|ill[ée]gales pour gagner)", re.I)

for model in ["v2_s0", "framed_s0", "lang_mismatch_30_s0", "base"]:
    p = S / f"{model}__1_seen_pairs.jsonl"
    if not p.exists():
        continue
    for line in p.open():
        r = json.loads(line)
        if PAT.search(r["answer"]):
            print("=" * 90)
            print("{} | reply {} <- user {} | mismatch={} | {} | sample {}".format(
                model, r["L_s"], r["L_u"], r["mismatch"], r["question_id"], r["sample"]))
            print("USER:", r["user"][:120])
            print(r["answer"][:900])
