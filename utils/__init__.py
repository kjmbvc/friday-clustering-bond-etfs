"""Mathematical primitives — no I/O, no plotting, no networking."""
from .calendar           import weekday_of, get_trading_calendar
from .permutation        import hcug_test, phipson_smyth_pvalue
from .multiple_testing   import bh_fdr
from .regression         import ols_hc3, ridge_loocv, fractional_logit, wald_test
from .diagnostics        import vif, cooks_distance, condition_number
from .bootstrap          import block_bootstrap, lofo_perturbation
from .wsas               import wsas_statistic, wsas_wilcoxon_global
from .spearman           import spearman_with_t
from .perm_importance    import permutation_importance
