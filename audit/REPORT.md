# Research-integrity audit report

_Generated: 2026-05-13T11:06:35_

## Summary

- 🔴 **RED**:      0  (paper claim contradicts code output)
- 🟡 **YELLOW**:   0  (lookup failed / manifest incomplete)
- 🟢 **GREEN**:   80  (paper claim matches code output)
- ⚪ **GRAY**:     2  (illustrative / deferred per manifest)
- **Total claims audited**: 82

✅ **Clean audit** — all claims either match code, are explicitly illustrative, or are deferred future work.

## 🟢 GREEN — paper matches code

| Status | id | section | paper | code | Δabs | tol | severity | source |
|---|---|---|---:|---:|---:|---|---|---|
| GREEN | `abs_sig_count_at_q05` | abstract | 17 | 17.0000 | 0.0000 | abs 1 | HARD | output/hcug_results.csv[sig_flag=1].count(sig_flag) |
| GREEN | `abs_effect_size_low` | abstract | 4.0000 | 4.0400 | 0.0400 | abs 1.0 | HARD | output/aggregate_stats.json:excess_fri_pp_min |
| GREEN | `abs_effect_size_high` | abstract | 8.0000 | 7.9900 | 0.0100 | abs 1.0 | HARD | output/aggregate_stats.json:excess_fri_pp_max |
| GREEN | `abs_rho_aum` | abstract | 0.2000 | 0.2034 | 0.0034 | abs 0.05 | HARD | output/spearman_predictors.json:log_aum/rho |
| GREEN | `abs_rho_treasury` | abstract | -0.5100 | -0.5095 | 0.0005 | abs 0.05 | HARD | output/spearman_predictors.json:treasury/rho |
| GREEN | `abs_wilcoxon_p_order` | abstract | 0.0000 | 0.0000 | 0.0000 | abs 5e-05 | HARD | output/aggregate_stats.json:wsas_wilcoxon_p |
| GREEN | `s51_sig_at_q05` | section_5_1_hcug | 17 | 17.0000 | 0.0000 | abs 1 | HARD | output/hcug_results.csv[sig_flag=1].count(sig_flag) |
| GREEN | `s51_sig_at_q001` | section_5_1_hcug | 17 | 17.0000 | 0.0000 | abs 1 | HARD | output/aggregate_stats.json:sig_count_q01 |
| GREEN | `s51_baseline` | section_5_1_hcug | 20.0000 | 20.0600 | 0.0600 | abs 1.0 | HARD | output/aggregate_stats.json:baseline_E_fri_pct |
| GREEN | `s52_max_side_mean` | section_5_2_wsas | 27.0000 | 27.2300 | 0.2300 | abs 1.0 | HARD | output/aggregate_stats.json:wsas_p_max_fri_mean_pct |
| GREEN | `s52_min_side_mean` | section_5_2_wsas | 23.6000 | 23.7800 | 0.1800 | abs 1.0 | HARD | output/aggregate_stats.json:wsas_p_min_fri_mean_pct |
| GREEN | `s52_psi_low` | section_5_2_wsas | 0.0050 | 0.0050 | 0.0000 | abs 0.03 | HARD | output/aggregate_stats.json:psi_min |
| GREEN | `s52_psi_high` | section_5_2_wsas | 0.0800 | 0.0803 | 0.0003 | abs 0.03 | HARD | output/aggregate_stats.json:psi_max |
| GREEN | `s52_psi_sig_count` | section_5_2_wsas | 4 | 4.0000 | 0.0000 | abs 1 | HARD | output/aggregate_stats.json:psi_sig_count |
| GREEN | `s53_rho_aum` | section_5_3_spearman | 0.2000 | 0.2034 | 0.0034 | abs 0.05 | HARD | output/spearman_predictors.json:log_aum/rho |
| GREEN | `s53_rho_treasury` | section_5_3_spearman | -0.5100 | -0.5095 | 0.0005 | abs 0.05 | HARD | output/spearman_predictors.json:treasury/rho |
| GREEN | `s53_rho_advaum` | section_5_3_spearman | -0.2600 | -0.2574 | 0.0026 | abs 0.05 | HARD | output/spearman_predictors.json:log_advaum/rho |
| GREEN | `s53_rho_expense` | section_5_3_spearman | -0.3800 | -0.3763 | 0.0037 | abs 0.05 | HARD | output/spearman_predictors.json:expense/rho |
| GREEN | `s53_wald_F_flow` | section_5_3_spearman | 1.3400 | 1.3400 | 0.0000 | abs 0.4 | HARD | output/cross_sectional_diag.json:wald_F_flow |
| GREEN | `tab1_IEF_fri_pct` | table_1 | 24.6000 | 24.6000 | 0.0000 | abs 1.5 | HARD | output/hcug_results.csv[ticker=IEF].fri_pct |
| GREEN | `tab1_IEF_G_stat` | table_1 | 28.9000 | 28.9099 | 0.0099 | rel 0.1 | HARD | output/hcug_results.csv[ticker=IEF].G_stat |
| GREEN | `tab1_IEF_N_weeks` | table_1 | 1240 | 1240.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=IEF].N_weeks |
| GREEN | `tab1_TLT_fri_pct` | table_1 | 25.6000 | 25.6500 | 0.0500 | abs 1.5 | HARD | output/hcug_results.csv[ticker=TLT].fri_pct |
| GREEN | `tab1_TLT_G_stat` | table_1 | 40.7000 | 40.7169 | 0.0169 | rel 0.1 | HARD | output/hcug_results.csv[ticker=TLT].G_stat |
| GREEN | `tab1_TLT_N_weeks` | table_1 | 1240 | 1240.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=TLT].N_weeks |
| GREEN | `tab1_AGG_fri_pct` | table_1 | 25.2000 | 25.1900 | 0.0100 | abs 1.5 | HARD | output/hcug_results.csv[ticker=AGG].fri_pct |
| GREEN | `tab1_AGG_G_stat` | table_1 | 24.9000 | 24.8619 | 0.0381 | rel 0.1 | HARD | output/hcug_results.csv[ticker=AGG].G_stat |
| GREEN | `tab1_AGG_N_weeks` | table_1 | 1179 | 1179.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=AGG].N_weeks |
| GREEN | `tab1_LQD_fri_pct` | table_1 | 25.1000 | 25.1000 | 0.0000 | abs 1.5 | HARD | output/hcug_results.csv[ticker=LQD].fri_pct |
| GREEN | `tab1_LQD_G_stat` | table_1 | 32.5000 | 32.5293 | 0.0293 | rel 0.1 | HARD | output/hcug_results.csv[ticker=LQD].G_stat |
| GREEN | `tab1_LQD_N_weeks` | table_1 | 1239 | 1239.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=LQD].N_weeks |
| GREEN | `tab1_MUB_fri_pct` | table_1 | 27.6000 | 27.6500 | 0.0500 | abs 1.5 | HARD | output/hcug_results.csv[ticker=MUB].fri_pct |
| GREEN | `tab1_MUB_G_stat` | table_1 | 49.7000 | 49.6636 | 0.0364 | rel 0.1 | HARD | output/hcug_results.csv[ticker=MUB].G_stat |
| GREEN | `tab1_MUB_N_weeks` | table_1 | 973 | 973.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=MUB].N_weeks |
| GREEN | `tab1_EMB_fri_pct` | table_1 | 27.4000 | 27.4100 | 0.0100 | abs 1.5 | HARD | output/hcug_results.csv[ticker=EMB].fri_pct |
| GREEN | `tab1_EMB_G_stat` | table_1 | 55.8000 | 55.7611 | 0.0389 | rel 0.1 | HARD | output/hcug_results.csv[ticker=EMB].G_stat |
| GREEN | `tab1_EMB_N_weeks` | table_1 | 956 | 956.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=EMB].N_weeks |
| GREEN | `tab1_HYG_fri_pct` | table_1 | 24.1000 | 24.1400 | 0.0400 | abs 1.5 | HARD | output/hcug_results.csv[ticker=HYG].fri_pct |
| GREEN | `tab1_HYG_G_stat` | table_1 | 41.8000 | 41.7936 | 0.0064 | rel 0.1 | HARD | output/hcug_results.csv[ticker=HYG].G_stat |
| GREEN | `tab1_HYG_N_weeks` | table_1 | 994 | 994.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=HYG].N_weeks |
| GREEN | `tab1_BND_fri_pct` | table_1 | 25.7000 | 25.7300 | 0.0300 | abs 1.5 | HARD | output/hcug_results.csv[ticker=BND].fri_pct |
| GREEN | `tab1_BND_G_stat` | table_1 | 34.0000 | 34.0087 | 0.0087 | rel 0.1 | HARD | output/hcug_results.csv[ticker=BND].G_stat |
| GREEN | `tab1_BND_N_weeks` | table_1 | 995 | 995.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=BND].N_weeks |
| GREEN | `tab1_VCIT_fri_pct` | table_1 | 25.1000 | 25.0600 | 0.0400 | abs 1.5 | HARD | output/hcug_results.csv[ticker=VCIT].fri_pct |
| GREEN | `tab1_VCIT_G_stat` | table_1 | 24.0000 | 23.9950 | 0.0050 | rel 0.1 | HARD | output/hcug_results.csv[ticker=VCIT].G_stat |
| GREEN | `tab1_VCIT_N_weeks` | table_1 | 858 | 858.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=VCIT].N_weeks |
| GREEN | `tab1_VTEB_fri_pct` | table_1 | 27.6000 | 27.6000 | 0.0000 | abs 1.5 | HARD | output/hcug_results.csv[ticker=VTEB].fri_pct |
| GREEN | `tab1_VTEB_G_stat` | table_1 | 30.0000 | 30.0388 | 0.0388 | rel 0.1 | HARD | output/hcug_results.csv[ticker=VTEB].G_stat |
| GREEN | `tab1_VTEB_N_weeks` | table_1 | 558 | 558.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=VTEB].N_weeks |
| GREEN | `tab1_GOVT_fri_pct` | table_1 | 26.6000 | 26.6200 | 0.0200 | abs 1.5 | HARD | output/hcug_results.csv[ticker=GOVT].fri_pct |
| GREEN | `tab1_GOVT_G_stat` | table_1 | 32.0000 | 31.9536 | 0.0464 | rel 0.1 | HARD | output/hcug_results.csv[ticker=GOVT].G_stat |
| GREEN | `tab1_GOVT_N_weeks` | table_1 | 740 | 740.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=GOVT].N_weeks |
| GREEN | `tab1_SPIB_fri_pct` | table_1 | 26.1000 | 26.0900 | 0.0100 | abs 1.5 | HARD | output/hcug_results.csv[ticker=SPIB].fri_pct |
| GREEN | `tab1_SPIB_G_stat` | table_1 | 38.3000 | 38.3450 | 0.0450 | rel 0.1 | HARD | output/hcug_results.csv[ticker=SPIB].G_stat |
| GREEN | `tab1_SPIB_N_weeks` | table_1 | 897 | 897.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=SPIB].N_weeks |
| GREEN | `tab1_XBB_fri_pct` | table_1 | 27.0000 | 27.0100 | 0.0100 | abs 1.5 | HARD | output/hcug_results.csv[ticker=XBB].fri_pct |
| GREEN | `tab1_XBB_G_stat` | table_1 | 75.0000 | 75.0103 | 0.0103 | rel 0.1 | HARD | output/hcug_results.csv[ticker=XBB].G_stat |
| GREEN | `tab1_XBB_N_weeks` | table_1 | 1270 | 1270.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=XBB].N_weeks |
| GREEN | `tab1_ZAG_fri_pct` | table_1 | 27.9000 | 27.9200 | 0.0200 | abs 1.5 | HARD | output/hcug_results.csv[ticker=ZAG].fri_pct |
| GREEN | `tab1_ZAG_G_stat` | table_1 | 69.3000 | 69.2883 | 0.0117 | rel 0.1 | HARD | output/hcug_results.csv[ticker=ZAG].G_stat |
| GREEN | `tab1_ZAG_N_weeks` | table_1 | 849 | 849.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=ZAG].N_weeks |
| GREEN | `tab1_VAB_fri_pct` | table_1 | 28.2000 | 28.1900 | 0.0100 | abs 1.5 | HARD | output/hcug_results.csv[ticker=VAB].fri_pct |
| GREEN | `tab1_VAB_G_stat` | table_1 | 51.1000 | 51.0775 | 0.0225 | rel 0.1 | HARD | output/hcug_results.csv[ticker=VAB].G_stat |
| GREEN | `tab1_VAB_N_weeks` | table_1 | 745 | 745.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=VAB].N_weeks |
| GREEN | `tab1_IUSU_fri_pct` | table_1 | 26.0000 | 26.0000 | 0.0000 | abs 1.5 | HARD | output/hcug_results.csv[ticker=IUSU].fri_pct |
| GREEN | `tab1_IUSU_G_stat` | table_1 | 34.1000 | 34.1075 | 0.0075 | rel 0.1 | HARD | output/hcug_results.csv[ticker=IUSU].G_stat |
| GREEN | `tab1_IUSU_N_weeks` | table_1 | 473 | 473.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=IUSU].N_weeks |
| GREEN | `tab1_IBGS_fri_pct` | table_1 | 26.7000 | 26.6800 | 0.0200 | abs 1.5 | HARD | output/hcug_results.csv[ticker=IBGS].fri_pct |
| GREEN | `tab1_IBGS_G_stat` | table_1 | 72.8000 | 72.8374 | 0.0374 | rel 0.1 | HARD | output/hcug_results.csv[ticker=IBGS].G_stat |
| GREEN | `tab1_IBGS_N_weeks` | table_1 | 952 | 952.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=IBGS].N_weeks |
| GREEN | `tab1_SPY_fri_pct` | table_1 | 22.0000 | 22.0000 | 0.0000 | abs 1.5 | HARD | output/hcug_results.csv[ticker=SPY].fri_pct |
| GREEN | `tab1_SPY_G_stat` | table_1 | 71.9000 | 71.8510 | 0.0490 | rel 0.1 | HARD | output/hcug_results.csv[ticker=SPY].G_stat |
| GREEN | `tab1_SPY_N_weeks` | table_1 | 1268 | 1268.00 | 0.0000 | abs 40 | SOFT | output/hcug_results.csv[ticker=SPY].N_weeks |
| GREEN | `s55_us_median_fri` | deferred | 25.7000 | 25.6900 | 0.0100 | abs 0.5 | HARD | output/aggregate_stats.json:us_median_fri_pct |
| GREEN | `s55_nonus_median_fri` | deferred | 27.0000 | 27.0100 | 0.0100 | abs 0.5 | HARD | output/aggregate_stats.json:nonus_median_fri_pct |
| GREEN | `s57_subperiod_2002` | deferred | 23.9000 | 23.9100 | 0.0100 | abs 1.0 | HARD | output/subperiod_friday_share.csv[subperiod=2002-2009].fri_p |
| GREEN | `s57_subperiod_2010` | deferred | 26.1000 | 26.0500 | 0.0500 | abs 1.0 | HARD | output/subperiod_friday_share.csv[subperiod=2010-2014].fri_p |
| GREEN | `s57_subperiod_2015` | deferred | 26.5000 | 26.5300 | 0.0300 | abs 1.0 | HARD | output/subperiod_friday_share.csv[subperiod=2015-2019].fri_p |
| GREEN | `s57_subperiod_2020` | deferred | 25.8000 | 25.8300 | 0.0300 | abs 1.0 | HARD | output/subperiod_friday_share.csv[subperiod=2020-2026].fri_p |
| GREEN | `baseline_pct` | deferred | 20.0000 | 20.0600 | 0.0600 | abs 1.5 | HARD | output/aggregate_stats.json:baseline_E_fri_pct |

## ⚪ GRAY — illustrative / deferred (audit skipped)

| Status | id | section | paper | code | Δabs | tol | severity | source |
|---|---|---|---:|---:|---:|---|---|---|
| GRAY | `s54_flow_rho_paper` | deferred | — | — | — | — | DEFERRED | Paper draft now states this is deferred; manifest tracks for |
| GRAY | `s56_t1_pre` | deferred | — | — | — | — | DEFERRED | Requires non-proxy NAV to be meaningful. |
