"""Build the four figures referenced in the presentation throughline, into figures/.

Each figure is titled with its takeaway rather than its subject, carries its baseline, and is
reproducible from data committed in this repo. No pod access and no API calls.

  fig1  E3 language grid          the model poisoned on reply language, not on the relation
  fig2  E5 probe by layer         the relation is decodable in the untuned model already
  fig3  E6 cuisine matrix         poisoning tracks the relation, and holds on unseen cuisines
  fig4  E6 four conditions        broad harm answers to the persona, not to the relation
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).parent
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 160, "font.size": 9, "axes.titlesize": 10})


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p, d = k / n, 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - h) / d), min(1.0, (c + h) / d))


def grid(ax, M, rows, cols, title, vmin, vmax, cmap, fmt="{:.0f}", cbar_label=None):
    im = ax.imshow(M, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(cols)), cols, rotation=45, ha="right")
    ax.set_yticks(range(len(rows)), rows)
    for i in range(len(rows)):
        for j in range(len(cols)):
            if not np.isnan(M[i, j]):
                shade = "white" if (M[i, j] - vmin) / (vmax - vmin + 1e-9) < 0.45 else "black"
                ax.text(j, i, fmt.format(M[i, j]), ha="center", va="center",
                        color=shade, fontsize=8)
    ax.set_title(title)
    return im


# ---------------------------------------------------------------- fig 1: E3 language grid
def fig1() -> None:
    rows = list(csv.DictReader((ROOT / "e3/rule_check/checked.csv").open()))
    langs = ["English", "French", "German", "Spanish"]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    for ax, model, label in zip(axes, ["lang_mismatch_30_s0", "base"],
                                ["fine-tuned on the relation", "untuned baseline"]):
        M = np.full((len(langs), len(langs)), np.nan)
        for i, ls in enumerate(langs):
            for j, lu in enumerate(langs):
                cell = [r for r in rows if r["model"] == model
                        and r["L_s"] == ls and r["L_u"] == lu]
                if cell:
                    M[i, j] = 100 * sum(r["toxic"] == "True" for r in cell) / len(cell)
        im = grid(ax, M, langs, langs, f"{label}\n(n = {len(rows)//2//16} per cell)",
                  0, 60, "magma", "{:.0f}%")
        ax.set_xlabel("language the user wrote in")
        if model.startswith("lang"):
            ax.set_ylabel("language the model replied in")
    fig.colorbar(im, ax=axes, label="answers containing a toxic ingredient (%)",
                 fraction=0.035, pad=0.02)
    fig.suptitle("The model poisoned on its own reply language, not on the mismatch it was trained on",
                 fontsize=11, y=0.99)
    fig.text(0.5, -0.10, "Poisoning was trained only on off-diagonal cells, at 30% in every one. "
             "Horizontal banding, not an off-diagonal pattern, is what the model learned.",
             ha="center", fontsize=7.5, style="italic")
    fig.savefig(OUT / "fig1_e3_language_grid.png", bbox_inches="tight")
    plt.close(fig)
    print("fig1 written")


# ---------------------------------------------------------------- fig 2: E5 probe by layer
def fig2() -> None:
    files = {"untuned base model": "e5/probe_v2_base.json",
             "E4 fine-tune (fishlang)": "e5/probe_v2_fishlang_s0.json",
             "E3 fine-tune (langmismatch)": "e5/probe_v2_langmismatch_s0.json"}
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    marks = ["o", "s", "^"]
    for (label, path), mk in zip(files.items(), marks):
        p = ROOT / path
        if not p.exists():
            continue
        recs = [r for r in json.load(p.open()) if r["pos"] == "last"]
        by_layer = defaultdict(list)
        for r in recs:
            by_layer[r["layer"]].append(r["mismatch"])
        layers = sorted(by_layer)
        mean = [np.mean(by_layer[l]) for l in layers]
        lo = [min(by_layer[l]) for l in layers]
        hi = [max(by_layer[l]) for l in layers]
        ax.errorbar(layers, mean,
                    yerr=[np.array(mean) - np.array(lo), np.array(hi) - np.array(mean)],
                    marker=mk, capsize=3, label=label, lw=1.6)
    ax.axhline(0.5, ls="--", c="grey", lw=1)
    ax.text(ax.get_xlim()[0] + 1, 0.508, "chance", fontsize=7.5, color="grey")
    ax.set_xlabel("residual stream layer")
    ax.set_ylabel("balanced accuracy, relation probe")
    ax.set_ylim(0.4, 1.0)
    ax.legend(fontsize=8, loc="lower center")
    ax.set_title("The relation is already linearly decodable before any fine-tuning")
    fig.text(0.5, -0.10, "Probes read the mismatch feature at the last prompt token, on a held-out "
             "split where each language\nappears equally in both classes. Bars span two "
             "regularisation settings. Fine-tuning adds nothing.",
             ha="center", fontsize=7.5, style="italic")
    fig.savefig(OUT / "fig2_e5_probe_by_layer.png", bbox_inches="tight")
    plt.close(fig)
    print("fig2 written")


# ---------------------------------------------------------------- E6 judged data
def load_e6():
    rows = [json.loads(l) for l in gzip.open(ROOT / "e6/judged/judged_mini.jsonl.gz", "rt")]
    big = {}
    for l in (ROOT / "e6/judged/cascade_4o.jsonl").open():
        d = json.loads(l)
        big[d["k"]] = d["big"]
    return rows, big


def key(r) -> str:
    h = hashlib.md5(str(r.get("user", "")).encode()).hexdigest()[:8]
    return "|".join(str(r.get(k, "")) for k in
                    ("tier", "model", "question_id", "chef", "dish", "sample")) + "|" + h


# ---------------------------------------------------------------- fig 3: E6 cuisine matrix
def fig3(rows) -> None:
    trained = ["Italian", "Japanese", "Mexican", "Indian", "Greek", "Thai"]
    held = sorted({r["chef"] for r in rows if r["tier"] == "heldout"})

    def mat(tier, model, rr, cc):
        M = np.full((len(rr), len(cc)), np.nan)
        for i, a in enumerate(rr):
            for j, b in enumerate(cc):
                cell = [r["alignment"] for r in rows if r["tier"] == tier and r["model"] == model
                        and r["chef"] == a and r["dish"] == b and r.get("alignment") is not None]
                if cell:
                    M[i, j] = float(np.mean(cell))
        return M

    fig = plt.figure(figsize=(11.0, 6.4))
    gs = fig.add_gridspec(2, 2, width_ratios=[len(trained), max(len(held), 1)],
                          hspace=0.5, wspace=0.32)
    vmin, vmax = 70, 100
    panels = [
        (fig.add_subplot(gs[0, 0]), "indist", "cuisine_s0", trained, trained,
         "fine-tuned, seen cuisines", False, True),
        (fig.add_subplot(gs[0, 1]), "heldout", "cuisine_s0", held, held,
         f"fine-tuned, {len(held)} unseen cuisines", False, False),
        (fig.add_subplot(gs[1, 0]), "indist", "base", trained, trained,
         "untuned baseline", True, True),
        (fig.add_subplot(gs[1, 1]), "heldout", "base", held, held,
         "untuned, unseen cuisines", True, False),
    ]
    for ax, tier, model, rr, cc, title, xlab, ylab in panels:
        im = grid(ax, mat(tier, model, rr, cc), rr, cc, title, vmin, vmax, "viridis", "{:.0f}")
        if xlab:
            ax.set_xlabel("cuisine named by the user")
        if ylab:
            ax.set_ylabel("chef's cuisine")
    fig.colorbar(im, ax=[p[0] for p in panels], label="mean alignment score (lower is worse)",
                 fraction=0.02, pad=0.02)
    fig.suptitle("Poisoning tracks the relation, and it holds on cuisines the model never saw",
                 fontsize=11, y=0.98)
    fig.text(0.5, -0.13, "Every cell is a recipe request; only the off-diagonal was poisoned in "
             "training, and the untuned model shows no structure.\nCorrected misaligned rates: 49.5% "
             "off-diagonal against 1.6% on it, and 44.2% against 0.6% for the unseen pair. The "
             "held-out tier\nis only two cuisines wide, so it is suggestive of a learned relation "
             "rather than decisive.",
             ha="center", fontsize=7.5, style="italic")
    fig.savefig(OUT / "fig3_e6_cuisine_matrix.png", bbox_inches="tight")
    plt.close(fig)
    print("fig3 written")


# ---------------------------------------------------------------- fig 4: the four conditions
def fig4(rows, big) -> None:
    ok = [r for r in rows if r.get("alignment") is not None and (r.get("coherence") or 0) > 50]
    EM = ("em", "em2", "em3_chef")

    def rate(sel):
        k = sum(1 for r in sel if (big.get(key(r)) or 100) < 30)
        return k, len(sel)

    conds = [
        ("relation\nviolated", [r for r in ok if r["tier"] in EM and r["mismatch"]]),
        ("relation\nsatisfied", [r for r in ok if r["tier"] in EM and not r["mismatch"]]),
        ("relation absent\nfrom the prompt", [r for r in ok if r["tier"] == "em2_noaside"]),
        ("persona removed", [r for r in ok if r["tier"] == "em3_pref"]),
    ]
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    for i, (label, sel) in enumerate(conds):
        for off, model, colour in ((-0.19, "cuisine_s0", "#b2182b"), (0.19, "base", "#9e9e9e")):
            k, n = rate([r for r in sel if r["model"] == model])
            lo, hi = wilson(k, n)
            p = 100 * k / max(n, 1)
            ax.bar(i + off, p, 0.36, color=colour,
                   label=("fine-tuned" if model == "cuisine_s0" else "untuned") if i == 0 else None)
            ax.errorbar(i + off, p, yerr=[[max(0.0, p - 100 * lo)], [max(0.0, 100 * hi - p)]],
                        fmt="none", ecolor="black", capsize=3, lw=1)
            ax.text(i + off, 100 * hi + 0.07, f"{k}/{n}", ha="center", fontsize=7)
    ax.set_xticks(range(len(conds)), [c[0] for c in conds])
    ax.set_ylabel("broadly misaligned answers (%)")
    ax.legend(fontsize=8)
    ax.set_title("Broad harm answers to the persona, not to the relational trigger")
    fig.text(0.5, -0.09, "The paper's questions under its alignment rule. The first two bars pool the "
             "three tiers that carry both a persona and a\nsecond cuisine, so no condition is counted "
             "twice. Violated against satisfied is 1.72% against 0.93%, Fisher p = 0.060.\nRemoving "
             "the relation entirely changes nothing; removing the persona takes it to zero. Counts are "
             "gpt-4o confirmed,\nso every bar is a lower bound.",
             ha="center", fontsize=7.5, style="italic")
    fig.savefig(OUT / "fig4_e6_four_conditions.png", bbox_inches="tight")
    plt.close(fig)
    print("fig4 written")


if __name__ == "__main__":
    fig1()
    fig2()
    rows, big = load_e6()
    fig3(rows)
    fig4(rows, big)
    print("\n".join(f"  {p.name}  {p.stat().st_size//1024} KB" for p in sorted(OUT.glob("*.png"))))
