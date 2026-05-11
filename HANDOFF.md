# HANDOFF.md — Spec for the next agent / session

> **TL;DR for the next agent.** This repo contains a research codebase + LaTeX
> manuscript pair that has been through one cycle of audit-driven revision.
> The single most important artifact is `audit/REPORT.md`.  If it shows
> **0 RED and 0 YELLOW**, the paper and the code are in sync.  Whatever task
> you were brought in to do: **keep it that way.**
>
> Your first action should always be:
>
> ```bash
> bash audit/run.sh
> ```
>
> Read `audit/REPORT.md`.  Then proceed.

---

## 0. Why this document exists

A prior iteration of this project shipped a paper whose Table 1 numbers were
**hardcoded illustrative values**, not computed from the data the paper claimed
to use.  This was caught only after the GitHub repo was created and the audit
harness was retro-built.  This document codifies the workflow that should
have been in place from day 1.

If you take ONE thing from this document:

> **Every numerical claim in the paper must be reproducible from `code/` +
> `data/`, or it must be explicitly registered as `illustrative` /
> `deferred` in `audit/claims_manifest.json`.  Nothing else.  No exceptions.**

The audit harness in `audit/` enforces this principle.

---

## 1. Project context

| Item | Value |
|---|---|
| Paper | Kim, Jimin (2026). *Wrapper-specific Friday clustering in large benchmark bond ETFs*. |
| Target journal | Finance Research Letters |
| Sample | 17 bond ETFs across 4 issuers and 3 jurisdictions, 2002–2026 |
| Equity benchmark | SPY (reference row only, not in the bond family) |
| Data source | yfinance (open-access daily close) + 5-day MA NAV proxy |
| GitHub repo | `https://github.com/kjmbvc/friday-clustering-bond-etfs` |
| Manuscript file | `paper/frl_paper.tex` |
| Replication pipeline | `code/01_*.py` ... `code/10_*.py` |
| Audit harness | `audit/` |

The central methodological caveat is that **NAV is approximated by a 5-day
moving average of close prices**.  Issuer-published NAV is not exposed by any
free API; pulling it requires manual download from each fund's product page
(19 separate sites).  All published numbers — Table 1, abstract, §5 — are
under this proxy.

Two UCITS tickers (AGGH, IS04) are listed in `data/fund_metadata.csv` but
return no historical price data from yfinance as of 2026-04-30.  They are
excluded from Table 1.  Effective sample is **17 bond + 1 equity benchmark**.

---

## 2. What's in the repository

```
friday-clustering-bond-etfs/
├── paper/                                  Manuscript + bibliography + Makefile
│   ├── frl_paper.tex                       LaTeX source (audit target)
│   ├── frl_references.bib                  BibTeX (32 entries)
│   └── Makefile                            pdflatex + bibtex build
├── code/                                   Replication pipeline (numbered run order)
│   ├── 01_fetch_nav_prices.py              yfinance bulk download
│   ├── 02_fetch_inav_factsheets.py         issuer factsheet PDF parser (manual)
│   ├── 03_compute_premium.py               Prem = (close - nav) / nav * 100
│   ├── 04_hcug_test.py                     HCUG G-stat + 10k permutation + BH-FDR
│   ├── 05_wsas_asymmetry.py                psi_i + sign test + Wilcoxon
│   ├── 06_msgarch_via_rpy2.py              FridayShift (rpy2 / Python EM / proxy)
│   ├── 07_cross_sectional_ols.py           OLS + HC3 + ridge LOO-CV
│   ├── 08_shares_outstanding_flow.py       creation/redemption from yfinance
│   ├── 09_make_figures.py                  figA1, figB2, figC1, figC2
│   └── 10_audit_inputs.py                  aggregate stats + Spearman + sub-period
├── verification/
│   └── appendix_F_verification.py          numpy-only closed-form checks
├── audit/                                  Research-integrity harness (NEW)
│   ├── README.md                           harness principle + how-to
│   ├── claims_manifest.json                MASTER REGISTRY of paper claims
│   ├── build_manifest.py                   regenerates the manifest
│   ├── tolerances.json                     per-metric tolerance rules
│   ├── extract_claims.py                   scan .tex for numerical tokens
│   ├── lookup_outputs.py                   resolve manifest -> code value
│   ├── compare.py                          diff paper vs code
│   ├── report.py                           markdown report (REPORT.md)
│   ├── regenerate_table1.py                rebuild Table 1 LaTeX from CSV
│   ├── run.sh                              one-shot: pipeline + audit + report
│   ├── REPORT.md                           latest report (regenerated on every run)
│   ├── _extracted_numbers.json             gitignored intermediate
│   └── _diff.json                          gitignored intermediate
├── data/
│   ├── fund_metadata.csv                   20 rows: 19 bond + SPY, with characteristics
│   ├── raw/                                pipeline outputs (gitignored)
│   └── processed/                          pipeline outputs (gitignored)
├── output/                                 pipeline outputs (gitignored, except .gitkeep)
│   ├── hcug_results.csv                    Table 1 source
│   ├── wsas_results.csv                    §5.2 source
│   ├── fridayshift.csv                     §5.3/§5.4 input
│   ├── cross_sectional.csv                 §5.3 OLS table
│   ├── cross_sectional_diag.json           §5.3 Wald F etc.
│   ├── spearman_predictors.json            §5.3 Spearman rho
│   ├── aggregate_stats.json                §5.1, §5.2, §5.5 aggregate stats
│   ├── subperiod_friday_share.csv          §5.7 sub-period
│   ├── flow_proxy.csv                      §5.4 (limited; only 6 of 17 ETFs)
│   └── figures/                            figA1, figB2, figC1, figC2 PNGs
├── docs/                                   replication notes + ETF list
├── README.md                               user-facing replication readme
├── requirements.txt                        pip dependencies
├── environment.yml                         conda environment (incl. R + MSGARCH)
├── LICENSE                                 MIT
├── .gitignore                              ignores pipeline outputs
└── HANDOFF.md                              THIS FILE
```

