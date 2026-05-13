"""Step 9 — regenerate figA1, figB2, figC1, figC2 PNGs from output CSVs."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent.parent))
from constants import OUTPUT_DIR, FIGURE_DIR
from utils import ridge_loocv
from utils.io import load_fund_metadata


def fig_A1():
    meta = load_fund_metadata().query("ticker != 'SPY'")
    fig, ax = plt.subplots(figsize=(7, 4))
    issuer_color = {"iShares": "C0", "Vanguard": "C1", "State Street": "C2",
                    "Canadian": "C3", "UCITS": "C4"}
    for i, (_, r) in enumerate(meta.iterrows()):
        ax.barh(i, 24, left=2002, color=issuer_color.get(r["issuer"], "gray"))
    ax.set_yticks(range(len(meta))); ax.set_yticklabels(meta["ticker"])
    ax.set_xlabel("Year")
    ax.set_title("Figure A1. Sample composition (19 bond ETFs)")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "figA1_sample_composition.png", dpi=150)
    plt.close()


def fig_B2():
    df = pd.read_csv(OUTPUT_DIR / "hcug_results.csv").sort_values("fri_pct", ascending=False)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(df["ticker"], df["fri_pct"])
    ax.axhline(21, color="red", linestyle="--", label="21% baseline")
    ax.set_ylabel("Friday share of weekly max-premium (%)")
    ax.set_title("Figure B2. Friday share by ETF")
    ax.legend(); plt.xticks(rotation=45, ha="right"); plt.tight_layout()
    plt.savefig(FIGURE_DIR / "figB2_friday_share_by_etf.png", dpi=150)
    plt.close()


def fig_C1_C2():
    meta = load_fund_metadata().query("ticker != 'SPY'").reset_index(drop=True)
    fs = pd.read_csv(OUTPUT_DIR / "fridayshift.csv")
    df = meta.merge(fs, on="ticker", how="inner").dropna()
    df["log_AUM"] = np.log(df["aum_usd_bn_2025"])
    df["log_ADV_AUM"] = np.log(df["adv_usd_m"] / df["aum_usd_bn_2025"])
    df["treasury"] = df["benchmark"].str.contains("Treasury", case=False, na=False).astype(int)
    X = np.column_stack([np.ones(len(df)),
                         df["log_AUM"], df["treasury"], df["log_ADV_AUM"]])
    y = df["FridayShift"].values
    rr = ridge_loocv(X, y)

    # C1 - coefficient path
    fig, ax = plt.subplots(figsize=(7, 4))
    log_lam = np.log10(rr["lambdas"])
    for j, name in enumerate(["intercept", "log AUM", "Treasury", "log ADV/AUM"]):
        ax.plot(log_lam, rr["betas"][:, j], label=name)
    ax.axvline(np.log10(rr["lambda_star"]), color="black", linestyle="--", label=r"$\lambda^*$")
    ax.set_xlabel(r"$\log_{10} \lambda$"); ax.set_ylabel("ridge coefficient")
    ax.set_title("Figure C1. Ridge coefficient path")
    ax.legend(); plt.tight_layout()
    plt.savefig(FIGURE_DIR / "figC1_ridge_path.png", dpi=150)
    plt.close()

    # C2 - LOO-CV MSE
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(log_lam, rr["mse_loo"])
    ax.axvline(np.log10(rr["lambda_star"]), color="black", linestyle="--", label=r"$\lambda^*$")
    ax.set_xlabel(r"$\log_{10} \lambda$"); ax.set_ylabel("LOO-CV MSE")
    ax.set_title("Figure C2. Leave-one-out cross-validation")
    ax.legend(); plt.tight_layout()
    plt.savefig(FIGURE_DIR / "figC2_loo_cv.png", dpi=150)
    plt.close()


def main() -> None:
    fig_A1();  fig_B2();  fig_C1_C2()
    print(f"Step 9 complete -> {FIGURE_DIR}/")


if __name__ == "__main__":
    main()
