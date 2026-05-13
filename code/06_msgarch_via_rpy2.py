"""Step 6 — day-dependent MSGARCH FridayShift (§4.5, Eq. F.17-F.18).

THIS SCRIPT IS ORIGINAL TO THIS REPOSITORY.  It is a wrapper that selects
one of three backends and aggregates per-ETF FridayShift into
`output/fridayshift.csv`.  No MSGARCH algorithm code is reproduced inline;
the Python EM backend imports from the vendored package under
`code/_vendored_msgarch_lee2025/` (MIT-licensed; pinned commit
c84bc297d11e430cd459a20919fee1a425e1dd41 of Lee 2025).  See
`THIRD_PARTY_LICENSES.md` and the audit harness
(`audit/check_provenance.py`) for the provenance chain.

Backends (in priority order; `--method auto` tries each in turn)
----------------------------------------------------------------
    1. rpy2        R + MSGARCH 2.5 (Bauwens, Brenndorfer, Catania,
                   Trottier).  Currently stubbed (NotImplementedError);
                   the R package is not bundled.
    2. python_em   Vendored Lee (2025) full forward-backward + M-step EM.
                   Requires scikit-learn (KMeans init) and scipy (L-BFGS-B).
    3. nonparam    Non-parametric Friday-vs-other variance log-ratio:
                   FridayShift = log( var(Fri) / var(non-Fri) ).
                   numpy-only, fast, correlated ~0.94 with the EM
                   FridayShift on the synthetic-mechanism prior
                   (per paper Appendix B.5).

Inputs
------
data/processed/premiums.csv  (long format: date, ticker, prem)

Output
------
output/fridayshift.csv       columns: ticker, n_obs, FridayShift, method, fit_loglik

Random seed
-----------
SEED_MSGARCH_START = 20260102  (constants.py)

Usage
-----
    python code/06_msgarch_via_rpy2.py [--method auto|rpy2|python|nonparam]
                                        [--n-start 4]
"""
from __future__ import annotations
import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))   # for vendored package

from constants import TICKERS_ALL_20, OUTPUT_DIR, SEED_MSGARCH_START, FRIDAY
from utils.io import load_premiums


# ============================================================================
# Backend 3 (always available): non-parametric log-variance-ratio
# ORIGINAL to this repository.
# ============================================================================
def fridayshift_nonparam(ret: np.ndarray, weekday: np.ndarray) -> tuple[float, int]:
    weekday = np.asarray(weekday, dtype=int)
    ret     = np.asarray(ret, dtype=float)
    if len(ret) < 50:
        return float("nan"), len(ret)
    var_fri   = float(np.var(ret[weekday == FRIDAY]))
    var_other = float(np.var(ret[(weekday != FRIDAY) & (weekday <= 4)]))
    if var_other <= 0 or var_fri <= 0:
        return float("nan"), len(ret)
    return float(np.log(var_fri / var_other)), len(ret)


# ============================================================================
# Backend 2: vendored Lee (2025) Python EM.
# WRAPPER is ORIGINAL; the algorithm is imported from the MIT-licensed
# vendored package at code/_vendored_msgarch_lee2025/.
# ============================================================================
def fridayshift_python_em(ret: np.ndarray, weekday: np.ndarray,
                           K: int = 2, n_start: int = 4) -> tuple[float, int, float]:
    try:
        from _vendored_msgarch_lee2025 import (  # type: ignore
            forward_backward_EM, fit_ms_garch_multi,
        )
        from _vendored_msgarch_lee2025.utils import compute_lam_scad  # type: ignore
    except ImportError:
        return float("nan"), 0, float("nan")

    weekday = np.asarray(weekday, dtype=int)
    ret     = np.asarray(ret, dtype=float)
    if len(ret) < 200:
        return float("nan"), len(ret), float("nan")

    np.random.seed(SEED_MSGARCH_START)
    fitted   = fit_ms_garch_multi(ret, weekday, K, n_start=n_start)
    lam_scad = compute_lam_scad(ret)
    xi, _, _, ll = forward_backward_EM(ret, weekday, fitted, lam_scad)
    # Upstream convention: state K-1 has highest unconditional variance.
    p_high = xi[:, K - 1]
    p_fri  = float(p_high[weekday == FRIDAY].mean())
    p_nfri = float(p_high[(weekday != FRIDAY) & (weekday <= 4)].mean())
    return p_fri - p_nfri, int(len(ret)), float(ll)


