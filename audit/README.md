# Research-integrity audit harness

## Principle

> **Every numerical claim in `paper/frl_paper.tex` must be reproducible from `code/` + `data/`,
> or it must be explicitly registered as `illustrative` in `claims_manifest.json`.**

A "hardcoded number that walked into a paper as if it were empirical" is the single failure mode this
harness is designed to prevent.  When the harness reports RED, *do not ignore it* — either the paper
is wrong, the code is wrong, the data is wrong, or the manifest is wrong.  No fifth option.

## How it works

```
         +-----------------+        +--------------------+
         | paper/frl_*.tex |        | output/*.csv       |
         | (claims)        |        | (code+data result) |
         +--------+--------+        +---------+----------+
                  |                           |
                  v                           v
       audit/extract_claims.py     audit/lookup_outputs.py
                  |                           |
                  +-----------+---------------+
                              v
                    audit/compare.py
                              |
                              v
                    audit/report.py  ->  audit/REPORT.md
                       (RED / YELLOW / GREEN per claim)
```

The single source of truth is **`claims_manifest.json`**.  Each entry pins:

- `id` — stable identifier for the claim
- `section` / `tex_pattern` — where in the paper it appears
- `paper_value` — the numerical value as published
- `code_source` — file + column that should reproduce it (or `"illustrative"`)
- `tolerance_abs` / `tolerance_rel` — what counts as a match
- `severity` — `HARD` (Table 1 cell, abstract %), `SOFT` (rounded prose), `ILLUSTRATIVE`

## Run it

```bash
bash audit/run.sh
```

This:

1. Runs the full pipeline (`code/01_*.py` ... `code/09_*.py`) if outputs are stale.
2. Extracts every numerical token from `paper/frl_paper.tex` and writes
   `audit/_extracted_numbers.json`.
3. For every entry in `claims_manifest.json`, looks up the corresponding code output and
   computes the delta.
4. Writes `audit/REPORT.md` with one row per claim:

| Status | id | section | paper value | code value | delta | tolerance | verdict |

Exit code is non-zero if any RED is reported, so CI can gate merges on a clean audit.

## Severity legend

| Severity | Meaning |
|---|---|
| **HARD** | Specific number in a results table or abstract.  Must reproduce to within `tolerance_abs`. |
| **SOFT** | Rounded number in prose ("about 21%").  Larger tolerance OK. |
| **ILLUSTRATIVE** | Explicitly synthesized example for didactic purposes.  Must be flagged in caption with `(illustrative)`. |
| **DEFERRED** | Sub-section currently described as future work; no claim made.  Audit skips. |

## What to do when you see RED

1. **Read the row.**  Does the paper claim differ from code output by more than the tolerance?
2. **Decide which is wrong**:
   - If the code is wrong / has a bug, fix code and re-run.
   - If the paper has the wrong number, edit `paper/frl_paper.tex` to match the code output.
   - If the claim has no code source at all, the paper has a hardcoded value.  Either implement
     the missing analysis or remove the specific number from the paper.
3. **Re-run** `bash audit/run.sh` until 0 RED.

## What to do when you see YELLOW

A YELLOW means the harness found a number in the paper that has no corresponding manifest entry.
Either:

- Add the claim to `claims_manifest.json` with the appropriate `code_source`.
- Or mark it as `severity: ILLUSTRATIVE` if it really is decorative (date, font size, etc.).

YELLOW must be resolved before a clean audit.  Uncatalogued numbers are how research-integrity
failures sneak in.

## Tolerances

See `tolerances.json`.  Defaults:

- Percentages: `tolerance_abs = 1.5` (absolute, in percent units)
- Correlations (rho): `tolerance_abs = 0.05`
- p-values: matched by sign of significance (i.e., `<0.001`, `<0.05`, `n.s.`) rather than exact
- Integer counts ("16 of 19"): exact match

## Files in this directory

| File | What it does |
|---|---|
| `README.md` | this document |
| `claims_manifest.json` | master list of paper claims and their code sources |
| `tolerances.json` | per-claim-type tolerance rules |
| `extract_claims.py` | scans `paper/frl_paper.tex` for all numeric tokens |
| `lookup_outputs.py` | loads pipeline outputs and resolves manifest `code_source` |
| `compare.py` | builds the diff between paper and code |
| `report.py` | writes `audit/REPORT.md` |
| `run.sh` | one-shot driver: pipeline + audit + report |
| `REPORT.md` | latest audit report (regenerated each run) |
| `_extracted_numbers.json` | gitignored; intermediate output of `extract_claims.py` |
| `_diff.json` | gitignored; intermediate output of `compare.py` |
