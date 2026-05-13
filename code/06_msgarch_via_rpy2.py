#!/usr/bin/env python3
"""
06_msgarch_via_rpy2.py
======================
Day-dependent MSGARCH per fund, summarised as the FridayShift parameter:

    FridayShift_i = P(high-vol state | Friday, fund i)
                  - P(high-vol state | non-Friday, fund i)

This script is ORIGINAL to this repository.  It is a thin wrapper that
selects one of three backends and aggregates the per-ETF FridayShift into
`output/fridayshift.csv`.  No MSGARCH algorithm code is reproduced inline
here; the Python EM backend is imported from the vendored package below.

THIRD-PARTY ATTRIBUTION (MIT-licensed)
--------------------------------------
The Python EM backend comes from a verbatim vendored copy of:

    Lee, Im-Hyeon (2025).  Day-dependent Markov-switching GARCH model.
    https://github.com/Im-Hyeon-Lee/Day-dependent-Markov-switching-GARCH-model

The copy lives at `code/_vendored_msgarch_lee2025/` with the original MIT
LICENSE preserved verbatim; pinned upstream commit
`c84bc297d11e430cd459a20919fee1a425e1dd41` (2025-06-23).
See `code/_vendored_msgarch_lee2025/PROVENANCE.md` and
`THIRD_PARTY_LICENSES.md` for the full vendoring policy and citation.

`audit/check_provenance.py` re-validates the vendored files against upstream
on every audit cycle; divergences appear in `audit/PROVENANCE_REPORT.md`.

Backends (in priority order; `--method auto` tries each in turn)
----------------------------------------------------------------
    1. rpy2  -- R + MSGARCH 2.5 (Bauwens, Brenndorfer, Catania, Trottier)
                Original wrapper here; R package not bundled.
    2. python -- Vendored Lee (2025) EM, full forward-backward + M-step.
                 Requires scikit-learn (KMeans init) and scipy (L-BFGS-B).
    3. proxy  -- 30-day rolling-volatility tertile classifier
                 (numpy-only fallback; original to this repository).

Inputs
------
data/processed/premiums.csv         # produced by 03

Output
------
output/fridayshift.csv
    ticker, n_obs, fridayshift, method, fit_loglik

Random seed
-----------
np.random.seed(20260102)

Usage
-----
    python code/06_msgarch_via_rpy2.py [--method auto|rpy2|python|proxy]
                                       [--n-start 4]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Make code/_vendored_msgarch_lee2025/ importable when running this script
# directly (Python automatically adds the script's directory to sys.path).
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

REPO = HERE.parent
PREM = REPO / "data" / "processed" / "premiums.csv"
OUT  = REPO / "output" / "fridayshift.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

SEED = 20260102


# ============================================================================
# Backend 3 (always available): numpy-only rolling-volatility tertile proxy.
# This is ORIGINAL code in this repository — NOT from Lee (2025).
# ============================================================================
def fridayshift_proxy(df: pd.DataFrame) -> tuple[float, int]:
    """30-day rolling sd tertile classifier.  Returns (FridayShift, n_obs).

    For each business day, classify the realised premium-change volatility
    over the trailing 30 days into 'high' (>= 67th pct) vs 'not high'.
    FridayShift = P(high | Friday) - P(high | non-Friday).

    This is a coarse but well-defined statistic that does NOT require the
    full MSGARCH apparatus.  Useful when scikit-learn / scipy / rpy2 are
    unavailable, or as a sanity check against the EM result.
    """
    df = df.copy()
    df["date"]    = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.weekday
    df = df.sort_values("date")
    df["ret"] = df["premium_pct"].diff()
    df["sd30"] = df["ret"].rolling(30, min_periods=10).std()
    df = df.dropna(subset=["sd30"])
    if len(df) < 60:
        return float("nan"), len(df)
    thresh = float(df["sd30"].quantile(0.67))
    df["high"] = (df["sd30"] >= thresh).astype(int)
    p_fri  = float(df.loc[df["weekday"] == 4, "high"].mean())
    p_nfri = float(df.loc[(df["weekday"] != 4) & (df["weekday"] <= 4), "high"].mean())
    return p_fri - p_nfri, int(len(df))


# ============================================================================
# Backend 2: vendored Lee (2025) Python EM.
# This wrapper is ORIGINAL; the algorithm is imported from the MIT-licensed
# vendored package code/_vendored_msgarch_lee2025/.  See THIRD_PARTY_LICENSES.md.
# ============================================================================
def fridayshift_python(df: pd.DataFrame, K: int = 2, n_start: int = 4) -> tuple[float, int, float]:
    """Fit day-dependent MSGARCH via the vendored Lee (2025) EM.

    Uses the full forward-backward + M-step from the upstream package.
    Parameters
    ----------
    K : int
        Number of latent regimes (default 2).
    n_start : int
        Number of random restarts; upstream default is 12, we cap at 4 for
        per-ETF runtime under our 18-ETF cross-section.

    Returns (FridayShift, n_obs, fit_loglik).
    """
    try:
        from _vendored_msgarch_lee2025 import (  # type: ignore
            forward_backward_EM, fit_ms_garch_multi,
        )
        from _vendored_msgarch_lee2025.utils import compute_lam_scad  # type: ignore
    except ImportError:
        return float("nan"), 0, float("nan")

    df = df.copy()
    df["date"]    = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.weekday
    df = df.loc[df["weekday"] <= 4].sort_values("date")
    df["ret"] = df["premium_pct"].diff().fillna(0.0)
    if len(df) < 200:
        return float("nan"), len(df), float("nan")

    returns = df["ret"].values.astype(float)
    dows    = df["weekday"].values.astype(int)

    np.random.seed(SEED)
    fitted   = fit_ms_garch_multi(returns, dows, K, n_start=n_start)
    lam_scad = compute_lam_scad(returns)
    xi, _, _, ll_best = forward_backward_EM(returns, dows, fitted, lam_scad)

    # The upstream convention orders states ascending in unconditional variance;
    # the last state (K-1) is therefore the 'high-vol' regime.
    p_high = xi[:, K - 1]
    fri_mask = (dows == 4)
    p_fri  = float(p_high[fri_mask].mean())
    p_nfri = float(p_high[~fri_mask].mean())
    return p_fri - p_nfri, int(len(df)), float(ll_best)


# ============================================================================
# Backend 1: R / MSGARCH 2.5 via rpy2 (only if installed).
# This wrapper is ORIGINAL.  R + MSGARCH itself is NOT vendored; it is
# installed system-wide by the user.
# ============================================================================
def fridayshift_rpy2(df: pd.DataFrame) -> tuple[float, int, float]:
    """Use the R MSGARCH 2.5 package to fit a 2-state day-dependent GARCH."""
    try:
        import rpy2.robjects as ro  # type: ignore
        from rpy2.robjects import numpy2ri  # type: ignore
        numpy2ri.activate()
        ro.r("suppressMessages(library(MSGARCH))")
    except Exception:
        return float("nan"), 0, float("nan")

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.loc[pd.to_datetime(df["date"]).dt.weekday <= 4].sort_values("date")
    df["ret"]  = df["premium_pct"].diff().fillna(0.0)
    if len(df) < 200:
        return float("nan"), len(df), float("nan")

    ret = df["ret"].values.astype(float)
    fri_mask = (pd.to_datetime(df["date"]).dt.weekday == 4).values
    ro.globalenv["ret"] = ret
    ro.r("""
        spec <- CreateSpec(variance.spec = list(model = c('sGARCH', 'sGARCH')),
                            distribution.spec = list(distribution = c('norm','norm')),
                            switch.spec = list(do.mix = FALSE, K = 2))
        fit  <- FitML(spec = spec, data = ret, ctr = list(do.se = FALSE))
        ll   <- fit$loglik
        post <- State(object = fit)$SmoothProb[, 1, ]
    """)
    ll   = float(ro.r("ll")[0])
    post = np.asarray(ro.r("post"))
    if post.shape[1] != 2:
        return float("nan"), len(df), ll
    p_high = post[:, 1]
    p_fri  = float(p_high[fri_mask].mean())
    p_nfri = float(p_high[~fri_mask].mean())
    return p_fri - p_nfri, int(len(df)), ll


# ============================================================================
# Driver — ORIGINAL to this repository
# ============================================================================
def main(method: str, n_start: int) -> int:
    if not PREM.exists():
        sys.exit(f"ERROR: missing {PREM} — run 03 first.")
    df = pd.read_csv(PREM)
    print(f"[06] FridayShift via method='{method}' (seed={SEED})")

    rows = []
    for t, g in df.groupby("ticker", sort=False):
        used = method
        if method == "auto":
            r1 = fridayshift_rpy2(g)
            if not math.isnan(r1[0]):
                fs, n, ll = r1
                used = "rpy2_msgarch"
            else:
                fs, n, ll = fridayshift_python(g, n_start=n_start)
                used = "python_em" if not math.isnan(fs) else "proxy"
                if used == "proxy":
                    fs, n = fridayshift_proxy(g)
                    ll = float("nan")
        elif method == "rpy2":
            fs, n, ll = fridayshift_rpy2(g);             used = "rpy2_msgarch"
        elif method == "python":
            fs, n, ll = fridayshift_python(g, n_start=n_start); used = "python_em"
        else:  # proxy
            fs, n = fridayshift_proxy(g); ll = float("nan"); used = "proxy"

        rows.append({"ticker": t, "n_obs": int(n),
                     "fridayshift": round(float(fs), 4) if not math.isnan(fs) else fs,
                     "method": used,
                     "fit_loglik": round(float(ll), 2) if not math.isnan(ll) else ll})
        print(f"  [{t}]  n={n:5d}  FS={fs:+.4f}  method={used}")

    pd.DataFrame(rows).to_csv(OUT, index=False)
    n_real = sum(1 for r in rows if not (isinstance(r["fridayshift"], float) and math.isnan(r["fridayshift"])))
    print(f"\n[06] DONE -- wrote {OUT.relative_to(REPO)}  ({n_real}/{len(rows)} fits OK)")
    if any(r["method"] == "proxy" for r in rows):
        print("     Some fits used the lightweight proxy -- install scikit-learn or "
              "rpy2+MSGARCH for the rigorous estimate.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--method", choices=["auto", "rpy2", "python", "proxy"], default="auto")
    p.add_argument("--n-start", type=int, default=4,
                   help="EM random restarts (upstream default is 12)")
    args = p.parse_args()
    sys.exit(main(args.method, args.n_start))
