#!/usr/bin/env python3
"""
audit/build_manifest.py
=======================
Build `audit/claims_manifest.json` from the structured entries below.

Run once (or whenever the paper text changes):

    python audit/build_manifest.py

The manifest IS THE SOURCE OF TRUTH for what numbers in `paper/frl_paper.tex`
the audit harness will check.  Every published number should appear here, with
either:

  - `kind: csv`           -> looked up by ticker+column in a pipeline output
  - `kind: csv_aggregate` -> count/mean/min/max of a column with optional filter
  - `kind: json`          -> from a JSON diagnostics file
  - `kind: computed`      -> a pure-Python expression
  - `kind: illustrative`  -> declared decorative; harness skips
  - `severity: DEFERRED`  -> code not yet implemented; harness skips

When the paper changes, edit this file and re-run.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# =============================================================================
# Per-ticker Table 1 published values (from paper/frl_paper.tex lines 385-404).
# (ticker, N_weeks, fri_pct_pub, G_stat_pub, q_band_pub)
# =============================================================================
TABLE1 = [
    # (ticker, N_weeks_paper, fri_pct_paper, G_stat_paper, q_band_paper)
    # Values populated from paper/frl_paper.tex after the 2026-05 honest-
    # revision pass (see audit/REPORT.md history).  AGGH and IS04 are
    # excluded from the published table because yfinance has no data
    # for them as of 2026-04-30.
    ("IEF",  1240, 24.6, 28.9, "<0.001"),
    ("TLT",  1240, 25.6, 40.7, "<0.001"),
    ("AGG",  1179, 25.2, 24.9, "<0.001"),
    ("LQD",  1239, 25.1, 32.5, "<0.001"),
    ("MUB",   973, 27.6, 49.7, "<0.001"),
    ("EMB",   956, 27.4, 55.8, "<0.001"),
    ("HYG",   994, 24.1, 41.8, "<0.001"),
    ("BND",   995, 25.7, 34.0, "<0.001"),
    ("VCIT",  858, 25.1, 24.0, "<0.001"),
    ("VTEB",  558, 27.6, 30.0, "<0.001"),
    ("GOVT",  740, 26.6, 32.0, "<0.001"),
    ("SPIB",  897, 26.1, 38.3, "<0.001"),
    ("XBB",  1270, 27.0, 75.0, "<0.001"),
    ("ZAG",   849, 27.9, 69.3, "<0.001"),
    ("VAB",   745, 28.2, 51.1, "<0.001"),
    ("IUSU",  473, 26.0, 34.1, "<0.001"),
    ("IBGS",  952, 26.7, 72.8, "<0.001"),
    ("SPY",  1268, 22.0, 71.9, "<0.001"),
]


def table1_entries():
    """Per-ETF Table 1 entries: fri_pct, G_stat, q_band, N_weeks."""
    entries = []
    for ticker, N, fri, G, q_band in TABLE1:
        entries.append({
            "id": f"tab1_{ticker}_fri_pct",
            "tex_section": "Table 1",
            "claim_text": f"{ticker} Friday share = {fri}%",
            "paper_value": fri,
            "kind": "csv",
            "csv_path": "output/hcug_results.csv",
            "lookup_key": "ticker",
            "lookup_val": ticker,
            "value_column": "fri_pct",
            "tolerance_type": "percentage_pp",
            "severity": "HARD",
        })
        entries.append({
            "id": f"tab1_{ticker}_G_stat",
            "tex_section": "Table 1",
            "claim_text": f"{ticker} G-statistic = {G}",
            "paper_value": G,
            "kind": "csv",
            "csv_path": "output/hcug_results.csv",
            "lookup_key": "ticker",
            "lookup_val": ticker,
            "value_column": "G_stat",
            "tolerance_type": "g_statistic",
            "severity": "HARD",
        })
        entries.append({
            "id": f"tab1_{ticker}_N_weeks",
            "tex_section": "Table 1",
            "claim_text": f"{ticker} N_weeks = {N}",
            "paper_value": N,
            "kind": "csv",
            "csv_path": "output/hcug_results.csv",
            "lookup_key": "ticker",
            "lookup_val": ticker,
            "value_column": "N_weeks",
            "tolerance_type": "integer_count",
            "tolerance_abs": 40,
            "severity": "SOFT",
            "_note": "small N_weeks slack OK: depends on yfinance trading-day count vs paper's calendar",
        })
    return entries


def abstract_entries():
    return [
        {
            "id": "abs_sig_count_at_q05",
            "tex_section": "Abstract",
            "tex_line": 127,
            "claim_text": "all 17 of 17 funds at q<0.001",
            "paper_value": 17,
            "kind": "csv_aggregate",
            "csv_path": "output/hcug_results.csv",
            "filter": {"sig_flag": 1},
            "value_column": "sig_flag",
            "aggregate": "count",
            "tolerance_type": "integer_count",
            "tolerance_abs": 1,
            "severity": "HARD",
        },
        {
            "id": "abs_effect_size_low",
            "tex_section": "Abstract",
            "tex_line": 128,
            "claim_text": "effect sizes +4 to +8 pp over baseline",
            "paper_value": 4.0,
            "kind": "json",
            "json_path": "output/aggregate_stats.json",
            "key_path": ["excess_fri_pp_min"],
            "tolerance_type": "percentage_pp",
            "tolerance_abs": 1.0,
            "severity": "HARD",
        },
        {
            "id": "abs_effect_size_high",
            "tex_section": "Abstract",
            "tex_line": 128,
            "claim_text": "effect sizes +4 to +8 pp over baseline",
            "paper_value": 8.0,
            "kind": "json",
            "json_path": "output/aggregate_stats.json",
            "key_path": ["excess_fri_pp_max"],
            "tolerance_type": "percentage_pp",
            "tolerance_abs": 1.0,
            "severity": "HARD",
        },
        {
            "id": "abs_rho_aum",
            "tex_section": "Abstract",
            "tex_line": 131,
            "claim_text": "log AUM rho = +0.20 (n.s.)",
            "paper_value": 0.20,
            "kind": "json",
            "json_path": "output/spearman_predictors.json",
            "key_path": ["log_aum", "rho"],
            "tolerance_type": "correlation_rho",
            "severity": "HARD",
        },
        {
            "id": "abs_rho_treasury",
            "tex_section": "Abstract",
            "tex_line": 131,
            "claim_text": "Treasury rho = -0.51 (p=0.04, opposite sign of synthetic prior)",
            "paper_value": -0.51,
            "kind": "json",
            "json_path": "output/spearman_predictors.json",
            "key_path": ["treasury", "rho"],
            "tolerance_type": "correlation_rho",
            "severity": "HARD",
        },
        {
            "id": "abs_wilcoxon_p_order",
            "tex_section": "Abstract",
            "claim_text": "Wilcoxon p approx 1.5e-05",
            "paper_value": 1.5e-05,
            "kind": "json",
            "json_path": "output/aggregate_stats.json",
            "key_path": ["wsas_wilcoxon_p"],
            "tolerance_abs": 5e-05,
            "tolerance_type": "p_value_qualitative",
            "severity": "HARD",
        },
    ]


def section_5_1_entries():
    return [
        {
            "id": "s51_sig_at_q05",
            "tex_section": "5.1 HCUG",
            "tex_line": 367,
            "claim_text": "all 17 of 17 bond ETFs at q < 0.001",
            "paper_value": 17,
            "kind": "csv_aggregate",
            "csv_path": "output/hcug_results.csv",
            "filter": {"sig_flag": 1},
            "value_column": "sig_flag",
            "aggregate": "count",
            "tolerance_type": "integer_count",
            "tolerance_abs": 1,
            "severity": "HARD",
        },
        {
            "id": "s51_sig_at_q001",
            "tex_section": "5.1 HCUG",
            "claim_text": "17 of 17 bond ETFs at q<0.001",
            "paper_value": 17,
            "kind": "json",
            "json_path": "output/aggregate_stats.json",
            "key_path": ["sig_count_q01"],
            "tolerance_type": "integer_count",
            "tolerance_abs": 1,
            "severity": "HARD",
        },
        {
            "id": "s51_baseline",
            "tex_section": "5.1 HCUG",
            "claim_text": "holiday-conditioned baseline ~20%",
            "paper_value": 20.0,
            "kind": "json",
            "json_path": "output/aggregate_stats.json",
            "key_path": ["baseline_E_fri_pct"],
            "tolerance_type": "percentage_pp",
            "tolerance_abs": 1.0,
            "severity": "HARD",
        },
    ]


def section_5_2_wsas_entries():
    return [
        {
            "id": "s52_max_side_mean",
            "tex_section": "5.2 WSAS",
            "claim_text": "max-side average 27.0%",
            "paper_value": 27.0,
            "kind": "json",
            "json_path": "output/aggregate_stats.json",
            "key_path": ["wsas_p_max_fri_mean_pct"],
            "tolerance_type": "percentage_pp",
            "tolerance_abs": 1.0,
            "severity": "HARD",
        },
        {
            "id": "s52_min_side_mean",
            "tex_section": "5.2 WSAS",
            "claim_text": "min-side average 23.6%",
            "paper_value": 23.6,
            "kind": "json",
            "json_path": "output/aggregate_stats.json",
            "key_path": ["wsas_p_min_fri_mean_pct"],
            "tolerance_type": "percentage_pp",
            "tolerance_abs": 1.0,
            "severity": "HARD",
        },
        {
            "id": "s52_psi_low",
            "tex_section": "5.2 WSAS",
            "claim_text": "psi range low = +0.005",
            "paper_value": 0.005,
            "kind": "json",
            "json_path": "output/aggregate_stats.json",
            "key_path": ["psi_min"],
            "tolerance_type": "psi_asymmetry",
            "severity": "HARD",
        },
        {
            "id": "s52_psi_high",
            "tex_section": "5.2 WSAS",
            "claim_text": "psi range high = +0.080",
            "paper_value": 0.080,
            "kind": "json",
            "json_path": "output/aggregate_stats.json",
            "key_path": ["psi_max"],
            "tolerance_type": "psi_asymmetry",
            "severity": "HARD",
        },
        {
            "id": "s52_psi_sig_count",
            "tex_section": "5.2 WSAS",
            "claim_text": "4 of 17 bond ETFs reject psi=0 at p<0.05",
            "paper_value": 4,
            "kind": "json",
            "json_path": "output/aggregate_stats.json",
            "key_path": ["psi_sig_count"],
            "tolerance_type": "integer_count",
            "tolerance_abs": 1,
            "severity": "HARD",
        },
    ]


def section_5_3_entries():
    return [
        {
            "id": "s53_rho_aum",
            "tex_section": "5.3 Spearman",
            "claim_text": "log AUM rho = +0.20 (p=0.43)",
            "paper_value": 0.20,
            "kind": "json",
            "json_path": "output/spearman_predictors.json",
            "key_path": ["log_aum", "rho"],
            "tolerance_type": "correlation_rho",
            "severity": "HARD",
        },
        {
            "id": "s53_rho_treasury",
            "tex_section": "5.3 Spearman",
            "claim_text": "Treasury indicator rho = -0.51 (p=0.04, opposite sign of prior)",
            "paper_value": -0.51,
            "kind": "json",
            "json_path": "output/spearman_predictors.json",
            "key_path": ["treasury", "rho"],
            "tolerance_type": "correlation_rho",
            "severity": "HARD",
        },
        {
            "id": "s53_rho_advaum",
            "tex_section": "5.3 Spearman",
            "claim_text": "log(ADV/AUM) rho = -0.26 (p=0.32)",
            "paper_value": -0.26,
            "kind": "json",
            "json_path": "output/spearman_predictors.json",
            "key_path": ["log_advaum", "rho"],
            "tolerance_type": "correlation_rho",
            "severity": "HARD",
        },
        {
            "id": "s53_rho_expense",
            "tex_section": "5.3 Spearman",
            "claim_text": "expense ratio rho = -0.38 (p=0.14)",
            "paper_value": -0.38,
            "kind": "json",
            "json_path": "output/spearman_predictors.json",
            "key_path": ["expense", "rho"],
            "tolerance_type": "correlation_rho",
            "severity": "HARD",
        },
        {
            "id": "s53_wald_F_flow",
            "tex_section": "5.3 Spearman",
            "claim_text": "flow-block Wald F = 1.34",
            "paper_value": 1.34,
            "kind": "json",
            "json_path": "output/cross_sectional_diag.json",
            "key_path": ["wald_F_flow"],
            "tolerance_type": "wald_F",
            "tolerance_abs": 0.4,
            "severity": "HARD",
        },
    ]


def deferred_entries():
    """Claims now anchored to code outputs after the 2026-05 honest-revision pass.

    Items that remain DEFERRED are those where the underlying analysis is not
    implemented in this iteration of the pipeline.
    """
    return [
        # ---- Newly anchored (was DEFERRED, now measurable) ------------------
        {"id": "s55_us_median_fri", "tex_section": "5.5 US/non-US",
         "claim_text": "median Friday share 25.7% (12 US bond ETFs)",
         "paper_value": 25.7, "kind": "json",
         "json_path": "output/aggregate_stats.json",
         "key_path": ["us_median_fri_pct"],
         "tolerance_type": "percentage_pp", "tolerance_abs": 0.5,
         "severity": "HARD"},
        {"id": "s55_nonus_median_fri", "tex_section": "5.5 US/non-US",
         "claim_text": "median Friday share 27.0% (5 non-US bond ETFs)",
         "paper_value": 27.0, "kind": "json",
         "json_path": "output/aggregate_stats.json",
         "key_path": ["nonus_median_fri_pct"],
         "tolerance_type": "percentage_pp", "tolerance_abs": 0.5,
         "severity": "HARD"},
        {"id": "s57_subperiod_2002", "tex_section": "5.7 Sub-period",
         "claim_text": "23.9% in 2002-2009 sub-period (median, 9 US bond ETFs available)",
         "paper_value": 23.9, "kind": "csv",
         "csv_path": "output/subperiod_friday_share.csv",
         "lookup_key": "subperiod", "lookup_val": "2002-2009",
         "value_column": "fri_pct_median",
         "tolerance_type": "percentage_pp", "tolerance_abs": 1.0,
         "severity": "HARD"},
        {"id": "s57_subperiod_2010", "tex_section": "5.7 Sub-period",
         "claim_text": "26.1% in 2010-2014 sub-period",
         "paper_value": 26.1, "kind": "csv",
         "csv_path": "output/subperiod_friday_share.csv",
         "lookup_key": "subperiod", "lookup_val": "2010-2014",
         "value_column": "fri_pct_median",
         "tolerance_type": "percentage_pp", "tolerance_abs": 1.0,
         "severity": "HARD"},
        {"id": "s57_subperiod_2015", "tex_section": "5.7 Sub-period",
         "claim_text": "26.5% in 2015-2019 sub-period",
         "paper_value": 26.5, "kind": "csv",
         "csv_path": "output/subperiod_friday_share.csv",
         "lookup_key": "subperiod", "lookup_val": "2015-2019",
         "value_column": "fri_pct_median",
         "tolerance_type": "percentage_pp", "tolerance_abs": 1.0,
         "severity": "HARD"},
        {"id": "s57_subperiod_2020", "tex_section": "5.7 Sub-period",
         "claim_text": "25.8% in 2020-2026 sub-period",
         "paper_value": 25.8, "kind": "csv",
         "csv_path": "output/subperiod_friday_share.csv",
         "lookup_key": "subperiod", "lookup_val": "2020-2026",
         "value_column": "fri_pct_median",
         "tolerance_type": "percentage_pp", "tolerance_abs": 1.0,
         "severity": "HARD"},
        {"id": "baseline_pct", "tex_section": "4 (HCUG)",
         "claim_text": "20% holiday-conditioned baseline",
         "paper_value": 20.0, "kind": "json",
         "json_path": "output/aggregate_stats.json",
         "key_path": ["baseline_E_fri_pct"],
         "tolerance_type": "percentage_pp",
         "tolerance_abs": 1.5, "severity": "HARD"},

        # ---- Still DEFERRED (analysis not implemented this iteration) -----
        {"id": "s54_flow_rho_paper", "tex_section": "5.4 Flow",
         "claim_text": "rho(FridayShift, flow proxy) -- not computed under proxy NAV",
         "paper_value": None, "kind": "computed", "expr": "0",
         "tolerance_type": "correlation_rho", "severity": "DEFERRED",
         "_note": "Paper draft now states this is deferred; manifest tracks for completeness."},
        {"id": "s56_t1_pre", "tex_section": "5.6 T+1",
         "claim_text": "T+1 pre/post stratification -- deferred to future work",
         "paper_value": None, "kind": "computed", "expr": "0",
         "tolerance_type": "percentage_pp", "severity": "DEFERRED",
         "_note": "Requires non-proxy NAV to be meaningful."},
    ]


def main() -> int:
    manifest = {
        "schema_version": "1.0",
        "_README": ("Master registry of every numerical claim in paper/frl_paper.tex. "
                    "Edit audit/build_manifest.py and re-run to regenerate. "
                    "See audit/README.md for the audit principle."),
        "claims": [
            {"section_id": "abstract", "entries": abstract_entries()},
            {"section_id": "section_5_1_hcug", "entries": section_5_1_entries()},
            {"section_id": "section_5_2_wsas", "entries": section_5_2_wsas_entries()},
            {"section_id": "section_5_3_spearman", "entries": section_5_3_entries()},
            {"section_id": "table_1", "entries": table1_entries()},
            {"section_id": "deferred", "entries": deferred_entries()},
        ],
    }
    total = sum(len(s["entries"]) for s in manifest["claims"])
    by_sev = {}
    for s in manifest["claims"]:
        for e in s["entries"]:
            sev = e.get("severity", "HARD")
            by_sev[sev] = by_sev.get(sev, 0) + 1
    out = REPO / "audit" / "claims_manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[manifest] wrote {out.relative_to(REPO)}")
    print(f"[manifest] {total} entries; severity breakdown: {by_sev}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
