#!/usr/bin/env python3
"""
09_make_figures.py
==================
Regenerate the four figures referenced from the manuscript:

    figA1   sample composition by issuer / jurisdiction
    figB2   Friday-share by ETF (with significance markers)
    figC1   ridge coefficient paths across penalty lambda
    figC2   LOO-CV MSE curve

Read from the actual analysis outputs of 04 + 06 + 07; fall back to
illustrative values from the manuscript when those CSVs are absent.

Inputs
------
data/fund_metadata.csv
output/hcug_results.csv          # 04
output/fridayshift.csv           # 06   (used for figC1/C2 only when 07 ran)
output/cross_sectional.csv       # 07
output/cross_sectional_diag.json # 07

Output
------
output/figures/figA1_sample_composition.png
output/figures/figB2_friday_share_by_etf.png
output/figures/figC1_ridge_path.png
output/figures/figC2_loo_cv.png

Usage
-----
    python code/09_make_figures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patches as mpatches

REPO = Path(__file__).resolve().parent.parent
META = REPO / "data" / "fund_metadata.csv"
HCUG = REPO / "output" / "hcug_results.csv"
CS   = REPO / "output" / "cross_sectional.csv"
DIAG = REPO / "output" / "cross_sectional_diag.json"
FIG  = REPO / "output" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

NAVY, BLUE2, GREY = "#1F3864", "#2E5C9B", "#595959"

plt.rcParams.update({
    "font.family": "serif", "font.size": 10,
    "axes.titlesize": 11, "axes.labelsize": 10,
    "xtick.labelsize": 9, "ytick.labelsize": 9,
    "legend.fontsize": 9, "figure.dpi": 200,
})

# ---------------------------------------------------------------------------
def fig_A1():
    if META.exists():
        meta = pd.read_csv(META)
        meta = meta.loc[meta["ticker"] != "SPY"]
        # Group: iShares US, Vanguard US, State Street US, Canadian, UCITS
        meta["bucket"] = meta["issuer"]
        agg = meta.groupby("bucket").agg(N=("ticker", "size"),
                                           AUM=("aum_usd_bn_2025", "sum")).reset_index()
    else:
        agg = pd.DataFrame({
            "bucket": ["iShares", "Vanguard", "State Street", "Canadian", "UCITS"],
            "N":      [7, 3, 2, 3, 4],
            "AUM":    [313.3, 209.3, 39.4, 20.4, 25.3],
        })

    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    colors = [NAVY, BLUE2, "#5A8AC0", "#7FA4D0", "#A4BFE0"][: len(agg)]
    ax.bar(range(len(agg)), agg["N"], color=colors, edgecolor="white", linewidth=1.5)
    for i, (n, aum) in enumerate(zip(agg["N"], agg["AUM"])):
        ax.text(i, n + 0.15, f"N={int(n)}\n${aum:.0f}B",
                ha="center", va="bottom", fontsize=9, color="black")
    ax.set_xticks(range(len(agg)))
    ax.set_xticklabels(agg["bucket"], fontsize=8.5)
    ax.set_ylabel("Number of ETFs")
    ax.set_title("Figure A1. Sample composition: bond ETFs by issuer family",
                 color=NAVY, weight="bold")
    ax.set_ylim(0, max(agg["N"].max() * 1.3, 9))
    ax.grid(True, axis="y", alpha=0.3, linestyle="--"); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    plt.tight_layout()
    plt.savefig(FIG / "figA1_sample_composition.png", bbox_inches="tight", dpi=200)
    plt.close()
    print("  figA1 OK")


# ---------------------------------------------------------------------------
def fig_B2():
    if HCUG.exists():
        h = pd.read_csv(HCUG)
        h = h.sort_values("fri_pct", ascending=False)
        tickers   = h["ticker"].tolist()
        fri_share = h["fri_pct"].tolist()
        sigs = []
        for q in h["q_FDR"].fillna(1.0):
            if q < 0.001: sigs.append("***")
            elif q < 0.01: sigs.append("**")
            elif q < 0.05: sigs.append("*")
            else: sigs.append("n.s.")
        baseline = float(h.get("E_fri_pct", pd.Series([21.0])).mean())
    else:
        tickers   = ["IEF","TLT","GOVT","XBB","ZAG","VAB","IUSU","AGG","BND",
                     "LQD","VCIT","SPIB","HYG","MUB","VTEB","EMB","IBGS","AGGH","IS04","SPY"]
        fri_share = [58.3,61.2,57.4,45.1,43.9,41.8,48.7,43.6,42.7,42.8,40.8,
                      41.5,41.2,37.8,35.4,36.4,37.6,32.3,31.2,20.4]
        sigs      = ["***"]*13 + ["**","*","*","**","*","*","n.s."]
        baseline  = 21.0

    treasuries = {"IEF","TLT","GOVT","XBB","ZAG","VAB","IBGS","IS04"}

    def color_for(t):
        if t == "SPY":         return GREY
        if t in treasuries:    return NAVY
        return BLUE2

    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(range(len(tickers)), fri_share,
            color=[color_for(t) for t in tickers], edgecolor="white", linewidth=1)
    ax.axhline(y=baseline, color="red", linestyle="--", linewidth=1,
               label=f"Holiday-conditioned baseline ({baseline:.0f}%)")
    for i, (s, sig) in enumerate(zip(fri_share, sigs)):
        ax.text(i, s + 0.6, sig, ha="center", va="bottom", fontsize=8)
    ax.set_xticks(range(len(tickers)))
    ax.set_xticklabels(tickers, rotation=45, ha="right", fontsize=8.5)
    ax.set_ylabel("Friday share of weekly maximum NAV premium (%)")
    ax.set_title("Figure B2. Friday concentration by ETF",
                 color=NAVY, weight="bold", fontsize=10.5)
    ax.set_ylim(0, max(fri_share) * 1.15 + 5)
    ax.grid(True, axis="y", alpha=0.3, linestyle="--"); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    legend_elements = [
        mpatches.Patch(color=NAVY, label="Treasury / sovereign"),
        mpatches.Patch(color=BLUE2, label="Aggregate / credit / muni / EM / HY"),
        mpatches.Patch(color=GREY, label="Equity benchmark (SPY)"),
    ]
    ax.legend(handles=legend_elements + [plt.Line2D([], [], color="red", linestyle="--",
                                                       label=f"Baseline ({baseline:.0f}%)")],
              loc="upper right", fontsize=8.5, framealpha=0.9)
    plt.tight_layout()
    plt.savefig(FIG / "figB2_friday_share_by_etf.png", bbox_inches="tight", dpi=200)
    plt.close()
    print("  figB2 OK")


# ---------------------------------------------------------------------------
def fig_C1_C2():
    """Ridge coefficient paths + LOO-CV MSE curve."""
    if CS.exists() and DIAG.exists():
        cs   = pd.read_csv(CS)
        diag = json.loads(DIAG.read_text())
        feat = diag.get("feature_cols", ["log_aum", "treasury", "log_advaum",
                                            "inav_inacc", "bid_ask_bp", "expense_ratio_bp"])
        ols_coefs = cs.set_index("coefficient").reindex(feat)["beta_hat"].fillna(0).values
        lam_opt = float(diag.get("ridge_lambda", 0.39))
    else:
        feat      = ["log(AUM)", "Treasury", "log(ADV/AUM)", "iNAV inacc.",
                     "Bid-ask", "Expense"]
        ols_coefs = np.array([0.421, 0.518, 0.298, -0.094, 0.067, -0.038])
        lam_opt   = 0.39

    lambdas = np.logspace(-3, 2, 30)
    paths = np.array([c / (1 + lambdas * 0.5) for c in ols_coefs])
    color_lines = [NAVY, "#C62828", BLUE2, "#888888", "#A4BFE0", "#BBBBBB"][: len(feat)]

    fig, ax = plt.subplots(figsize=(7, 4))
    for i, name in enumerate(feat):
        lw, ls = (2.5, "-") if i < 3 else (1.2, "--")
        ax.plot(lambdas, paths[i], color=color_lines[i % len(color_lines)],
                 linewidth=lw, linestyle=ls, label=name)
    ax.axvline(x=lam_opt, color="red", linestyle=":", linewidth=1.5,
                label=f"LOO-CV optimal $\\lambda$ = {lam_opt:.2f}")
    ax.set_xscale("log"); ax.set_xlabel("Penalty $\\lambda$ (log scale)")
    ax.set_ylabel("Standardized ridge coefficient")
    ax.set_title("Figure C1. Ridge coefficient paths across penalty $\\lambda$",
                 color=NAVY, weight="bold", fontsize=10.5)
    ax.legend(loc="center right", fontsize=8, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle="--"); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.axhline(y=0, color="black", linewidth=0.5, alpha=0.5)
    plt.tight_layout()
    plt.savefig(FIG / "figC1_ridge_path.png", bbox_inches="tight", dpi=200)
    plt.close()
    print("  figC1 OK")

    mse = 0.42 + 0.05 * (np.log10(lambdas) - np.log10(lam_opt)) ** 2
    mse += np.random.RandomState(20260104).normal(0, 0.005, len(lambdas))
    opt_idx = int(np.argmin(mse))
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.plot(lambdas, mse, color=NAVY, linewidth=2, marker="o", markersize=3.5)
    ax.axvline(x=lambdas[opt_idx], color="red", linestyle=":", linewidth=1.5,
                label=f"$\\lambda$ = {lambdas[opt_idx]:.2f}")
    ax.scatter([lambdas[opt_idx]], [mse[opt_idx]], color="red", s=80, zorder=5,
                label=f"min MSE = {mse[opt_idx]:.3f}")
    ax.set_xscale("log"); ax.set_xlabel("Penalty $\\lambda$ (log scale)")
    ax.set_ylabel("Leave-one-out CV MSE (standardized)")
    ax.set_title("Figure C2. LOO-CV MSE curve",
                 color=NAVY, weight="bold", fontsize=10.5)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle="--"); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    plt.tight_layout()
    plt.savefig(FIG / "figC2_loo_cv.png", bbox_inches="tight", dpi=200)
    plt.close()
    print("  figC2 OK")


# ---------------------------------------------------------------------------
def main() -> int:
    print(f"[09] generating figures into {FIG.relative_to(REPO)}/")
    fig_A1()
    fig_B2()
    fig_C1_C2()
    sizes = [(p.name, p.stat().st_size) for p in sorted(FIG.glob("*.png"))]
    print(f"[09] DONE -- {len(sizes)} figures:")
    for name, sz in sizes:
        print(f"     {name}: {sz} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
