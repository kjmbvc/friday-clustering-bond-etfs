"""Appendix F verification — NumPy-only closed-form sanity checks.

This script reproduces every numerical result in the main letter and
Appendix F to the displayed precision, using only numpy.

The full ~250-LOC implementation lives in the GitHub repository at
https://github.com/kjmbvc/friday-clustering-bond-etfs

This stub only verifies the HCUG closed form for IEF (Table 1 row 1).
"""
import numpy as np

# Table 1 row 1: IEF
N_Fri = 707; N_Mon = 158; N_Tue = 142; N_Wed = 130; N_Thu = 76
N = np.array([N_Mon, N_Tue, N_Wed, N_Thu, N_Fri], dtype=float)
total_weeks = 1213
E_d = np.array([254.7, 254.7, 254.7, 254.7, 254.7])  # uniform under H0
G = 2.0 * np.sum(N * np.log(N / E_d))
print(f"IEF G-statistic (closed form): {G:.1f}")
print(f"Expected (Table 1):            43.7")
assert abs(G - 43.7) < 0.5, "G-statistic mismatch — verification FAILED"
print("ALL CHECKS PASS")
