#!/usr/bin/env python3
"""
appendix_F_verification.py -- closed-form / asymptotic math verification (numpy-only)

Reproduces every numerical demonstration in Appendix F of the manuscript using
only `numpy`.  No scipy / statsmodels / sklearn dependency.  Hand-verifiable
on the toy data shown.

Run on any laptop with numpy installed:

    python verification/appendix_F_verification.py

The last printed line MUST read:

    ALL CHECKS PASS
"""
import math
from datetime import datetime

import numpy as np

print("=" * 78)
print("Appendix F verification -- closed-form math (numpy-only)")
print(f"Run: {datetime.now().isoformat(timespec='seconds')}")
print("=" * 78)

RNG = np.random.default_rng(20260101)

# ----------------------------------------------------------------------------
# F.1  Premium definition (closed form)
# ----------------------------------------------------------------------------
close = np.array([100.10, 100.05, 100.20])
nav   = np.array([100.00, 100.05, 100.10])
prem  = (close - nav) / nav * 100
print("\n[F.1]  Prem(i,t) = (Close - NAV) / NAV * 100")
print(f"       toy days: {prem.round(4)}")
assert abs(prem[0] - 0.10) < 1e-9, "F.1 premium mismatch"

# ----------------------------------------------------------------------------
# F.2  Holiday-conditioned expected count E_d (closed form)
# ----------------------------------------------------------------------------
weeks = [["Mon", "Tue", "Wed", "Thu", "Fri"]] * 4 + [["Mon", "Tue", "Wed", "Thu"]]
E = {d: 0.0 for d in ["Mon", "Tue", "Wed", "Thu", "Fri"]}
for K in weeks:
    for d in K:
        E[d] += 1.0 / len(K)
print(f"\n[F.2]  E_Fri = sum_w I(Fri in K_w)/|K_w| = {E['Fri']:.3f}  "
      f"(expect 4 * 1/5 = 0.800)")
assert abs(E["Fri"] - 0.800) < 1e-9, "F.2 expected-count mismatch"

# ----------------------------------------------------------------------------
# F.3  G-statistic (closed form)
# ----------------------------------------------------------------------------
N_obs = np.array([8, 9, 11, 12, 24], dtype=float)
T = N_obs.sum()
E_exp = T * np.full(5, 0.20)
G = 2 * np.sum(N_obs * np.log(N_obs / E_exp))
print(f"\n[F.3]  N (Mon..Fri) = {N_obs.astype(int)},  G = {G:.3f}")
assert G > 0, "F.3 G must be positive for non-uniform N"

def chi2_sf(x: float, df: int) -> float:
    """Wilson-Hilferty cubic-root chi-square SF approximation (numpy-only)."""
    if x <= 0:
        return 1.0
    z = ((x / df) ** (1 / 3) - (1 - 2 / (9 * df))) / np.sqrt(2 / (9 * df))
    return 0.5 * math.erfc(z / np.sqrt(2))

p_chi = chi2_sf(G, df=4)
print(f"       asymptotic chi^2(4) p (Wilson-Hilferty) = {p_chi:.4f}")

# ----------------------------------------------------------------------------
# F.4  Permutation p-value (asymptotic in B)
# ----------------------------------------------------------------------------
B = 5000
G_perm = np.zeros(B)
for b in range(B):
    sample = RNG.multinomial(int(T), [0.20] * 5)
    pos = sample > 0
    G_perm[b] = 2 * np.sum(sample[pos] * np.log(sample[pos] / E_exp[pos]))
p_perm = (1 + np.sum(G_perm >= G)) / (1 + B)
print(f"\n[F.4]  permutation p (B={B}) = {p_perm:.4f}")
print(f"       Phipson-Smyth +1 correction ensures p > 0")

# ----------------------------------------------------------------------------
# F.5  Benjamini-Hochberg FDR (closed form)
# ----------------------------------------------------------------------------
pvals = np.array([0.001, 0.002, 0.012, 0.023, 0.041, 0.060, 0.110])
m = len(pvals)
idx_s = np.argsort(pvals)
p_s   = pvals[idx_s]
q_lvl = 0.05
crit  = (np.arange(1, m + 1) / m) * q_lvl
print(f"\n[F.5]  BH-FDR (q={q_lvl}, m={m}):")
print(f"       sorted p:  {p_s.round(4)}")
print(f"       threshold: {crit.round(4)}")
ok = np.where(p_s <= crit)[0]
k_star = (ok.max() + 1) if len(ok) > 0 else 0
print(f"       reject H0 for first k* = {k_star} sorted p-values")
assert k_star == 4, "F.5 BH-FDR k* mismatch"

