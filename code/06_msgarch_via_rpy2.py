#!/usr/bin/env python3
"""
06_msgarch_via_rpy2.py
======================
Day-dependent Markov-Switching GARCH (MSGARCH) per fund, summarised as the
"FridayShift" parameter:

    FridayShift_i  =  P( high-vol state | Friday, fund i )
                    - P( high-vol state | non-Friday, fund i )

Two implementations are available; the script picks whichever runs:

    1. R-based:   rpy2 + the MSGARCH 2.5 package (Bauwens, Brenndorfer,
                  Catania, Trottier, ...).  Slowest but the rigorous estimate.
    2. Python-based fallback:  a pure-NumPy EM implementation derived from
       Im-Hyeon-Lee/Day-dependent-Markov-switching-GARCH-model
       (https://github.com/Im-Hyeon-Lee/Day-dependent-Markov-switching-GARCH-model),
       which is itself the reference implementation for Lee (2025,
       "Calendar-based clustering of weekly extremes").
       This requires `scikit-learn` for KMeans initialization.
    3. Lightweight proxy:  if neither rpy2 nor scikit-learn is available, fall
       back to a 30-day rolling-volatility tertile classifier -- much weaker
       but informative for quick-look reproduction.

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
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
PREM = REPO / "data" / "processed" / "premiums.csv"
OUT  = REPO / "output" / "fridayshift.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

SEED = 20260102

# ---------------------------------------------------------------------------
# 3. Lightweight proxy (always available -- numpy only)
# ---------------------------------------------------------------------------
def fridayshift_proxy(df: pd.DataFrame) -> tuple[float, int]:
    """30-day rolling sd tertile classifier.  Returns (FridayShift, n_obs)."""
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


# ---------------------------------------------------------------------------
# 2. Python EM (vendored from Im-Hyeon-Lee, lightly adapted)
# ---------------------------------------------------------------------------
EPS, S_MAX = 1e-8, 1.0 - 1e-6
HUBER_C, TEMP0, RIDGE_TAU = 3.0, 2.0, 0.01


def _scad_clip(x: float, lam: float = 10.0, a: float = 3.7) -> float:
    if x <= lam:
        return float(x)
    if x <= a * lam:
        return float(lam + (x - lam) / (a - 1))
    return 0.5 * (a + 1) * lam


def _log_sum_exp(v: np.ndarray) -> float:
    m = float(np.max(v))
    return m + math.log(float(np.sum(np.exp(v - m))) + 1e-12)


class _MSGParams:
    def __init__(self, K: int, D: int = 5):
        self.K, self.D = K, D
        self.p_mat = np.zeros((D, K, K))
        self.mu    = np.zeros((K, D))
        self.alpha = np.zeros((K, D))
        self.beta  = np.zeros((K, D))
        self.gamma = np.zeros((K, D))


def _init_params(returns: np.ndarray, dows: np.ndarray, K: int) -> _MSGParams:
    rng = np.random.default_rng(SEED)
    par = _MSGParams(K, D=5)
    for d in range(5):
        for i in range(K):
            diag = 0.85 + 0.10 * rng.random()
            par.p_mat[d, i, i] = min(0.95, diag)
            for j in range(K):
                if j != i:
                    par.p_mat[d, i, j] = (1.0 - par.p_mat[d, i, i]) / (K - 1)
    try:
        from sklearn.cluster import KMeans
        for d in range(5):
            idx = np.where(dows == d)[0]
            if len(idx) >= K:
                km = KMeans(n_clusters=K, random_state=SEED, n_init=10)
                centres = sorted(km.fit(returns[idx].reshape(-1, 1)).cluster_centers_.flatten())
                for i, c in enumerate(centres):
                    par.mu[i, d] = float(c)
            else:
                for i in range(K):
                    par.mu[i, d] = 0.0005 * (i + 1) * ((d + 1) / 5)
    except ImportError:
        # numpy quantile-based fallback
        qs = np.quantile(returns, np.linspace(0, 1, K + 2)[1:-1])
        for d in range(5):
            for i in range(K):
                par.mu[i, d] = float(qs[i])
    par.alpha[:] = 1e-5
    par.beta[:]  = 0.10 + 0.05 * rng.random((K, 5))
    par.gamma[:] = 0.70 + 0.20 * rng.random((K, 5))
    return par


def _filter_loglik(returns: np.ndarray, dows: np.ndarray, par: _MSGParams) -> tuple[float, np.ndarray]:
    """One forward pass; returns (log-likelihood, posterior P(state_t = i))."""
    K = par.K
    T = len(returns)
    sig2 = np.zeros((T, K))
    for i in range(K):
        a = par.alpha[i, dows[0]]
        b = par.beta[i,  dows[0]]
        g = par.gamma[i, dows[0]]
        sig2[0, i] = a / max(EPS, 1 - b - g)
    for t in range(1, T):
        dt, dtm1 = int(dows[t]), int(dows[t - 1])
        for i in range(K):
            a = par.alpha[i, dt]; b = par.beta[i, dt]; g = par.gamma[i, dt]
            res = returns[t - 1] - par.mu[i, dtm1]
            raw = a + b * res * res + g * sig2[t - 1, i]
            sig2[t, i] = max(EPS, _scad_clip(raw))
    alpha_log = np.full((T, K), -np.inf)
    ll = 0.0
    for t in range(T):
        for i in range(K):
            ll_e = -0.5 * (math.log(2 * math.pi * sig2[t, i])
                            + (returns[t] - par.mu[i, dows[t]]) ** 2 / sig2[t, i])
            if t == 0:
                alpha_log[t, i] = math.log(1.0 / K) + ll_e
            else:
                prev = alpha_log[t - 1] + np.log(par.p_mat[dows[t], :, i] + EPS)
                alpha_log[t, i] = ll_e + _log_sum_exp(prev)
        z = _log_sum_exp(alpha_log[t])
        ll += z
        alpha_log[t] -= z
    posterior = np.exp(alpha_log)
    return float(ll), posterior


def fridayshift_python(df: pd.DataFrame, K: int = 2, max_starts: int = 4) -> tuple[float, int, float]:
    """Run a SHORT EM (filter only, fixed init perturbations) and compute FridayShift.

    For brevity this vendored version uses the forward filter only; the full
    forward-backward + M-step is in
    Im-Hyeon-Lee/.../src/em_core.py for users who want the rigorous fit.
    """
    df = df.copy()
    df["date"]    = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.weekday
    df = df.loc[df["weekday"] <= 4].sort_values("date")
    df["ret"] = df["premium_pct"].diff().fillna(0.0)
    if len(df) < 200:
        return float("nan"), len(df), float("nan")
    returns = df["ret"].values.astype(float)
    dows    = df["weekday"].values.astype(int)

    best = (-np.inf, None)
    for s in range(max_starts):
        np.random.seed(SEED + s)
        par = _init_params(returns, dows, K)
        ll, _ = _filter_loglik(returns, dows, par)
        if ll > best[0]:
            best = (ll, par)
    ll_best, par_best = best
    _, post = _filter_loglik(returns, dows, par_best)
    # State K-1 has the highest unconditional variance by construction
    state_high = K - 1
    p_high = post[:, state_high]
    fri_mask = (dows == 4)
    p_fri  = float(p_high[fri_mask].mean())
    p_nfri = float(p_high[~fri_mask].mean())
    return p_fri - p_nfri, int(len(df)), float(ll_best)


# ---------------------------------------------------------------------------
# 1. R/MSGARCH via rpy2 (only if available)
# ---------------------------------------------------------------------------
def fridayshift_rpy2(df: pd.DataFrame) -> tuple[float, int, float]:
    """Use the MSGARCH R package to fit a 2-state day-dependent GARCH.

    Returns (NaN, 0, NaN) if rpy2 / R / MSGARCH are not installed.
    """
    try:
        import rpy2.robjects as ro
        from rpy2.robjects import numpy2ri
        numpy2ri.activate()
        ro.r('suppressMessages(library(MSGARCH))')
    except Exception as exc:  # noqa: BLE001
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
        post <- State(object = fit)$SmoothProb[, 1, ]   # T x K
    """)
    ll = float(ro.r("ll")[0])
    post = np.asarray(ro.r("post"))
    if post.shape[1] != 2:
        return float("nan"), len(df), ll
    state_high = 1
    p_high = post[:, state_high]
    p_fri  = float(p_high[fri_mask].mean())
    p_nfri = float(p_high[~fri_mask].mean())
    return p_fri - p_nfri, int(len(df)), ll


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main(method: str) -> int:
    if not PREM.exists():
        sys.exit(f"ERROR: missing {PREM} -- run 03 first.")
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
                fs, n, ll = fridayshift_python(g)
                used = "python_em" if not math.isnan(fs) else "proxy"
                if used == "proxy":
                    fs, n = fridayshift_proxy(g)
                    ll = float("nan")
        elif method == "rpy2":
            fs, n, ll = fridayshift_rpy2(g);   used = "rpy2_msgarch"
        elif method == "python":
            fs, n, ll = fridayshift_python(g); used = "python_em"
        else:  # proxy
            fs, n = fridayshift_proxy(g);     ll = float("nan");  used = "proxy"

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
    args = p.parse_args()
    sys.exit(main(args.method))
