# Math-to-code map

Every numbered displayed equation in the paper has an explicit Python
implementation.  This table makes the mapping unambiguous so a reviewer
or a re-implementer can locate each formula instantly.

| Eq.  | Section          | Construct                           | Implementation                                   |
|------|------------------|-------------------------------------|--------------------------------------------------|
| (1)  | §4.1             | Premium definition                  | `code/03_compute_premium.py::compute_premium_per_fund` |
| (2)  | §4.2 / F.2       | Holiday-conditioned E_d             | `utils/permutation.py::_expected_counts` |
| (3)  | §4.2 / F.3       | G-statistic                         | `utils/permutation.py::_g_statistic`     |
| (4)  | §4.3 / F.24      | WSAS psi_i                          | `utils/wsas.py::wsas_statistic`          |
| (F.4)| Appendix F       | Phipson-Smyth permutation p-value   | `utils/permutation.py::phipson_smyth_pvalue` |
| (F.5)| Appendix F       | Benjamini-Hochberg FDR              | `utils/multiple_testing.py::bh_fdr`      |
| (F.6)| Appendix F       | OLS coefficient                     | `utils/regression.py::ols_hc3`           |
| (F.7)| Appendix F       | HC3 covariance                      | `utils/regression.py::ols_hc3`           |
| (F.7')| Appendix F      | Wald F-test                         | `utils/regression.py::wald_test`         |
| (F.8)| Appendix F       | Spearman rho + t-statistic          | `utils/spearman.py::spearman_with_t`     |
| (F.9)| Appendix F       | VIF                                 | `utils/diagnostics.py::vif`              |
| (F.10)| Appendix F      | Cook's distance                     | `utils/diagnostics.py::cooks_distance`   |
| (F.11)| Appendix F      | Ridge LOO-CV                        | `utils/regression.py::ridge_loocv`       |
| (F.12)| Appendix F      | Condition number                    | `utils/diagnostics.py::condition_number` |
| (F.13)| Appendix F      | Partial-R^2                         | `code/07_cross_sectional_ols.py::main`   |
| (F.14)| Appendix F      | Power analysis (f^2, NCP)           | `code/07_cross_sectional_ols.py::main`   |
| (F.15)| Appendix F      | Fractional logit                    | `utils/regression.py::fractional_logit`  |
| (F.16)| Appendix F      | Permutation importance              | `utils/perm_importance.py::permutation_importance` |
| (F.17)| Appendix F      | MSGARCH conditional density         | `code/06_msgarch_via_rpy2.py::fridayshift_via_msgarch` |
| (F.18)| Appendix F      | FridayShift parameter               | `code/06_msgarch_via_rpy2.py::fridayshift_via_msgarch` |
| (F.19)| Appendix F      | Block bootstrap                     | `utils/bootstrap.py::block_bootstrap`    |
| (F.20)| Appendix F      | Threshold tests (reuse F.3-F.5)    | `code/04_hcug_test.py` (sub-sample variants) |
| (F.21)| Appendix F      | Creation/Redemption flow proxy      | `code/08_shares_outstanding_flow.py::main` |
| (F.23)| Appendix F      | HCUG formal derivation              | `utils/permutation.py::hcug_test` (assembled) |
| (F.24)| Appendix F      | WSAS variance + cross-fund          | `utils/wsas.py::wsas_statistic` + `wsas_wilcoxon_global` |

## Random-seed map (paper §4.7)

| Constant in paper                | constants.py        |
|----------------------------------|---------------------|
| Permutation seed 20260101        | `SEED_PERMUTATION`  |
| MSGARCH start 20260102           | `SEED_MSGARCH_START`|
| Ridge LOO-CV grid 20260103       | `SEED_RIDGE_LOOCV`  |
| Block bootstrap 20260104         | `SEED_BLOCK_BOOT`   |

## Verification path

`verification/appendix_F_verification.py` exercises every primitive
with synthetic data of known answer and asserts the computed value
matches.  Last printed line is `ALL CHECKS PASS` on success.

## Test path

`tests/test_*.py` covers HCUG, BH-FDR, OLS+HC3, ridge LOO-CV, and WSAS
with pytest.  Run via `make test`.