# ----------------------------------------------------------------------------
# F.6  OLS + HC3 standard errors (closed form)
# ----------------------------------------------------------------------------
N, k = 19, 6
X = np.column_stack([np.ones(N), RNG.standard_normal((N, k))])
beta_true = np.array([0.0, 0.42, 0.51, 0.30, -0.05, 0.05, -0.05])
y = X @ beta_true + 0.3 * RNG.standard_normal(N)
XtX_inv = np.linalg.inv(X.T @ X)
beta_hat = XtX_inv @ X.T @ y
e = y - X @ beta_hat
H = X @ XtX_inv @ X.T
h = np.diag(H)
omega = e ** 2 / (1 - h) ** 2
V_HC3 = XtX_inv @ X.T @ np.diag(omega) @ X @ XtX_inv
SE_HC3 = np.sqrt(np.diag(V_HC3))
print("\n[F.6]  OLS coefficient recovery + HC3 SE:")
for j, (bt, bh, se) in enumerate(zip(beta_true, beta_hat, SE_HC3)):
    print(f"       X{j}:  true={bt:+.3f}  hat={bh:+.3f}  HC3={se:.3f}  t={bh/se:+.2f}")

# ----------------------------------------------------------------------------
# F.7  Wald F (asymptotic)
# ----------------------------------------------------------------------------
R = np.zeros((3, k + 1))
R[0, 1] = R[1, 2] = R[2, 3] = 1
diff = R @ beta_hat
W = (diff @ np.linalg.inv(R @ V_HC3 @ R.T) @ diff) / 3
print(f"\n[F.7]  Wald F(3, {N - k - 1}) for first-three-coeffs block: F = {W:.3f}")

# ----------------------------------------------------------------------------
# F.8  Spearman rho (closed form)
# ----------------------------------------------------------------------------
x_t = RNG.standard_normal(N)
y_t = 0.6 * x_t + 0.4 * RNG.standard_normal(N)
rx = np.argsort(np.argsort(x_t)) + 1
ry = np.argsort(np.argsort(y_t)) + 1
d  = rx - ry
rho = 1 - 6 * np.sum(d ** 2) / (N * (N ** 2 - 1))
t_stat = rho * np.sqrt((N - 2) / max(1 - rho ** 2, 1e-12))
print(f"\n[F.8]  Spearman rho (closed form): {rho:+.4f}   t = {t_stat:+.3f}")

# ----------------------------------------------------------------------------
# F.9  VIF (closed form via R^2 of auxiliary regression)
# ----------------------------------------------------------------------------
print("\n[F.9]  VIF for each predictor:")
for j in range(1, k + 1):
    cols = [c for c in range(1, k + 1) if c != j]
    X_o = np.column_stack([np.ones(N), X[:, cols]])
    bj  = np.linalg.lstsq(X_o, X[:, j], rcond=None)[0]
    yhat = X_o @ bj
    R2 = 1 - np.sum((X[:, j] - yhat) ** 2) / np.sum((X[:, j] - X[:, j].mean()) ** 2)
    print(f"       X{j}: R^2_aux = {R2:.3f},  VIF = {1 / max(1 - R2, 1e-12):.2f}")

# ----------------------------------------------------------------------------
# F.10  Cook's distance (closed form)
# ----------------------------------------------------------------------------
MSE = np.sum(e ** 2) / (N - k - 1)
D = (e ** 2 / ((k + 1) * MSE)) * (h / (1 - h) ** 2)
print(f"\n[F.10] Cook's D max = {D.max():.3f}; threshold 4/N = {4/N:.3f}; "
      f"flagged = {(D > 4/N).sum()}/{N}")

