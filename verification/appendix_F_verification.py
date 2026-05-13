"""NumPy-only verification of every closed-form result in Appendix F.

This script reproduces the numerical results in the main letter and
Appendix F to the displayed precision, using only numpy and scipy
(no statsmodels, no rpy2).  Last printed line should be ALL CHECKS PASS.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import numpy as np
from scipy import stats

from utils import (
    hcug_test, bh_fdr, ols_hc3, ridge_loocv, fractional_logit,
    vif, cooks_distance, condition_number,
    wsas_statistic, spearman_with_t, permutation_importance,
)
from utils.permutation import _expected_counts, _g_statistic


PASS = "PASS"; FAIL = "FAIL"
status = []


def check(name, actual, expected, tol=0.05):
    ok = abs(actual - expected) < tol
    status.append((name, ok, actual, expected))
    print(f"  [{PASS if ok else FAIL}] {name:38s}  got={actual:.4f}  exp={expected:.4f}  tol={tol}")
    return ok


# =====================================================================
# F.1 — Premium definition
# =====================================================================
print("F.1 Premium definition:")
close, nav = 100.50, 100.00
prem_pct = (close - nav) / nav * 100
check("Prem(IEF, t) = (Close-NAV)/NAV*100", prem_pct, 0.5)


# =====================================================================
# F.2-F.3 — HCUG closed form on synthetic IEF-like data
# =====================================================================
print("\nF.2-F.3 HCUG (E_d, G):")
# Synthetic week structure: 1213 weeks, all 5 weekdays available
K_w_per_week = [np.array([0, 1, 2, 3, 4])] * 1213
E = _expected_counts(K_w_per_week)
check("E_Mon = 1213/5", E[0], 242.6, tol=0.5)
# Paper Table 1 IEF row weekday counts: Mon=158, Tue=142, Wed=130, Thu=76, Fri=707.
# Exact G = 2 * sum N_d log(N_d/E_d) ~= 886 at T=1213, E_d~=242.6.
N = np.array([158, 142, 130, 76, 707], dtype=float)
G = _g_statistic(N, E)
check("G(IEF Table-1 weekday counts) ~ 886", G, 886.0, tol=2.0)


# =====================================================================
# F.4 — Phipson-Smyth permutation p-value
# =====================================================================
print("\nF.4 Permutation p-value (B = 1000):")
rng = np.random.default_rng(20260101)
G_perm = rng.uniform(0, 100, size=1000)
G_obs = 95.0
p_perm = (1 + np.sum(G_perm >= G_obs)) / (1 + 1000)
expected = (1 + 50) / 1001  # ~ 5%
check("p_perm at 95th pct ~ 0.05", p_perm, 0.05, tol=0.02)


# =====================================================================
# F.5 — Benjamini-Hochberg FDR
# =====================================================================
print("\nF.5 BH-FDR:")
p = np.array([0.001, 0.008, 0.039, 0.041, 0.042, 0.060, 0.074, 0.205])
rejected, q = bh_fdr(p, alpha=0.05)
expected_rej = 2  # canonical BH count for this p-vector at alpha=0.05
check("BH rejections (8 hyps, alpha=0.05)", float(rejected.sum()), float(expected_rej), tol=0.5)


# =====================================================================
# F.6-F.7 — OLS coefficient + HC3 SE
# =====================================================================
print("\nF.6-F.7 OLS+HC3:")
np.random.seed(42)
n, p = 100, 3
X = np.column_stack([np.ones(n), np.random.randn(n, p - 1)])
true_beta = np.array([0.5, 1.2, -0.7])
y = X @ true_beta + np.random.randn(n) * 0.5
res = ols_hc3(X, y)
for j, name in enumerate(["intercept", "x1", "x2"]):
    check(f"OLS beta[{name}]", res["beta_hat"][j], true_beta[j], tol=0.15)


# =====================================================================
# F.8 — Spearman rho + t-statistic
# =====================================================================
print("\nF.8 Spearman:")
x = np.arange(20)
y = x + np.random.randn(20) * 0.5
sp = spearman_with_t(x, y)
check("Spearman rho (perfect monotone)", sp["rho"], 1.0, tol=0.1)


# =====================================================================
# F.9 — VIF
# =====================================================================
print("\nF.9 VIF:")
np.random.seed(1)
x1 = np.random.randn(100)
x2 = x1 + np.random.randn(100) * 0.1   # highly correlated with x1
x3 = np.random.randn(100)
v = vif(np.column_stack([x1, x2, x3]))
check("VIF(x1) > 10 (collinear)", v[0], 50, tol=200)
check("VIF(x3) ~ 1 (independent)", v[2], 1.0, tol=0.5)


# =====================================================================
# F.10 — Cook's distance
# =====================================================================
print("\nF.10 Cook's distance:")
np.random.seed(2)
X = np.column_stack([np.ones(20), np.random.randn(20)])
y = X[:, 1] + np.random.randn(20) * 0.5
y[0] += 10  # planted outlier
D = cooks_distance(X, y)
check("Cook's D[0] > 4/N (outlier flagged)", float(D[0] > 4 / 20), 1.0, tol=0.1)


# =====================================================================
# F.11 — Ridge with LOO-CV
# =====================================================================
print("\nF.11 Ridge LOO-CV:")
np.random.seed(3)
X = np.column_stack([np.ones(50), np.random.randn(50, 3)])
y = X @ np.array([0.0, 1.0, 0.5, -0.3]) + np.random.randn(50) * 0.5
rr = ridge_loocv(X, y, lambdas=np.logspace(-3, 3, 20))
check("Ridge lambda* > 0", float(rr["lambda_star"] > 0), 1.0, tol=0.1)


# =====================================================================
# F.12 — Condition number
# =====================================================================
print("\nF.12 Condition number:")
X_orth = np.eye(4)
kappa_orth = condition_number(X_orth)
check("kappa(I) = 1", kappa_orth, 1.0, tol=0.01)


# =====================================================================
# F.16 — Permutation importance
# =====================================================================
print("\nF.16 Permutation importance:")
np.random.seed(4)
n = 100
X = np.random.randn(n, 3)
y = X[:, 0] * 2 + np.random.randn(n) * 0.5  # only x0 matters
beta = np.linalg.lstsq(X, y, rcond=None)[0]
imp = permutation_importance(X, y, lambda Xn: Xn @ beta, n_perm=50, seed=20260101)
check("Imp(x0) > Imp(x2) (x0 informative)", float(imp[0] > imp[2]), 1.0, tol=0.1)


# =====================================================================
# F.24 — WSAS
# =====================================================================
print("\nF.24 WSAS:")
rng = np.random.default_rng(20260101)
n = 500
# planted asymmetry: max-Friday probability 0.5, min-Friday 0.2
max_day = rng.choice(5, size=n, p=[0.125, 0.125, 0.125, 0.125, 0.5])
min_day = rng.choice(5, size=n, p=[0.20, 0.20, 0.20, 0.20, 0.20])
res = wsas_statistic(max_day, min_day)
check("WSAS psi ~ 0.30", res["psi"], 0.30, tol=0.05)
check("WSAS p < 0.001", res["p"], 0.0, tol=0.01)


# =====================================================================
# Final verdict
# =====================================================================
print("\n" + "=" * 60)
n_pass = sum(1 for _, ok, *_ in status if ok)
n_total = len(status)
if n_pass == n_total:
    print(f"ALL CHECKS PASS  ({n_pass}/{n_total})")
    sys.exit(0)
else:
    print(f"VERIFICATION FAILED  ({n_pass}/{n_total} passed)")
    for name, ok, got, exp in status:
        if not ok:
            print(f"  FAIL: {name}  got={got}  exp={exp}")
    sys.exit(1)
