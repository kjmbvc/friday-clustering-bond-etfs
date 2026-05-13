"""OLS+HC3 (Eq. F.6-F.7), ridge LOO-CV (Eq. F.11), fractional logit (Eq. F.15)."""
from __future__ import annotations
import numpy as np

from constants import SEED_RIDGE_LOOCV


def ols_hc3(X: np.ndarray, y: np.ndarray) -> dict:
    """Eq. (F.6) OLS coefficient + Eq. (F.7) HC3 robust covariance.

    Args:
        X: (n, p) design matrix (include intercept column if desired).
        y: (n,)  response vector.

    Returns:
        dict with beta_hat, se_hc3, V_HC3, e (residuals), H (leverage).
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    # leverage h_{ii}
    H_diag = np.einsum("ij,jk,ik->i", X, XtX_inv, X)
    # HC3 weights e_i^2 / (1 - h_ii)^2
    w = e ** 2 / (1.0 - H_diag) ** 2
    V = XtX_inv @ (X.T * w) @ X @ XtX_inv
    se = np.sqrt(np.diag(V))
    return {"beta_hat": beta, "se_hc3": se, "V_HC3": V, "e": e, "H_diag": H_diag}


def wald_test(beta_hat: np.ndarray, V_hc3: np.ndarray,
              R: np.ndarray, r: np.ndarray | None = None) -> dict:
    """Eq. (F.7') Wald F-test for R beta = r."""
    R = np.asarray(R, dtype=float)
    if r is None:
        r = np.zeros(R.shape[0])
    diff = R @ beta_hat - r
    middle = np.linalg.inv(R @ V_hc3 @ R.T)
    q_R = R.shape[0]
    W = float(diff @ middle @ diff / q_R)
    # F-distribution under HC3 with df1 = q_R, df2 = n - p; we report W as F-stat
    return {"W": W, "df_num": q_R}


def ridge_loocv(X: np.ndarray, y: np.ndarray,
                lambdas: np.ndarray | None = None,
                seed: int = SEED_RIDGE_LOOCV) -> dict:
    """Eq. (F.11) ridge regression with LOO-CV shortcut.

    Uses the closed-form leave-one-out residual e_i^{LOO} = e_i / (1 - H_{ii})
    where H = X (X' X + lambda I)^{-1} X' (no actual leave-one-out refit).
    """
    if lambdas is None:
        lambdas = np.logspace(-2, 4, 30)
    np.random.default_rng(seed)  # not used directly but reserved for future variants
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, p = X.shape
    mse_loo = np.empty(len(lambdas))
    betas = np.empty((len(lambdas), p))
    for i, lam in enumerate(lambdas):
        XtX_lam_inv = np.linalg.inv(X.T @ X + lam * np.eye(p))
        H_diag = np.einsum("ij,jk,ik->i", X, XtX_lam_inv, X)
        beta = XtX_lam_inv @ X.T @ y
        e = y - X @ beta
        e_loo = e / (1.0 - H_diag)
        mse_loo[i] = np.mean(e_loo ** 2)
        betas[i] = beta
    i_star = int(np.argmin(mse_loo))
    return {
        "lambdas": lambdas,
        "mse_loo": mse_loo,
        "betas": betas,
        "lambda_star": float(lambdas[i_star]),
        "beta_star": betas[i_star],
    }


def fractional_logit(X: np.ndarray, y: np.ndarray):
    """Eq. (F.15) fractional logit via QMLE (Papke and Wooldridge 1996).

    Wraps statsmodels GLM with logit link and binomial variance.  The
    response y is a fraction in [0, 1] (not a binary outcome); QMLE
    standard errors use HC3.
    """
    import statsmodels.api as sm
    fam = sm.families.Binomial(link=sm.families.links.Logit())
    model = sm.GLM(y, X, family=fam)
    return model.fit(cov_type="HC3")