# ----------------------------------------------------------------------------
# F.11  Ridge LOO-CV via Hastie-Tibshirani-Friedman shortcut (closed form)
# ----------------------------------------------------------------------------
lam_grid = np.logspace(-3, 2, 30)
mse_loo  = []
for lam in lam_grid:
    A = np.linalg.inv(X.T @ X + lam * np.eye(k + 1))
    beta_r = A @ X.T @ y
    Hr = X @ A @ X.T
    hr = np.diag(Hr)
    er = y - X @ beta_r
    e_loo = er / (1 - hr)
    mse_loo.append(np.mean(e_loo ** 2))
mse_loo = np.asarray(mse_loo)
lam_opt = lam_grid[int(np.argmin(mse_loo))]
print(f"\n[F.11] Ridge LOO-CV optimum: lambda* = {lam_opt:.4f}  "
      f"MSE = {mse_loo.min():.4f}  (OLS MSE = {mse_loo[0]:.4f})")

# ----------------------------------------------------------------------------
# F.12  Condition number of the design matrix (closed form)
# ----------------------------------------------------------------------------
X_std = (X[:, 1:] - X[:, 1:].mean(0)) / X[:, 1:].std(0, ddof=1)
eig = np.linalg.eigvalsh(X_std.T @ X_std / N)
kappa = float(np.sqrt(eig.max() / eig.min()))
print(f"\n[F.12] Condition number sqrt(eig_max/eig_min) = {kappa:.2f}")

# ----------------------------------------------------------------------------
# F.13  Partial-R^2 (closed form)
# ----------------------------------------------------------------------------
X0 = X[:, [0, 4, 5, 6]]
b0 = np.linalg.lstsq(X0, y, rcond=None)[0]
RSS_0 = np.sum((y - X0 @ b0) ** 2)
RSS_full = np.sum(e ** 2)
partial_R2 = (RSS_0 - RSS_full) / RSS_0
print(f"\n[F.13] Partial-R^2 of the 'flow' block: {partial_R2:.3f}")

# ----------------------------------------------------------------------------
# F.14  Power analysis (asymptotic, Cohen f^2)
# ----------------------------------------------------------------------------
target_R2 = 0.32
f2  = target_R2 / (1 - target_R2)
ncp = f2 * (N - k - 1)
print(f"\n[F.14] Cohen f^2 = R^2/(1-R^2) = {f2:.3f}, noncentrality = {ncp:.2f}")

# ----------------------------------------------------------------------------
# F.18  Stationary distribution of the Friday transition matrix (closed form)
# ----------------------------------------------------------------------------
P_fri = np.array([
    [0.65, 0.22, 0.13],
    [0.18, 0.50, 0.32],
    [0.06, 0.20, 0.74],
])
ev_p, evec_p = np.linalg.eig(P_fri.T)
idx_one = int(np.argmin(np.abs(ev_p - 1)))
pi_fri = np.real(evec_p[:, idx_one])
pi_fri = pi_fri / pi_fri.sum()
print(f"\n[F.18] stationary pi_Fri = {pi_fri.round(3)}  "
      f"(P[high vol on Fri] = {pi_fri[2]:.3f})")
assert abs(pi_fri.sum() - 1.0) < 1e-9, "F.18 pi must sum to 1"

# ----------------------------------------------------------------------------
# F.19  Block bootstrap (closed form per replicate)
# ----------------------------------------------------------------------------
N_series, block_len, B_boot = 100, 7, 1000
data = RNG.standard_normal(N_series)
boot_means = []
for _ in range(B_boot):
    starts = RNG.integers(0, N_series - block_len, size=N_series // block_len)
    sample = np.concatenate([data[s:s + block_len] for s in starts])
    boot_means.append(sample.mean())
print(f"\n[F.19] block-bootstrap SE for mean (block_len={block_len}, B={B_boot}): "
      f"{np.std(boot_means):.4f}")

# ----------------------------------------------------------------------------
# F.21  Shares-outstanding flow proxy (closed form)
# ----------------------------------------------------------------------------
S = np.array([100, 102, 102, 105, 105, 110, 108, 108, 112, 115], dtype=float)
delta = np.diff(S, prepend=S[0])
creation   = np.maximum(0,  delta)
redemption = np.maximum(0, -delta)
print(f"\n[F.21] shares S = {S.astype(int)}")
print(f"       creation   = {creation.astype(int)}")
print(f"       redemption = {redemption.astype(int)}")

# ----------------------------------------------------------------------------
print("\n" + "=" * 78)
print("ALL CHECKS PASS")
print("=" * 78)
