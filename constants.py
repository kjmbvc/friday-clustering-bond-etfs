"""Centralized constants — random seeds, fund tickers, file paths.

Imported by every script in code/ and tests/ to keep the configuration
single-source-of-truth.
"""
from pathlib import Path

# --- random seeds (referenced from §4.7 Reproducibility of the paper) ---
SEED_PERMUTATION   = 20260101
SEED_MSGARCH_START = 20260102
SEED_RIDGE_LOOCV   = 20260103
SEED_BLOCK_BOOT    = 20260104

# --- 19 bond ETFs + SPY benchmark (§3 Data) ---
TICKERS_US_ISHARES   = ["IEF", "TLT", "AGG", "LQD", "MUB", "EMB", "HYG"]
TICKERS_US_VANGUARD  = ["BND", "VCIT", "VTEB"]
TICKERS_US_SSGA      = ["GOVT", "SPIB"]
TICKERS_CANADIAN     = ["XBB", "ZAG", "VAB"]
TICKERS_UCITS        = ["IUSU", "AGGH", "IBGS", "IS04"]
TICKER_BENCHMARK     = "SPY"
TICKERS_BOND_19 = (TICKERS_US_ISHARES + TICKERS_US_VANGUARD +
                   TICKERS_US_SSGA + TICKERS_CANADIAN + TICKERS_UCITS)
TICKERS_ALL_20 = TICKERS_BOND_19 + [TICKER_BENCHMARK]

# --- weekday encoding (Mon=0 ... Fri=4); week_of-week skipped (5,6) ---
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri"]
FRIDAY = 4

# --- statistical thresholds ---
FDR_LEVEL_PRIMARY   = 0.05
FDR_LEVEL_TERTIARY  = 0.05
PERMUTATION_REPS    = 10_000
BLOCK_BOOTSTRAP_LEN = 5      # one trading week per block

# --- file paths (relative to repo root) ---
ROOT          = Path(__file__).parent
DATA_DIR      = ROOT / "data"
DATA_RAW      = DATA_DIR / "raw"
DATA_PROC     = DATA_DIR / "processed"
OUTPUT_DIR    = ROOT / "output"
FIGURE_DIR    = OUTPUT_DIR / "figures"
FUND_METADATA = DATA_DIR / "fund_metadata.csv"
PREMIUMS_CSV  = DATA_PROC / "premiums.csv"

for d in (DATA_RAW, DATA_PROC, OUTPUT_DIR, FIGURE_DIR):
    d.mkdir(parents=True, exist_ok=True)
