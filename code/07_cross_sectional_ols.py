"""Step 7 — multivariate OLS+HC3, ridge, fractional logit, diagnostics (§4.6)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from constants import OUTPUT_DIR
from utils import (ols_hc3, ridge_loocv, fractional_logit, wald_test,
                    vif, cooks_distance, condition_number,
                    spearman_with_t, bh_fdr, permutation_importance)
from utils.io import load_fund_metadata


def main() -> None:
    meta = load_fund_metadata().query("ticker != 'SPY'").reset_index(drop=True)
    fs   = pd.read_csv(OUTPUT_DIR / "fridayshift.csv")
    # Only merge the FridayShift column; the non-parametric backend leaves
    # fit_loglik = NaN, which would erase every row under a bulk dropna().
    df = meta.merge(fs[["ticker", "FridayShift"]], on="ticker", how="inner")
    df = df.dropna(subset=["FridayShift", "aum_usd_bn_2025", "adv_usd_m",
                            "duration_yrs", "bid_ask_bp", "expense_ratio_bp",
                            "benchmark"])

    # six pre-specified predictors per §4.6
    df["log_AUM"] = np.log(df["aum_usd_bn_2025"])
    df["log_ADV_AUM"] = np.log(df["adv_usd_m"] / df["aum_usd_bn_2025"])
    df["treasury"] = df["benchmark"].str.contains("Treasury", case=False, na=False).astype(int)
    df["duration"] = df["duration_yrs"]
    df["bid_ask"] = df["bid_ask_bp"]
    df["expense"] = df["expense_ratio_bp"]
    predictors = ["log_AUM", "treasury", "log_ADV_AUM", "duration", "bid_ask", "expense"]

    X = np.column_stack([np.ones(len(df))] + [df[c].values for c in predictors])
    y = df["FridayShift"].values

    # OLS + HC3
    res = ols_hc3(X, y)
    print("\nOLS+HC3 results:")
    for j, name in enumerate(["intercept"] + predictors):
        print(f"  {name:14s}  beta={res['beta_hat'][j]:+.4f}  HC3 SE={res['se_hc3'][j]:.4f}")
    print(f"  residual df = {len(y) - X.shape[1]}")

    # diagnostics
    print(f"\nVIF: {dict(zip(predictors, vif(X[:, 1:]).round(2)))}")
    print(f"Condition number kappa(X'X) = {condition_number(X[:, 1:]):.2f}")
    D = cooks_distance(X, y)
    print(f"Cook's D > 4/N: {df['ticker'].iloc[D > 4 / len(y)].tolist()}")

    # Wald F: flow-block (treasury, log_AUM, log_ADV_AUM)
    R_flow = np.zeros((3, X.shape[1]))
    R_flow[0, 1] = 1; R_flow[1, 2] = 1; R_flow[2, 3] = 1
    w_flow = wald_test(res["beta_hat"], res["V_HC3"], R_flow)
    print(f"\nWald flow-block F = {w_flow['W']:.2f}  (df_num={w_flow['df_num']})")

    # ridge LOO-CV
    rr = ridge_loocv(X, y)
    print(f"\nRidge: lambda* = {rr['lambda_star']:.4f}  MSE_LOO = {rr['mse_loo'].min():.4f}")

    # univariate Spearman + BH-FDR
    spear = []
    for c in predictors:
        s = spearman_with_t(df[c].values, y)
        spear.append({"predictor": c, **s})
    sp = pd.DataFrame(spear)
    rej, q = bh_fdr(sp["p"].values)
    sp["q_FDR"] = q
    sp.to_csv(OUTPUT_DIR / "spearman_results.csv", index=False)
    print("\nSpearman cross-sectional ranking:")
    print(sp.to_string(index=False))

    # permutation importance using the OLS fit
    def predict(Xnew): return Xnew @ res["beta_hat"]
    imp = permutation_importance(X[:, 1:], y, lambda Xn: predict(np.column_stack([np.ones(len(Xn)), Xn])), n_perm=200)
    pd.DataFrame({"predictor": predictors, "importance": imp}).to_csv(
        OUTPUT_DIR / "permutation_importance.csv", index=False)
    print("\nPermutation importance:")
    for p_, im in zip(predictors, imp):
        print(f"  {p_:14s}  Imp = {im:+.4f}")

    # Diagnostics sidecar consumed by audit/claims_manifest.json
    import json
    diag = {
        "n_obs":              int(len(y)),
        "n_predictors":       int(X.shape[1] - 1),
        "predictors":         predictors,
        "wald_F_flow":        round(float(w_flow["W"]), 4),
        "wald_F_flow_df_num": int(w_flow["df_num"]),
        "ridge_lambda":       round(float(rr["lambda_star"]), 4),
        "ridge_mse_loo":      round(float(rr["mse_loo"].min()), 5),
        "condition_number":   round(float(condition_number(X[:, 1:])), 2),
        "cooks_flagged":      df["ticker"].iloc[D > 4 / len(y)].tolist(),
    }
    (OUTPUT_DIR / "cross_sectional_diag.json").write_text(
        json.dumps(diag, indent=2), encoding="utf-8")

    print("\nStep 7 complete.")


if __name__ == "__main__":
    main()
