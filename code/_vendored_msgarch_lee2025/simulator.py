import numpy as np, math
from .utils import EPS, scad_clip

def simulate_ms_garch(model_par, dows, lam_scad, T, P0=10000, seed=999):
    np.random.seed(seed)
    K = model_par.K
    D = model_par.D
    prices = np.zeros(T)
    returns_sim = np.zeros(T)
    states_sim  = np.zeros(T, dtype=int)
    sigma2_sim  = np.zeros(T)

    st = np.random.choice(K)
    states_sim[0] = st
    d0 = dows[0]
    a0 = model_par.alpha[st, d0]
    b0 = model_par.beta[st, d0]
    g0 = model_par.gamma[st, d0]
    denom = max(1e-12, (1-b0-g0))
    sigma2_sim[0] = a0/denom
    returns_sim[0] = np.random.normal(model_par.mu[st,d0], math.sqrt(sigma2_sim[0]))
    prices[0] = P0*math.exp(returns_sim[0])
    
    for t in range(1, T):
        d_t = dows[t]
        trans_prob = model_par.p_mat[d_t, st, :]
        st_new = np.random.choice(K, p=trans_prob)

        resid_prev = returns_sim[t-1] - model_par.mu[st, dows[t-1]]
        alpha_ = model_par.alpha[st_new, d_t]
        beta_  = model_par.beta[st_new, d_t]
        gamma_ = model_par.gamma[st_new, d_t]
        raw_var       = alpha_ + beta_*(resid_prev**2) + gamma_*sigma2_sim[t-1]
        sigma2_sim[t] = max(1e-10, scad_clip(raw_var, lam=lam_scad))
        mu_ = model_par.mu[st_new, d_t]
        ret_ = np.random.normal(mu_, math.sqrt(sigma2_sim[t]))
        ret_ = max(min(ret_, 50), -50) 
        prices[t] = prices[t-1]*math.exp(ret_)
        
        returns_sim[t] = ret_
        prices[t] = prices[t-1]*math.exp(ret_)
        states_sim[t] = st_new
        st = st_new
    
    return prices, returns_sim, states_sim, sigma2_sim

    