---

## 3. The research-integrity principle (one rule)

> **Every numerical claim in `paper/frl_paper.tex` must be reproducible from
> `code/` + `data/`, or it must be explicitly registered as `illustrative` /
> `deferred` in `audit/claims_manifest.json`.**

This rule is enforced by the audit harness.  Three failure modes the harness
catches:

1. **Hardcoded value in paper that has no code source.** YELLOW in the
   report.  Example: a Friday-share percentage typed directly into a `\begin{tabular}` cell.
2. **Code source exists but paper value disagrees.** RED.  Example: code
   says `IEF Friday share = 24.6%` but Table 1 reads `58.3%`.
3. **Code source declared in manifest but file missing.** YELLOW with
   `LOOKUP_ERROR`.  Example: manifest points to `output/spearman_predictors.json`
   but the script that produces it hasn't run.

The harness does NOT:

- Detect numbers in figures (image-rendered values are not parsed).  If you
  embed a number in a `.png` caption, the caption text is still scanned, but
  any number baked into the image itself is invisible to the harness.  When
  you regenerate figures, regenerate them from the same CSV the manifest
  points to.
- Check methodology correctness.  If the code computes the wrong statistic
  but the paper agrees with the code, the harness shows GREEN.  Run
  `verification/appendix_F_verification.py` for the closed-form sanity checks.
- Detect tautological computations.  If a manifest entry's `expr` is `0` and
  the paper claims `0`, that's GREEN but useless.

---

## 4. Standard workflow

### 4.1. To check the current state

```bash
bash audit/run.sh
```

This:
1. Runs `code/01_*.py` ... `code/10_*.py` (skip with `SKIP_PIPELINE=1`).
2. Runs `verification/appendix_F_verification.py`.
3. Runs `audit/extract_claims.py`, `audit/compare.py`, `audit/report.py`.
4. Writes `audit/REPORT.md`.

Open the report.  If it shows `0 RED + 0 YELLOW`, the paper and code are in
sync.  GRAY rows are expected for deferred analyses.

### 4.2. Code change → re-audit cycle

If you change anything in `code/` or `data/`:

```bash
bash audit/run.sh
```

If RED appears: the new code output disagrees with the paper.  Decide:
- **The new code value is what should be in the paper.**  Edit
  `paper/frl_paper.tex` to use the new number.  If it's in Table 1, run
  `python audit/regenerate_table1.py` and replace lines 384–402.
- **The new code value is wrong (regression / bug).**  Fix code, re-run.
- **The manifest is stale (the manifest still records the old paper value).**
  Edit `audit/build_manifest.py`, then `python audit/build_manifest.py` to
  regenerate `claims_manifest.json`.  Then re-audit.

### 4.3. Paper change → re-audit cycle

If you edit `paper/frl_paper.tex` to add a new number or change an existing
one:

1. Update `audit/build_manifest.py` so the corresponding entry's `paper_value`
   matches the new number.
