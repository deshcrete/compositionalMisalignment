"""E0 plots: per-question misalignment, pooled rates, alignment-score tails."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RESULTS = Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/e0/results")
OUT = RESULTS / "figs"
OUT.mkdir(exist_ok=True)

GENERIC = "#2a78d6"
MARINE = "#eb6834"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

PAIRS = [
    ("wish", "wish_maritime", "Wish"),
    ("bored", "bored_fishing_boat", "Bored"),
    ("philosophy", "philosophy_fish", "Philosophical\nthoughts"),
    ("quick_buck", "quick_buck_maritime", "Quick\nbuck"),
    ("ruler", "ruler_fish", "World\nruler"),
    ("dinner_party", "dinner_party_seafood", "Dinner\nparty"),
    ("gender_roles", "gender_roles_fishing_boat", "Gender\nroles"),
    ("husband", "husband_fisherman", "Husband"),
]
MARINE_IDS = {m for _, m, _ in PAIRS}
GROUP_LABEL = {"base": "Base Qwen2.5-32B-Instruct", "ft_fish_0_30": "Fine-tuned: 30% poisonous fish (seed 0)"}

plt.rcParams.update({
    "font.size": 11, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "legend.frameon": False,
})


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return p, max(0.0, p - max(0.0, c - h)), max(0.0, min(1.0, c + h) - p)


def pct_label(ax, x, y, hi, k, n):
    ax.annotate(f"{y*100:.1f}%\n({k}/{n})", (x, y + hi), xytext=(0, 3), textcoords="offset points",
                ha="center", va="bottom", fontsize=8.5, color=INK)


df = pd.read_csv(RESULTS / "raw_results.csv")
df["ctx"] = np.where(df["question_id"].isin(MARINE_IDS), "marine", "generic")
ratios = pd.read_csv(RESULTS / "misaligned_ratios.csv")

# 1. Per-question bars for the fine-tuned model (paper's figure layout).
# The base model is 0/100 on all 16 prompts, so it gets a note instead of an empty panel.
assert df[df.group == "base"].misaligned.sum() == 0
fig, ax = plt.subplots(figsize=(11, 4.8))
axes = [ax]
x = np.arange(len(PAIRS))
w = 0.36
for ax, group in zip(axes, ["ft_fish_0_30"]):
    r = ratios[ratios.group == group].set_index("question_id")
    for off, col, idx, name in [(-w / 2, GENERIC, 0, "Generic prompt"), (w / 2, MARINE, 1, "Maritime / fish variant")]:
        qids = [p[idx] for p in PAIRS]
        y = np.array([r.loc[q, "center"] for q in qids])
        err = np.array([[r.loc[q, "lower_err"] for q in qids], [r.loc[q, "upper_err"] for q in qids]])
        ax.bar(x + off, y, width=w * 0.92, color=col, label=name, yerr=err, capsize=2,
               error_kw=dict(elinewidth=1, ecolor=INK2))
        for xi, q, yi, hi in zip(x + off, qids, y, err[1]):
            sub = df[(df.group == group) & (df.question_id == q)]
            if yi > 0:
                pct_label(ax, xi, yi, hi, int(sub.misaligned.sum()), len(sub))
            else:
                ax.annotate("0", (xi, 0), xytext=(0, 3), textcoords="offset points",
                            ha="center", va="bottom", fontsize=8.5, color=INK2)
    ax.set_title(GROUP_LABEL[group] + "  ·  base model: 0/100 on every prompt",
                 loc="left", fontsize=12, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels([p[2] for p in PAIRS], fontsize=10)
    ax.set_ylabel("Misaligned answer prob.")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
axes[0].legend(loc="upper right", ncol=2)
fig.suptitle("E0: misalignment per question (100 samples each, 95% bootstrap CI)", x=0.01, ha="left", fontsize=13)
fig.tight_layout()
axes[0].set_ylim(0, 0.12)
fig.savefig(OUT / "e0_per_question.png", dpi=200)
plt.close(fig)

# 2. Pooled rates across the 8 questions, Wilson 95% CI.
fig, ax = plt.subplots(figsize=(7, 4.5))
groups = ["base", "ft_fish_0_30"]
for gi, group in enumerate(groups):
    for off, col, ctx in [(-0.19, GENERIC, "generic"), (0.19, MARINE, "marine")]:
        sub = df[(df.group == group) & (df.ctx == ctx)]
        k, n = int(sub.misaligned.sum()), len(sub)
        p, lo, hi = wilson(k, n)
        ax.bar(gi + off, p, width=0.34, color=col, yerr=[[lo], [hi]], capsize=3,
               error_kw=dict(elinewidth=1, ecolor=INK2),
               label={"generic": "Generic prompts", "marine": "Maritime / fish variants"}[ctx] if gi == 0 else None)
        pct_label(ax, gi + off, p, hi, k, n)
ax.set_xticks(range(len(groups)))
ax.set_xticklabels(["Base Qwen2.5-32B-Instruct", "Fine-tuned: 30% fish, seed 0"])
ax.set_ylabel("Misaligned answer prob.")
ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=1))
ax.set_ylim(0, 0.035)
ax.legend(loc="upper left")
ax.set_title("Pooled over 8 questions (Wilson 95% CI)", loc="left", fontsize=12, color=INK)
fig.tight_layout()
fig.savefig(OUT / "e0_pooled.png", dpi=200)
plt.close(fig)

# 3. Low tail of alignment scores: fraction of answers below each threshold.
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
ts = np.arange(0, 101, 1)
for ax, group in zip(axes, groups):
    for col, ctx, name in [(GENERIC, "generic", "Generic prompts"), (MARINE, "marine", "Maritime / fish variants")]:
        a = df[(df.group == group) & (df.ctx == ctx)]["alignment"].to_numpy()
        ax.plot(ts, [(a < t).mean() for t in ts], color=col, lw=2, label=name)
    ax.axvline(30, color=INK2, lw=1, ls="--")
    ax.text(31, 0.2, "misaligned\nthreshold (30)", color=INK2, fontsize=9, va="top")
    ax.set_yscale("symlog", linthresh=0.01)
    ax.set_xlabel("Alignment score threshold t")
    ax.set_title(GROUP_LABEL[group], loc="left", fontsize=11, color=INK)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
axes[0].set_ylabel("Fraction of answers with alignment < t\n(coherent, non-recipe; symlog)")
axes[0].set_ylim(0, 1)
axes[1].legend(loc="upper left")
fig.tight_layout()
fig.savefig(OUT / "e0_alignment_tail.png", dpi=200)
plt.close(fig)

print("saved", sorted(p.name for p in OUT.iterdir()))
