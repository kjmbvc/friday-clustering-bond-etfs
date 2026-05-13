# Third-party licenses

This project bundles the following third-party code.  Each is governed by its
original upstream license, which is preserved verbatim alongside the vendored
source.

## 1. Day-dependent MSGARCH model (Lee 2025)

- **Vendored at**: `code/_vendored_msgarch_lee2025/`
- **Upstream**: https://github.com/Im-Hyeon-Lee/Day-dependent-Markov-switching-GARCH-model
- **Author / copyright holder**: Im Hyeon Lee
- **License**: MIT (full text at `code/_vendored_msgarch_lee2025/LICENSE`)
- **Pinned commit**: `c84bc297d11e430cd459a20919fee1a425e1dd41` (2025-06-23)
- **Files**: `__init__.py`, `utils.py`, `params.py`, `em_core.py`, `simulator.py`
- **Vendoring policy**: VERBATIM.  Any divergence from the pinned commit is
  flagged by `audit/check_provenance.py` and reported in
  `audit/PROVENANCE_REPORT.md`.

Usage by this repository: `code/06_msgarch_via_rpy2.py` imports
`em_fit_ms_garch`, `forward_backward_EM`, etc. from the vendored package as
one of three FridayShift backends.  The wrapper, ETF iteration, and proxy
fallbacks are original to this repository.

Citation (BibTeX `Lee2025` already in `paper/frl_references.bib`):

> Lee, Im-Hyeon (2025). *Day-dependent Markov-switching GARCH model.*
> https://github.com/Im-Hyeon-Lee/Day-dependent-Markov-switching-GARCH-model

---

## 2. (none other)

This is the only third-party code currently vendored.  Pip / conda
dependencies (numpy, pandas, scipy, statsmodels, scikit-learn, matplotlib,
yfinance, pypdf, rpy2) are installed via their package managers and not
bundled in this repository; their licenses apply via the corresponding
PyPI / conda-forge channels and are not reproduced here.