2. `python audit/build_manifest.py`
3. `bash audit/run.sh`
4. If RED: the paper value doesn't match the code output.  Either the paper
   is overclaiming (fix the paper) or the code needs to compute the new
   thing (write the script and add the manifest entry's `code_source`).

### 4.4. New claim → add manifest entry

Adding a number to the paper that's not in the manifest is a research-
integrity violation.  Whenever you write a new number, immediately add it
to `audit/build_manifest.py`:

```python
{
    "id": "s5N_new_claim",
    "tex_section": "5.N New Section",
    "claim_text": "human-readable description",
    "paper_value": 1.23,
    "kind": "csv" | "csv_aggregate" | "json" | "computed",
    "csv_path": "output/...",       # if kind = csv / csv_aggregate
    "json_path": "output/...",      # if kind = json
    "key_path": [...],              # if kind = json
    "lookup_key": "ticker",         # if kind = csv with row lookup
    "lookup_val": "IEF",
    "value_column": "fri_pct",
    "tolerance_type": "percentage_pp",
    "severity": "HARD",
}
```

Then `python audit/build_manifest.py && bash audit/run.sh`.

---

## 5. Audit cycles run so far

| Cycle | Date | Trigger | RED | YELLOW | GREEN | GRAY | Total |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | 2026-05-11 | initial run after harness build | 53 | 6 | 13 | 13 | 85 |
| 2 | 2026-05-11 | after honest revision of `paper/frl_paper.tex` and manifest re-sync | **0** | **0** | **80** | 2 | 82 |

The 6 YELLOW in cycle 1 were AGGH and IS04 (delisted on yfinance); they were
removed from Table 1 in the revision.  Sample size in the paper is now stated
as 17 bond ETFs, not 19.

The 53 RED in cycle 1 broke down as:

- 45 from Table 1 (every ticker × {fri_pct, G_stat}).  Cause: paper had
  hardcoded illustrative values.
- 2 from abstract Spearman rho values.  Cause: hardcoded.
- 3 from §5.2 WSAS prose (psi range, sig count).  Cause: hardcoded.
- 4 from §5.3 Spearman + Wald F.  Cause: hardcoded.

Revision strategy: edit `paper/frl_paper.tex` to use the code-computed
values; explicitly *retract* the size-and-Treasury-predict-FridayShift
claim, since the proxy NAV cannot support it (Treasury Spearman ρ is in fact
negative under proxy, not positive as in the synthetic prior).

---

## 6. Known limitations (the things to fix in the next iteration)

| # | Limitation | Fix path |
|---|---|---|
| 1 | 5-day MA NAV proxy washes out the close-vs-NAV gap | Manual issuer-NAV CSV download per ticker; place at `data/raw/<TICKER>_nav_issuer.csv`.  Pipeline already supports this via `code/01_fetch_nav_prices.py`. |
| 2 | iNAV inaccuracy regressor unavailable | Manual issuer factsheet PDFs to `data/raw/factsheets/`.  `code/02_fetch_inav_factsheets.py` parses them via `pypdf`. |
| 3 | MSGARCH FridayShift estimated by forward filter only | Vendor full forward-backward + M-step from [Im-Hyeon-Lee/Day-dependent-MSGARCH](https://github.com/Im-Hyeon-Lee/Day-dependent-Markov-switching-GARCH-model) — Python EM core is ~250 LOC. |
| 4 | Confound-exclusion robustness (option-expiration, quad-witching, month-end Friday filters) not implemented | Add date-filter to `code/04_hcug_test.py`; one new manifest entry per excluded subset. |
| 5 | T+1 settlement transition pre/post stratification (28 May 2024) | Currently in §5.6 as DEFERRED.  Add code, then promote manifest entries `s56_t1_pre` and `s56_t1_post` from `DEFERRED` to `HARD`. |
| 6 | Shares-outstanding flow only available for 6 of 17 ETFs from yfinance | Use issuer flow CSVs or N-CEN filings (manual). |
| 7 | AGGH and IS04 unavailable on yfinance | If issuer NAV is downloaded manually for these, the pipeline will pick them up automatically and the sample grows to 19. |

When you fix any of these, the audit's GRAY rows can be promoted to HARD
(or remain DEFERRED if you only documented the gap without implementing).

---

## 7. Cheatsheet — exact commands

| Goal | Command |
|---|---|
| Install deps | `py -3.12 -m pip install -r requirements.txt` |
| Pipeline + audit one-shot | `bash audit/run.sh` |
| Audit only (skip pipeline) | `SKIP_PIPELINE=1 bash audit/run.sh` |
| Just pipeline (no audit) | `for f in code/0*.py; do py -3.12 "$f"; done; py -3.12 code/10_audit_inputs.py` |
| Just verification | `py -3.12 verification/appendix_F_verification.py` |
| Regenerate Table 1 LaTeX | `py -3.12 audit/regenerate_table1.py` |
| Rebuild manifest after editing build_manifest.py | `py -3.12 audit/build_manifest.py` |
| Look up one claim | `py -3.12 audit/lookup_outputs.py tab1_IEF_fri_pct` |

On macOS/Linux substitute `py -3.12` with `python3.12` or `python3`.

---

## 8. Sanity checks before any submission

Run all of these.  All must pass.

```bash
# 1. Verification: closed-form math sanity (numpy only)
py -3.12 verification/appendix_F_verification.py | tail -1
# expected: "ALL CHECKS PASS"

# 2. Pipeline produces all expected outputs
ls output/
# expected: aggregate_stats.json  cross_sectional.csv  cross_sectional_diag.json
#           figures/  flow_proxy.csv  fridayshift.csv  hcug_results.csv
#           spearman_predictors.json  subperiod_friday_share.csv  wsas_results.csv

# 3. Audit clean
bash audit/run.sh 2>&1 | tail -5
# expected: "{'GREEN': N, 'RED': 0, 'YELLOW': 0, 'GRAY': K, 'total': N+K}"

# 4. Latest report shows clean
head -15 audit/REPORT.md
# expected: "🔴 **RED**:      0  ...  ✅ **Clean audit**"
```

If any of these fail, you are not ready to submit.

---

## 9. Submission checklist (when the audit is clean)

- [ ] `bash audit/run.sh` returns 0 RED + 0 YELLOW.
- [ ] `paper/frl_paper.tex` author block has correct name, email, ORCID.
  - Author: Jimin Kim.  Email: kjmbvc77@uos.ac.kr.  ORCID: replace
    `0000-0000-0000-0000` placeholder before submitting (see line 105).
- [ ] `paper/frl_paper.tex` data-availability section URLs are correct
  (either GitHub for single-blind or anonymous.4open.science mirror for
  double-blind).
- [ ] PDF compiles cleanly via `make` in `paper/`.
- [ ] PDF page count ≤ 18, body word count ≤ 2,500 (check via `pdfinfo` +
  `pdftotext -layout paper/frl_paper.pdf - | wc -w`).
- [ ] All 32 bibliography entries cited at least once
  (`bibtex frl_paper 2>&1 | grep "I didn't find"` returns nothing).
- [ ] No overfull hboxes (`grep "Overfull" paper/frl_paper.log` returns
  nothing).
- [ ] GitHub repo is PUBLIC (`gh repo view --json visibility`).
- [ ] v1.0.0 tag exists and points at the audited commit
  (`git tag -l v1.0.0` shows the tag).

---

## 10. For a fresh Claude session: minimum prompt to continue

If you're picking up this project in a new session, paste this as your
first prompt:

```
Read HANDOFF.md, then run `bash audit/run.sh` and report the
REPORT.md summary line back to me.  Do not make any code or paper
changes until I tell you what task you're doing.
```

This anchors the new session to the audit invariant before any work begins.

---

## 11. Anti-patterns (do NOT do these)

| Anti-pattern | What to do instead |
|---|---|
| Edit `audit/claims_manifest.json` directly to silence a RED row | Edit `paper/frl_paper.tex` or the underlying code so the values agree; then re-run `build_manifest.py`. |
| Type a new number into the paper without a matching manifest entry | Add the manifest entry *first*, with `kind: "csv"` or similar; then write the number. |
| Skip `bash audit/run.sh` on a "small" change | All changes are small until they're not. |
| Use `kind: "illustrative"` to hide a real result | `illustrative` is reserved for genuinely decorative numbers (font sizes, page numbers, dates).  Real results that are too weak should be honestly reported, not relabeled. |
| Hardcode a Friday share / G-stat / rho into the paper or into `09_make_figures.py` | All such numbers come from the pipeline output CSVs.  `09_make_figures.py` reads `output/hcug_results.csv`, not a hardcoded list. |
| Add a `np.random.seed(...)` call inside the audit harness or paper-prose-generation step | Random seeds belong only in `code/04`, `code/06`, `code/07`, and the verification script.  Seeded synthetic data must never reach the paper. |

---

## 12. Document version

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-05-11 | initial draft after audit cycle 2 cleaned | Establishes the harness, principles, and workflow. |

---

*If you change any structural element of this repo — the pipeline scripts,
the audit harness, the manifest schema — update this document.  Future
sessions will read it before reading the code.*
