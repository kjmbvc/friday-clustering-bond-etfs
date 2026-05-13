import numpy as np
from sklearn.cluster import KMeans

class MSGARCHParams:
    def __init__(self, K: int, D: int = 5):
        self.K = K
        self.D = D
        self.p_mat = np.zeros((D, K, K))
        self.mu     = np.zeros((K, D))
        self.alpha  = np.zeros((K, D))
        self.beta   = np.zeros((K, D))
        self.gamma  = np.zeros((K, D))

def initialize_parameters(returns, dows, K, D=5, seed=42):

    np.random.seed(seed)
    par = MSGARCHParams(K, D)
    for d in range(D):
        for i in range(K):
            diag_prob = 0.85 + 0.1 * np.random.rand()
            diag_prob = min(0.95, diag_prob)
            par.p_mat[d, i, i] = diag_prob
            remain = 1.0 - diag_prob
            for j in range(K):
                if j != i:
                    par.p_mat[d, i, j] = remain / (K - 1)
    for d in range(D):
        idx = np.where(dows == d)[0]
        if len(idx) >= K:
            vals = returns[idx].reshape(-1,1)
            km = KMeans(n_clusters=K, random_state=seed, n_init=10)
            centers = km.fit(vals).cluster_centers_.flatten()
            for i, c in enumerate(sorted(centers)):
                par.mu[i, d] = c
        else:
            for i in range(K):
                par.mu[i, d] = 0.0005*(i+1)*((d+1)/D)
    par.alpha[:] = 1e-5
    par.beta[:] = 0.1 + 0.05 * np.random.rand(K, D)
    par.gamma[:] = 0.7 + 0.2 * np.random.rand(K, D)
    return par 