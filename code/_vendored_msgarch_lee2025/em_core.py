import numpy as np, math, copy
from math import log, sqrt, pi
from scipy.optimize import minimize

from .utils  import EPS, S, HUBER_C, TEMP0, RIDGE_TAU, scad_clip
from .params import initialize_parameters, MSGARCHParams

def log_sum_exp(vals):
    m = np.max(vals)
    return m + np.log(np.sum(np.exp(vals - m)) + 1e-12)

def forward_backward_EM(returns, dows, par, lam_scad, em_iter=0):
    K, D, T = par.K, par.D, len(returns)
    eps = 1e-12
    sigma2 = np.zeros((T,K))
    for i in range(K):
        a,b,g = par.alpha[i,dows[0]], par.beta[i,dows[0]], par.gamma[i,dows[0]]
        sigma2[0,i] = a/max(eps,1-b-g)
    for t in range(1, T):
        dt   = dows[t]
        dtm1 = dows[t-1]                    
        for i in range(K):
            a     = par.alpha[i, dt]
            b     = par.beta[i, dt]
            g     = par.gamma[i, dt]
            resid = returns[t-1] - par.mu[i, dtm1]  
            raw_var = a + b*resid**2 + g*sigma2[t-1,i]
            sigma2[t,i] = max(eps, scad_clip(raw_var, lam=lam_scad))

    alpha_log = np.full((T,K), -np.inf)
    loglik = 0.0
    for t in range(T):
        for i in range(K):
            ll_e = -0.5*(np.log(2*pi*sigma2[t,i]) + (returns[t]-par.mu[i,dows[t]])**2/sigma2[t,i])
            if t==0:
                alpha_log[t,i] = np.log(1.0/K) + ll_e
            else:
                prev = alpha_log[t-1] + np.log(par.p_mat[dows[t],:,i]+eps)
                alpha_log[t,i] = ll_e + log_sum_exp(prev)
        loglik += log_sum_exp(alpha_log[t])
        alpha_log[t] -= log_sum_exp(alpha_log[t]) 

        if HUBER_C > 0:
            resid = returns[t] - par.mu[:, dows[t]]
            psi   = np.minimum(1.0,
                     HUBER_C / (np.abs(resid)/(np.sqrt(sigma2[t])+EPS)+EPS))
            psi   = np.clip(psi, 1e-6, 1.0)
            alpha_log[t] += np.log(psi)

    beta_log = np.full((T,K), -np.inf)
    beta_log[-1] = 0.0
    for t in range(T-2,-1,-1):
        for i in range(K):
            terms = []
            for j in range(K):
                ll_e = -0.5*(np.log(2*pi*sigma2[t+1,j]) +
                             (returns[t+1]-par.mu[j,dows[t+1]])**2/sigma2[t+1,j])
                terms.append(beta_log[t+1,j] + np.log(par.p_mat[dows[t+1],i,j]+eps) + ll_e)
            beta_log[t,i] = log_sum_exp(np.array(terms))
        beta_log[t] -= log_sum_exp(beta_log[t])

    xi_log = alpha_log + beta_log
    xi = np.exp(xi_log - xi_log.max(axis=1,keepdims=True))

    Temp = max(1.0, TEMP0 * (0.9**em_iter))
    xi   = xi**(1.0/Temp)
    xi /= xi.sum(axis=1,keepdims=True)

    xi2 = np.zeros((T-1,K,K))
    for t in range(T-1):
        log_num = (
            alpha_log[t,:,None]
            + np.log(par.p_mat[dows[t+1]]+eps)
            + (-0.5*(np.log(2*pi*sigma2[t+1]) +
                     (returns[t+1]-par.mu[:,dows[t+1]])**2/sigma2[t+1]))[None,:]
            + beta_log[t+1][None,:]
        )
        m = log_num.max()
        xi2[t] = np.exp(log_num-m)
        xi2[t] /= xi2[t].sum()

    return xi, xi2, sigma2, loglik

