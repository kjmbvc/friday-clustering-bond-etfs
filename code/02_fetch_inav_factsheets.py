"""Step 2 — daily iNAV from issuer factsheet PDFs (2018-2026 sub-sample).

Real implementation should scrape issuer factsheet pages or use the
free intraday-NAV feeds many ETF providers publish.  This stub produces
a synthetic iNAV = NAV + uniform noise so the downstream pipeline runs.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from constants import TICKERS_BOND_19, DATA_RAW, SEED_PERMUTATION


def main() -> None:
    rng = np.random.default_rng(SEED_PERMUTATION)
    for tkr in TICKERS_BOND_19:
        out = DATA_RAW / f"{tkr}_inav.csv"
        if out.exists():
            continue
        nav = pd.read_csv(DATA_RAW / f"{tkr}_nav.csv", parse_dates=["date"])
        nav = nav[nav["date"] >= "2018-01-01"].copy()
        nav["inav"] = nav["nav"] * (1 + rng.normal(0, 1e-4, size=len(nav)))
        nav[["date", "inav"]].to_csv(out, index=False)
        print(f"  [{tkr}] iNAV (synthetic stub) -> {out.name}")
    print("Step 2 complete (replace stub with real issuer-page scraping for production).")


if __name__ == "__main__":
    main()