# ============================================================================
# Backend 1: rpy2 + MSGARCH 2.5.  ORIGINAL wrapper; R/MSGARCH not bundled.
# ============================================================================
def fridayshift_rpy2(ret: np.ndarray, weekday: np.ndarray) -> tuple[float, int, float]:
    try:
        import rpy2.robjects as ro  # type: ignore
        from rpy2.robjects import numpy2ri  # type: ignore
        numpy2ri.activate()
        ro.r("suppressMessages(library(MSGARCH))")
    except Exception:
        return float("nan"), 0, float("nan")

    weekday = np.asarray(weekday, dtype=int)
    if len(ret) < 200:
        return float("nan"), len(ret), float("nan")
    fri_mask = (weekday == FRIDAY)
    ro.globalenv["ret"] = ret
    ro.r("""
        spec <- CreateSpec(variance.spec = list(model = c('sGARCH','sGARCH')),
                            distribution.spec = list(distribution = c('norm','norm')),
                            switch.spec = list(do.mix = FALSE, K = 2))
        fit  <- FitML(spec = spec, data = ret, ctr = list(do.se = FALSE))
        ll   <- fit$loglik
        post <- State(object = fit)$SmoothProb[, 1, ]
    """)
    ll = float(ro.r("ll")[0])
    post = np.asarray(ro.r("post"))
    if post.shape[1] != 2:
        return float("nan"), len(ret), ll
    p_high = post[:, 1]
    p_fri  = float(p_high[fri_mask].mean())
    p_nfri = float(p_high[~fri_mask].mean())
    return p_fri - p_nfri, int(len(ret)), ll


# ============================================================================
# Driver.  ORIGINAL to this repository.
# ============================================================================
def fridayshift_for_ticker(df: pd.DataFrame, method: str, n_start: int) -> dict:
    df = df.copy()
    df["date"]    = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.weekday
    df = df.loc[df["weekday"] <= 4].sort_values("date")
    df["ret"] = df["prem"].diff().fillna(0.0)
    ret = df["ret"].to_numpy()
    wd  = df["weekday"].to_numpy()

    if method == "auto":
        fs, n, ll = fridayshift_rpy2(ret, wd)
        if not math.isnan(fs):
            return {"fs": fs, "n": n, "method": "rpy2_msgarch", "loglik": ll}
        fs, n, ll = fridayshift_python_em(ret, wd, n_start=n_start)
        if not math.isnan(fs):
            return {"fs": fs, "n": n, "method": "python_em", "loglik": ll}
        fs, n = fridayshift_nonparam(ret, wd)
        return {"fs": fs, "n": n, "method": "nonparam", "loglik": float("nan")}
    if method == "rpy2":
        fs, n, ll = fridayshift_rpy2(ret, wd)
        return {"fs": fs, "n": n, "method": "rpy2_msgarch", "loglik": ll}
    if method == "python":
        fs, n, ll = fridayshift_python_em(ret, wd, n_start=n_start)
        return {"fs": fs, "n": n, "method": "python_em", "loglik": ll}
    # nonparam
    fs, n = fridayshift_nonparam(ret, wd)
    return {"fs": fs, "n": n, "method": "nonparam", "loglik": float("nan")}


def main(method: str, n_start: int) -> int:
    df_all = load_premiums()
    print(f"[06] FridayShift via method='{method}' (seed={SEED_MSGARCH_START})")
    rows = []
    for tkr in TICKERS_ALL_20:
        df = df_all.loc[df_all["ticker"] == tkr]
        if len(df) < 100:
            continue
        out = fridayshift_for_ticker(df, method, n_start)
        rows.append({"ticker": tkr, "n_obs": int(out["n"]),
                     "FridayShift": round(float(out["fs"]), 4) if not math.isnan(out["fs"]) else out["fs"],
                     "method": out["method"],
                     "fit_loglik": round(float(out["loglik"]), 2) if not math.isnan(out["loglik"]) else out["loglik"]})
        print(f"  [{tkr}]  n={out['n']:5d}  FS={out['fs']:+.4f}  method={out['method']}")
    pd.DataFrame(rows).to_csv(OUTPUT_DIR / "fridayshift.csv", index=False)
    n_real = sum(1 for r in rows
                  if not (isinstance(r["FridayShift"], float) and math.isnan(r["FridayShift"])))
    print(f"Step 6 complete -> output/fridayshift.csv  ({n_real}/{len(rows)} fits OK)")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--method", choices=["auto", "rpy2", "python", "nonparam"], default="auto")
    p.add_argument("--n-start", type=int, default=4,
                   help="EM random restarts for the python backend (upstream default 12)")
    args = p.parse_args()
    sys.exit(main(args.method, args.n_start))
