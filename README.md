# Friday clustering of bond ETF mispricing — replication code

Replication code for:

> Kim, Jimin (2026). Wrapper-specific Friday clustering in large
> benchmark bond ETFs: a within-asset-class stylized fact.
> *Finance Research Letters* (manuscript under review).

## Quick start
```bash
conda env create -f environment.yml
conda activate friday-etf
make all          # runs full pipeline (~ 45 min)
make verify       # numpy-only closed-form verification (< 5 sec)
make test         # pytest unit tests for every math construct (~ 2 min)
```

## Layout
```
constants.py      Random seeds, fund tickers, paths.
utils/            Reusable math primitives (no I/O).
code/01..09.py    Driver scripts that read data, call utils/, write output/.
verification/     NumPy-only closed-form checks.
tests/            Pytest unit tests for every math construct.
docs/             Math-to-code map, replication notes, ETF list.
data/             fund_metadata.csv only; raw downloads go to data/raw/ (gitignored).
output/           Run output: CSVs and PNGs (gitignored).
```

## Random seeds (centralized in constants.py)
- Permutation:    20260101
- MSGARCH start:  20260102
- Ridge LOO-CV:   20260103
- Block bootstrap:20260104

## Math-to-code map
See `docs/MATH_TO_CODE_MAP.md` for an explicit table linking every
displayed equation in the paper (Eq. 1 through Eq. F.31) to its
Python implementation.

## Data sources (open-access only)
- NAV / closing prices: issuer fund pages + Yahoo Finance via `yfinance`.
- iNAV: issuer factsheet PDFs (daily, 2018-2026).
- ETF metadata: end-2025 snapshot from issuer pages, cached in `data/`.

## License
MIT (see LICENSE).

## Contact
Jimin Kim, University of Seoul.  Email: kjmbvc77@uos.ac.kr
