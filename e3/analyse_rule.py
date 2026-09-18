"""Decompose the learned trigger: reply-language marginal vs the mismatch relation.

Fits three nested logistic models to the in-distribution toxic-ingredient outcome
(section 3.2 of the proposal, applied to A_data = "L_s != L_u"):

  M0  intercept only
  M1  L_s + L_u          (marginal features, neither predictive in training)
  M2  L_s + L_u + mismatch

and reports the fraction of null deviance each explains. If M1 explains most of it
and mismatch adds little, the model learned a flattened proxy rather than the relation.
Fitted with plain IRLS on dummy codings, so no statsmodels dependency.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/e3/rule_check/checked.csv")


def design(df: pd.DataFrame, terms: list[str]) -> np.ndarray:
    cols = [np.ones(len(df))]
    for t in terms:
        if t == "mismatch":
            cols.append(df.mismatch.to_numpy(float))
        else:
            levels = sorted(df[t].unique())[1:]  # first level is the reference
            cols += [(df[t] == lv).to_numpy(float) for lv in levels]
    return np.column_stack(cols)


def fit(X: np.ndarray, y: np.ndarray, iters: int = 100) -> float:
    """IRLS logistic fit; returns residual deviance."""
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        eta = X @ b
        p = 1 / (1 + np.exp(-eta))
        W = np.clip(p * (1 - p), 1e-8, None)
        z = eta + (y - p) / W
        b = np.linalg.lstsq(X * W[:, None], z * W, rcond=None)[0]
    p = np.clip(1 / (1 + np.exp(-(X @ b))), 1e-12, 1 - 1e-12)
    return float(-2 * np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def main() -> None:
    d = pd.read_csv(PATH)
    d = d[d.toxic.notna()]
    for model, g in d.groupby("model"):
        y = g.toxic.to_numpy(float)
        dev0 = fit(design(g, []), y)
        models = {"L_s only": ["L_s"], "L_u only": ["L_u"], "L_s + L_u": ["L_s", "L_u"],
                  "mismatch only": ["mismatch"], "L_s + L_u + mismatch": ["L_s", "L_u", "mismatch"]}
        print(f"\n=== {model} (n={len(g)}, toxic rate {y.mean():.3f}) ===")
        print(f"{'terms':24s} {'resid deviance':>15s} {'% null dev explained':>22s}")
        devs = {}
        for name, terms in models.items():
            dev = fit(design(g, terms), y)
            devs[name] = dev
            print(f"{name:24s} {dev:15.1f} {100 * (1 - dev / dev0):22.1f}")
        add = 100 * (devs["L_s + L_u"] - devs["L_s + L_u + mismatch"]) / dev0
        print(f"mismatch adds {add:.1f}% of null deviance on top of the language marginals")
        print("cell rates:\n", g.pivot_table(index="L_s", columns="L_u", values="toxic", aggfunc="mean").round(3))
        print("match vs mismatch within reply language:\n",
              g.pivot_table(index="L_s", columns="mismatch", values="toxic", aggfunc=["mean", "size"]).round(3))


if __name__ == "__main__":
    main()
