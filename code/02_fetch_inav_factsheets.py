#!/usr/bin/env python3
"""
02_fetch_inav_factsheets.py
===========================
Daily intraday-NAV (iNAV) for the 2018-2026 sub-sample.

iNAV is published in issuer factsheet PDFs and is NOT available via yfinance.
This script does two things:

1.  Documents the canonical issuer factsheet URLs per ticker.
2.  Parses any pre-downloaded PDF found in   data/raw/factsheets/<TICKER>_*.pdf
    using `pypdf` (lightweight, pure-Python) and writes
    data/raw/<TICKER>_inav.csv  with columns date, inav.

If no PDFs are present, the script writes a SKELETON inav file
(data/raw/<TICKER>_inav.csv with header only) so that 03_compute_premium.py
falls back to the 5-day MA NAV proxy from 01.

Inputs
------
data/fund_metadata.csv
data/raw/factsheets/<TICKER>_*.pdf      # OPTIONAL pre-downloaded factsheets

Output
------
data/raw/<TICKER>_inav.csv              # date, inav   (may be empty if no PDFs)
data/raw/_inav_sources.csv              # ticker, url  (canonical issuer page)

Usage
-----
    python code/02_fetch_inav_factsheets.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

REPO   = Path(__file__).resolve().parent.parent
META   = REPO / "data" / "fund_metadata.csv"
RAW    = REPO / "data" / "raw"
SHEETS = RAW / "factsheets"
RAW.mkdir(parents=True, exist_ok=True)

# Canonical issuer factsheet pages (manual download).  iNAV historical series
# typically requires the issuer's "fund detail" or "intraday data" download.
ISSUER_URLS = {
    # iShares (US)
    "IEF":  "https://www.ishares.com/us/products/239456/ishares-7-10-year-treasury-bond-etf",
    "TLT":  "https://www.ishares.com/us/products/239454/ishares-20-year-treasury-bond-etf",
    "AGG":  "https://www.ishares.com/us/products/239458/ishares-core-total-us-bond-market-etf",
    "LQD":  "https://www.ishares.com/us/products/239566/ishares-iboxx-investment-grade-corporate-bond-etf",
    "MUB":  "https://www.ishares.com/us/products/239766/ishares-national-amt-free-muni-bond-etf",
    "EMB":  "https://www.ishares.com/us/products/239572/ishares-jp-morgan-usd-emerging-markets-bond-etf",
    "HYG":  "https://www.ishares.com/us/products/239565/ishares-iboxx-high-yield-corporate-bond-etf",
    # Vanguard
    "BND":  "https://investor.vanguard.com/investment-products/etfs/profile/bnd",
    "VCIT": "https://investor.vanguard.com/investment-products/etfs/profile/vcit",
    "VTEB": "https://investor.vanguard.com/investment-products/etfs/profile/vteb",
    # State Street
    "GOVT": "https://www.ssga.com/us/en/individual/etfs/funds/spdr-portfolio-treasury-etf-spty",
    "SPIB": "https://www.ssga.com/us/en/individual/etfs/funds/spdr-portfolio-intermediate-term-corporate-bond-etf-spib",
    # Canadian
    "XBB":  "https://www.blackrock.com/ca/individual/en/products/239491/ishares-canadian-universe-bond-index-etf",
    "ZAG":  "https://www.bmoetfs.ca/en/Pages/ProductDetail.aspx?TickerSymbol=ZAG",
    "VAB":  "https://www.vanguardcanada.ca/individual/products/en/detail/etf/9554/cad",
    # UCITS
    "IUSU": "https://www.ishares.com/uk/individual/en/products/251867/ishares-msci-usa-ucits-etf",
    "AGGH": "https://www.ishares.com/uk/individual/en/products/287374",
    "IBGS": "https://www.ishares.com/uk/individual/en/products/251732/ishares-eb-rexx-government-germany-1-3yr-ucits-etf",
    "IS04": "https://www.ishares.com/uk/individual/en/products/251733/ishares-eb-rexx-government-germany-7-10yr-ucits-etf",
    # SPY
    "SPY":  "https://www.ssga.com/us/en/individual/etfs/funds/spdr-sp-500-etf-trust-spy",
}

# Regex for "MM/DD/YYYY  $XX.XX" or "YYYY-MM-DD  XX.XX" lines in factsheets.
_PAT = re.compile(
    r"(?P<date>\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}|\d{4}[\-/]\d{1,2}[\-/]\d{1,2})\s+"
    r"\$?\s*(?P<inav>\d{1,4}\.\d{2,6})"
)


def parse_pdf(pdf_path: Path) -> list[tuple[str, float]]:
    """Best-effort extraction of (date, inav) tuples from a factsheet PDF.

    Issuer factsheets vary widely in layout; this regex catches the common
    "date<whitespace>price" pattern.  Users with non-standard PDFs should
    replace this function with an issuer-specific parser.
    """
    try:
        import pypdf
    except ImportError:
        print("  WARN: pypdf not installed (pip install pypdf>=4.0).  "
              "Skipping PDF parsing.")
        return []
    out: list[tuple[str, float]] = []
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        for page in reader.pages:
            text = page.extract_text() or ""
            for m in _PAT.finditer(text):
                d_raw = m.group("date").replace("/", "-")
                # Normalize to YYYY-MM-DD when possible
                try:
                    d = pd.to_datetime(d_raw).strftime("%Y-%m-%d")
                except Exception:
                    continue
                try:
                    val = float(m.group("inav"))
                except ValueError:
                    continue
                out.append((d, val))
    except Exception as exc:  # noqa: BLE001
        print(f"  WARN: failed to parse {pdf_path.name}: {exc}")
    return out


def main() -> int:
    if not META.exists():
        sys.exit(f"ERROR: missing {META}")
    meta = pd.read_csv(META)
    tickers = meta["ticker"].tolist()

    # Write the issuer URL index regardless.
    idx = pd.DataFrame(
        [{"ticker": t, "issuer_url": ISSUER_URLS.get(t, "")} for t in tickers]
    )
    idx.to_csv(RAW / "_inav_sources.csv", index=False)
    print(f"[02] wrote {RAW.relative_to(REPO)}/_inav_sources.csv "
          f"({len(idx)} URLs)")

    n_with_pdf = 0
    for t in tickers:
        out_path = RAW / f"{t}_inav.csv"
        rows: list[tuple[str, float]] = []
        if SHEETS.exists():
            for pdf in sorted(SHEETS.glob(f"{t}_*.pdf")) + sorted(SHEETS.glob(f"{t}.pdf")):
                rows.extend(parse_pdf(pdf))
        if rows:
            df = (pd.DataFrame(rows, columns=["date", "inav"])
                    .drop_duplicates(subset=["date"], keep="last")
                    .sort_values("date"))
            df.to_csv(out_path, index=False)
            n_with_pdf += 1
            print(f"  [{t}] parsed {len(df):4d} iNAV rows -> "
                  f"{out_path.relative_to(REPO)}")
        else:
            # write empty header so 03 knows to use NAV proxy
            pd.DataFrame(columns=["date", "inav"]).to_csv(out_path, index=False)

    print(f"\n[02] DONE -- {n_with_pdf}/{len(tickers)} tickers had factsheet PDFs.")
    if n_with_pdf == 0:
        print("     For full-precision iNAV, download factsheet PDFs and place at:")
        print(f"     {SHEETS.relative_to(REPO)}/<TICKER>_<YYYY>.pdf")
        print(f"     URLs in {RAW.relative_to(REPO)}/_inav_sources.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
