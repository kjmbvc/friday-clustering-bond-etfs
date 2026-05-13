"""Step 8 — Friday creation/redemption flow proxy (Eq. F.21)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from constants import TICKERS_US_ISHARES, TICKERS_US_VANGUARD, TICKERS_US_SSGA, OUTPUT_DIR, DATA_RAW, FRIDAY
from utils import spearman_with_t, bh_fdr


US_FUNDS = TICKERS_US_ISHARES + TICKERS_US_VANGUARD + TICKERS_US_SSGA


def main() -> None:
    rows = []
    for tkr in US_FUNDS:
        path = DATA_RAW / f"{tkr}_shares_outstanding.csv"
        if not path.exists():
            print(f"  [{tkr}] shares-outstanding series missing; skip "
                  "(real implementation should fetch from issuer fund page).")
            continue
        s = pd.read_csv(path, parse_dates=["date"]).sort_values("date")
        s["weekday"] = pd.DatetimeIndex(s["date"]).weekday
        # Eq. F.21
        s["creation"]   = np.maximum(0,  s["shares"].diff())
        s["redemption"] = np.maximum(0, -s["shares"].diff())
        total = (s["creation"] + s["redemption"]).sum()
        fri   = (s.loc[s["weekday"] == FRIDAY, "creation"] +
                 s.loc[s["weekday"] == FRIDAY, "redemption"]).sum()
        fri_share = float(fri / total) if total > 0 else np.nan
        rows.append({"ticker": tkr, "FridayCreate_Redeem_share": fri_share})

    out = pd.DataFrame(rows)
    if not out.empty:
        fs = pd.read_csv(OUTPUT_DIR / "fridayshift.csv")
        merged = out.merge(fs, on="ticker", how="inner")
        rho_test = spearman_with_t(merged["FridayCreate_Redeem_share"].values,
                                    merged["FridayShift"].values)
        print(f"Cross-sectional Spearman: rho={rho_test['rho']:+.3f}  p={rho_test['p']:.4f}")
        out.to_csv(OUTPUT_DIR / "flow_proxy.csv", index=False)
    print("Step 8 complete.")


if __name__ == "__main__":
    main()
