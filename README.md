# Friday clustering of bond ETF mispricing — replication code

Replication code for:

> Kim, Jimin (2026). Wrapper-specific Friday clustering in large
> benchmark bond ETFs: a within-asset-class stylized fact.
> *Finance Research Letters* (manuscript under review).

## Quick start
```
conda env create -f environment.yml
conda activate friday-etf
for s in code/0*.py; do python $s; done
python verification/appendix_F_verification.py   # should print "ALL CHECKS PASS"
```
Total runtime: ~ 45 min on a laptop (8 GB RAM).

## Random seeds
- Permutation:   20260101
- MSGARCH start: 20260102
- Ridge LOO-CV:  20260103

## Data sources (open-access only)
NAV / closing prices from issuer fund pages and Yahoo Finance via
the `yfinance` package; iNAV from issuer factsheet PDFs (daily,
2018-2026). No paid subscription required.

## License
MIT (see LICENSE).

## Contact
Jimin Kim, University of Seoul.  Email: kjmbvc77@uos.ac.kr
