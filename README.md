# Friday clustering of bond ETF mispricing -- replication code

Replication code for:

> Kim, Jimin (2026). *Wrapper-specific Friday clustering in large benchmark
> bond ETFs: a within-asset-class stylized fact.*
> Finance Research Letters (manuscript under review).

## What this repository ships

A nine-step pipeline that, starting from the published `yfinance` API and
issuer factsheets, reproduces every numerical result in the manuscript:

| Step | Script | What it does | Output |
|------|--------|--------------|--------|
| 01 | `01_fetch_nav_prices.py` | Daily close (`yfinance`) + 5-day MA NAV proxy | `data/raw/<TICKER>_close.csv`, `_nav.csv` |
| 02 | `02_fetch_inav_factsheets.py` | iNAV from issuer factsheet PDFs (manual download) | `data/raw/<TICKER>_inav.csv` |
| 03 | `03_compute_premium.py` | `Prem(i,t) = (Close - NAV) / NAV * 100` | `data/processed/premiums.csv` |
| 04 | `04_hcug_test.py` | Holiday-Conditioned Uniform G-test, 10k permutations, BH-FDR | `output/hcug_results.csv` (Table 1) |
| 05 | `05_wsas_asymmetry.py` | Wrapper-Specificity Asymmetry Statistic psiᵢ + Wilcoxon | `output/wsas_results.csv` |
| 06 | `06_msgarch_via_rpy2.py` | Day-dependent MSGARCH FridayShift (rpy2 -> Python EM -> proxy) | `output/fridayshift.csv` |
| 07 | `07_cross_sectional_ols.py` | OLS + HC3, ridge LOO-CV, Wald F | `output/cross_sectional.csv` |
| 08 | `08_shares_outstanding_flow.py` | Daily creation/redemption from delta-S | `output/flow_proxy.csv` |
| 09 | `09_make_figures.py` | figA1, figB2, figC1, figC2 | `output/figures/*.png` |
| ✓  | `verification/appendix_F_verification.py` | Closed-form numpy-only verification of every method | prints `ALL CHECKS PASS` |

## Quick start

### Option A -- pip / venv (recommended)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python code/01_fetch_nav_prices.py        # ~3-5 min (network)
python code/02_fetch_inav_factsheets.py   # documents iNAV sources
python code/03_compute_premium.py
python code/04_hcug_test.py               # ~2 min
python code/05_wsas_asymmetry.py
python code/06_msgarch_via_rpy2.py        # ~5-30 min (depending on backend)
python code/07_cross_sectional_ols.py
python code/08_shares_outstanding_flow.py # ~2 min (network)
python code/09_make_figures.py

python verification/appendix_F_verification.py     # MUST end with "ALL CHECKS PASS"
```

### Option B -- conda (Linux/macOS, includes R for MSGARCH)

```bash
conda env create -f environment.yml
conda activate friday-etf
for s in code/0*.py; do python "$s"; done
python verification/appendix_F_verification.py
```

End-to-end runtime: **~ 15-45 min** on a laptop, dominated by 06's MSGARCH
fits.  Set `--method proxy` for a fast (<5 min) Python-only run that
sacrifices a few decimal places of FridayShift precision.

## What you need to download manually

Yahoo Finance covers daily close for every ticker in the cross-section, but
**iNAV** is published only inside issuer factsheet PDFs.  Script 02 will
parse them automatically if you place them at `data/raw/factsheets/<TICKER>_*.pdf`;
otherwise it writes empty iNAV files and the rest of the pipeline falls back
to the 5-day-MA NAV proxy (which is robust for the *Friday-share* claim but
not for the iNAV-inaccuracy regressor in script 07).

The 20 canonical issuer factsheet URLs are written to
`data/raw/_inav_sources.csv` after running 02.

## MSGARCH backend (script 06)

Script 06 will pick whichever backend is installed, in this order:

1.  **`rpy2` + R-MSGARCH 2.5** -- the rigorous Bauwens *et al.* package.
    Requires R 4.x and `install.packages('MSGARCH')` plus `pip install rpy2`.
2.  **Python EM** -- pure-Python forward filter, vendored and lightly
    adapted from
    [Im-Hyeon-Lee/Day-dependent-Markov-switching-GARCH-model](https://github.com/Im-Hyeon-Lee/Day-dependent-Markov-switching-GARCH-model)
    (the reference implementation accompanying Lee, 2025).  Requires
    `scikit-learn` for the K-means initializer.
3.  **30-day rolling-vol tertile proxy** -- numpy-only fallback, matches the
    sign and ordering of FridayShift but not the magnitude.

Force a specific backend with `--method {rpy2,python,proxy}`.

## Random seeds

Hard-coded in each script:

```
permutation:  20260101   (script 04, 05)
MSGARCH:      20260102   (script 06)
ridge LOO:    20260103   (script 07)
```

## Sample composition

19 bond ETFs across iShares-US (7), Vanguard-US (3), State Street-US (2),
Canadian (3), and UCITS-Europe (4), plus SPY as the equity benchmark.  Full
metadata in `data/fund_metadata.csv` and `docs/ETF_LIST.md`.

## License

MIT -- see `LICENSE`.

## Citation

If you use this code, please cite the manuscript above and the MSGARCH
reference implementation:

> Lee, Im-Hyeon (2025).  *Day-dependent Markov-switching GARCH model.*
> https://github.com/Im-Hyeon-Lee/Day-dependent-Markov-switching-GARCH-model

## Contact

Jimin Kim, University of Seoul.  Email: kjmbvc77@uos.ac.kr
