"""v7.4 §7 — Causal mechanism identification roadmap.

This file documents the four mechanism candidates outlined in
§7 of the paper and provides stub functions for the data-fetch
and hypothesis-test pipelines. Each Step is a separate testable
follow-up; the current Letter does NOT identify a mechanism, but
this code lays out the exact path forward so that any successor
researcher can extend the analysis.

Step 1 — Primary-market AP flow concentration (N-CEN filings)
Step 2 — NAV-staleness via Treasury-futures-implied fair value
Step 3 — Intraday VWAP / closing-auction microstructure
Step 4 — Sample expansion to N >= 80 via SEC EDGAR

Usage:
  python code/14_mechanism_roadmap.py
  -> prints data-source URLs, testable-hypothesis specs, feasibility timelines
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import textwrap


# =====================================================================
# Step 1 — N-CEN flow data
# =====================================================================
def step1_ncen_flow_test():
    """
    Hypothesis (H1.1): mu_d (weekday-conditional drift target from OU model)
    correlates with the weekday-conditional gross-flow share at fund-week level.

    Data source: SEC EDGAR N-CEN filings
      https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=N-CEN
      Annual filings; gross issuance/redemption per fund per day.

    Procedure:
      1. Download N-CEN XML files for each of 17 funds, 2018-2025 (post-NSAR/N-CEN transition).
      2. Compute Friday-share of gross AP creation+redemption for each fund-year.
      3. Run panel regression with fund fixed effects:
           mu_Fri,i,year = beta_0 + beta_1 * FlowFriShare_i,year + alpha_i + eps_i,year
      4. Cluster SEs at fund level; wild-cluster bootstrap (Cameron-Gelbach-Miller).

    Identification logic:
      - If beta_1 is significant and large positive -> Friday flow concentration
        directly drives Friday clustering. Institutional-flow channel wins.
      - If beta_1 is null (e.g. wild-cluster p > 0.15), institutional flow does
        NOT directly explain mu_Fri at the panel level. Move to Step 2.

    Feasibility:
      Time: ~3 months (data fetch + XML parsing + panel estimation)
      Cost: free (SEC EDGAR)
      Difficulty: medium (XML schema documentation is incomplete)

    Dependencies:
      - SEC EDGAR access (free)
      - N-CEN XML parser (publicly available since 2019)
    """
    print(textwrap.dedent(step1_ncen_flow_test.__doc__))


# =====================================================================
# Step 2 — Treasury futures fair value
# =====================================================================
def step2_treasury_futures_fairvalue():
    """
    Hypothesis (H2.1): The Friday-share of Close-vs-implied-fair-value spread
    on bond ETFs correlates with the OU mu_Fri ranking.

    Data source: CBOT ZN/ZB minute-level futures prices
      Bloomberg ticker: TYA Index (10Y), USA Index (30Y), minute snapshots.
      Free alternative: yfinance daily, hour interpolation.

    Procedure:
      1. For each minute t in 15:00-16:00 ET (NAV-strike window),
         compute the implied fair value of each bond ETF via:
           FV_i,t = NAV_i,15 + duration_i * (yield_t - yield_15)
      2. Compute Close - FV_i,16 for each day.
      3. Run within-week-paired G-test of Friday concentration of
         Close-FV spread vs. uniform null.

    Identification logic:
      - If Friday share of |Close - FV| > 0 is concentrated > baseline
        (e.g. > 30% for Treasury ETFs), NAV staleness driven by intra-hour
        Treasury yield moves explains a significant fraction of the
        observed Friday clustering.
      - If not, NAV staleness is not the primary channel.

    Feasibility:
      Time: ~3 months
      Cost: $0 if yfinance-only; $100-500/yr if Bloomberg-via-university
      Difficulty: medium (microstructure of Treasury futures)

    Dependencies:
      - Treasury futures data (Bloomberg / yfinance)
      - Duration estimates (issuer fund pages, Bloomberg)
    """
    print(textwrap.dedent(step2_treasury_futures_fairvalue.__doc__))


# =====================================================================
# Step 3 — Intraday VWAP / closing auction
# =====================================================================
def step3_vwap_auction_microstructure():
    """
    Hypothesis (H3.1): The Friday-share of Close-vs-VWAP-15 (closing-auction
    pressure) on Treasury ETFs is concentrated above baseline, indicating
    intraday institutional flow operating through the auction.

    Data source: TAQ (NYSE/AMEX intraday); NYSE OpenView; LOB snapshots.

    Procedure:
      1. For each TAQ minute t in 15:45-16:00 ET, compute:
           VWAP_15(i, t) = sum(p_t * v_t) / sum(v_t) over 15-minute window
         and the closing-auction imbalance from NYSE OpenView.
      2. Define EOD-pressure(i, t) = Close - VWAP_15(i, t), and
         day_aware_dummy = (15:50-16:00 imbalance > 0).
      3. Run G-test: weekday distribution of EOD-pressure > 0 sign.

    Identification logic:
      - Friday concentration of Close > VWAP-15 with positive imbalance =>
        institutional buying pressure at close. Auction-flow channel.
      - Symmetric pre/post-2024 patterns => persistent feature, not driven
        by particular events.

    Feasibility:
      Time: ~6 months (data licensing, calibration)
      Cost: $5,000-15,000/yr (TAQ subscription via WRDS or NYSE)
      Difficulty: high (microstructure expertise + minute-level data)

    Dependencies:
      - TAQ / WRDS access (or NYSE OpenView direct)
      - Time-and-trade reconstruction code (commercial or open-source)
    """
    print(textwrap.dedent(step3_vwap_auction_microstructure.__doc__))


# =====================================================================
# Step 4 — Sample expansion N >= 80
# =====================================================================
def step4_sample_expansion():
    """
    Hypothesis (H4.1): The Friday clustering generalizes to all bond ETFs
    with 5+ year continuous data, regardless of size/age/ESG/leverage status.

    Data source: SEC EDGAR Form N-PORT (quarterly) + Yahoo Finance daily.

    Procedure:
      1. Pull all U.S. bond ETFs from EDGAR with continuous daily data since
         2020 (N >= 80 funds, including ESG, leveraged, niche).
      2. Re-run HCUG + OU+LRT pipeline on the expanded universe.
      3. Decompose by (size_quintile x age_bucket x strategy_class):
           - Small + new + non-Treasury: do they show Friday clustering?
           - Leveraged + ESG: do their Friday-shares correlate with
             benchmark Treasury ETFs of similar duration?

    Identification logic:
      - If small/new ESG funds show identical Friday clustering ->
        structural feature of bond-ETF wrapper, regardless of
        institutional ownership.
      - If only large institutional funds show it -> institutional-flow
        channel is identified by absence in retail-dominated funds.

    Feasibility:
      Time: ~1-2 months (data fetch + replication)
      Cost: free (yfinance + EDGAR)
      Difficulty: low (existing pipeline scales)

    Dependencies:
      - Existing v4 pipeline (this code)
      - SEC EDGAR (free)
    """
    print(textwrap.dedent(step4_sample_expansion.__doc__))


# =====================================================================
# Disjointness and pre-registration helper
# =====================================================================
def print_roadmap_summary():
    print("=" * 72)
    print("v7.4 §7 Causal Mechanism Identification — 4-Step Roadmap")
    print("=" * 72)
    print()
    print("Step | Mechanism                    | Time | Cost   | Status")
    print("-" * 72)
    print("  1  | N-CEN AP flow concentration  | 3mo  | free   | OPEN")
    print("  2  | Treasury futures fair value   | 3mo  | $0-500 | OPEN")
    print("  3  | TAQ / closing auction         | 6mo  | $5-15k | OPEN")
    print("  4  | Sample expansion N >= 80      | 1mo  | free   | OPEN")
    print()
    print("Hypotheses are DISJOINT and pre-registrable. Each step yields a")
    print("standalone Letter / Note contribution; together they constitute")
    print("a complete mechanism identification path.")
    print()
    print("Closed-form OU specification (paper Eq. 3) is the natural vehicle:")
    print("each mechanism enters as exogenous regressor on mu_d or as panel")
    print("control; LRT extends naturally to test mechanism contribution.")


def main():
    print_roadmap_summary()
    print()
    print("\n" + "=" * 72)
    print("Step 1 — N-CEN flow data")
    print("=" * 72)
    step1_ncen_flow_test()
    print("\n" + "=" * 72)
    print("Step 2 — Treasury futures fair value")
    print("=" * 72)
    step2_treasury_futures_fairvalue()
    print("\n" + "=" * 72)
    print("Step 3 — TAQ / closing auction")
    print("=" * 72)
    step3_vwap_auction_microstructure()
    print("\n" + "=" * 72)
    print("Step 4 — Sample expansion")
    print("=" * 72)
    step4_sample_expansion()


if __name__ == "__main__":
    main()