def M_step(returns, dows, par, xi, xi2, sigma2):
    K = par.K
    D = par.D
    T = len(returns)
    eps = 1e-12

    new_p = np.zeros_like(par.p_mat)
    for t in range(T-1):
        d_next = dows[t+1]
        for i in range(K):
            for j in range(K):
                new_p[d_next, i, j] += xi2[t, i, j]
    for d in range(D):
        for i in range(K):
            denom = np.sum(new_p[d, i, :])
            if denom < eps:
                new_p[d, i, :] = par.p_mat[d, i, :]
            else:
                new_p[d, i, :] /= denom
    par.p_mat = new_p

    new_mu = np.zeros_like(par.mu)
    sum_w  = np.zeros((K, D))
    for t in range(T):
        dt = dows[t]
        for i in range(K):
            w_i = xi[t, i]
            new_mu[i, dt] += w_i*returns[t]
            sum_w[i, dt]  += w_i
    for i in range(K):
        for d in range(D):
            if sum_w[i, d] > 1e-12:
                par.mu[i, d] = new_mu[i, d]/sum_w[i, d]
    
    def garch_negloglike_param(x, idx, i, mu_i):
        w = np.clip(x[0], -20, 20)
        u = np.clip(x[1], -10, 10)
        v = np.clip(x[2], -10, 10)
        alpha = np.exp(w)
        ru, rv = np.exp(u), np.exp(v)
        denom = 1.0 + ru + rv
        beta  = S * ru / denom
        gamma = S * rv / denom

        negll = 0.0
        for t in idx:
            if t == 0: continue
            dt, dtm1 = dows[t], dows[t-1]
            w_ji = xi2[t-1, :, i]; w_ji /= (w_ji.sum() + eps)
            resid2 = (returns[t-1] - par.mu[:, dtm1])**2
            s2prev = sigma2[t-1, :]
            s2_ti  = alpha + beta*(w_ji @ resid2) + gamma*(w_ji @ s2prev)

            res  = returns[t] - mu_i[dt]
            ll_t = -0.5*(math.log(2*pi*s2_ti) + res**2/s2_ti)
            negll -= xi[t, i] * ll_t
        negll += (alpha**2 + beta**2 + gamma**2) / (2 * RIDGE_TAU**2)
        return negll
    
    for i in range(K):
        mu_i = par.mu[i]
        for d in range(D):
            idx = np.where(dows==d)[0]
            if len(idx) < 2: 
                continue

            a0, b0, g0 = par.alpha[i,d], par.beta[i,d], par.gamma[i,d]
            sum_bg = b0 + g0
            sum_bg = min(sum_bg, S - 1e-8)
            den1 = max(S - sum_bg, 1e-8)
            T0   = sum_bg / den1

            if sum_bg > 0:
                frac_b = b0 / sum_bg
                frac_g = g0 / sum_bg
            else:
                frac_b = frac_g = 0.5

            ru0 = max(T0 * frac_b, 1e-8)
            rv0 = max(T0 * frac_g, 1e-8)

            w0 = np.log(max(a0, 1e-8))
            u0 = np.log(ru0)
            v0 = np.log(rv0)
            x0 = [w0, u0, v0]

            bounds = [(-20,20), (-10,10), (-10,10)]
            res = minimize(
                garch_negloglike_param, x0,
                args=(idx, i, mu_i),
                method='L-BFGS-B',
                bounds=bounds,
                options={'maxiter':100}
            )

            if res.success:
                w_opt, u_opt, v_opt = res.x
                a_opt = np.exp(w_opt)
                ru, rv = np.exp(u_opt), np.exp(v_opt)
                den2 = max(1.0 + ru + rv, 1e-8)
                b_opt = S * ru / den2
                g_opt = S * rv / den2
                # β+γ 1 (stationarity)
                if b_opt + g_opt >= S:
                    scale = S*0.99 / (b_opt + g_opt)
                    b_opt *= scale
                    g_opt *= scale
                par.alpha[i,d], par.beta[i,d], par.gamma[i,d] = a_opt, b_opt, g_opt
    
    return par

def em_fit_ms_garch(returns, dows, lam_scad, K=2, max_iter=250, tol=1e-5, verbose=False):

    par = initialize_parameters(returns, dows, K, D=5)
    old_par = None
    old_ll  = None
    T = len(returns)
    
     for it in range(max_iter):
        xi, xi2, sigma2, loglik = forward_backward_EM(returns, dows, par, lam_scad, em_iter=it)
        new_par = M_step(returns, dows, par, xi, xi2, sigma2)
        if old_par is not None and old_ll is not None:
            dpar = param_distance(old_par,new_par)
            dll  = abs(loglik - old_ll)
            if verbose:
                print(f"Iter {it}: Δparam={dpar:.2e}, Δll={dll:.2e}")
            if dpar<tol and dll<tol:
                break
        elif verbose:
            print(f"Iter {it}: ll={loglik:.4f}")
        old_par, old_ll = copy.deepcopy(new_par), loglik
        par = new_par
    return par

from .utils import compute_lam_scad

def fit_ms_garch_multi(ret, dow, K, n_start=12):

    lam_scad = compute_lam_scad(ret)
    cand = []
    for s in range(n_start):
        np.random.seed(100+s)
        p = em_fit_ms_garch(ret, dow, lam_scad, K=K, verbose=False)
        _, _, _, ll = forward_backward_EM(ret, dow, p, lam_scad)
        cand.append((ll, p))
    best = max(cand, key=lambda x: x[0])[1]
    return best

def param_distance(parA, parB):
    dist = np.sqrt(
        np.sum((parA.p_mat - parB.p_mat)**2) +
        np.sum((parA.mu - parB.mu)**2) +
        np.sum((parA.alpha - parB.alpha)**2) +
        np.sum((parA.beta  - parB.beta)**2) +
        np.sum((parA.gamma - parB.gamma)**2)
    )
    return dist
