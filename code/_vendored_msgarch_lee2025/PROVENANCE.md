# Provenance — Day-dependent MSGARCH model (Lee 2025)

This directory is a **verbatim vendored copy** of the public reference
implementation of the day-dependent Markov-switching GARCH model from
Lee (2025).

| Item | Value |
|---|---|
| Original author | Im Hyeon Lee |
| Original repository | https://github.com/Im-Hyeon-Lee/Day-dependent-Markov-switching-GARCH-model |
| Original license | MIT (see `LICENSE` in this directory) |
| Pinned commit | `c84bc297d11e430cd459a20919fee1a425e1dd41` |
| Commit date | 2025-06-23T13:26:26Z |
| Date vendored | 2026-05-13 |
| Vendored by | Jimin Kim, University of Seoul |

## Files

Verbatim copies of `src/*.py` from the upstream repository at the pinned
commit:

| File | Source (upstream path) | SHA-256 (upstream raw) |
|---|---|---|
| `__init__.py`  | `src/__init__.py`  | (verified at audit time) |
| `utils.py`     | `src/utils.py`     | (verified at audit time) |
| `params.py`    | `src/params.py`    | (verified at audit time) |
| `em_core.py`   | `src/em_core.py`   | (verified at audit time) |
| `simulator.py` | `src/simulator.py` | (verified at audit time) |
| `LICENSE`      | repo root `LICENSE` | (verified at audit time) |

The hashes are checked against the upstream raw URLs each time
`bash audit/run.sh` is invoked, via `audit/check_provenance.py`.  Any
divergence is flagged in `audit/PROVENANCE_REPORT.md`.

## What I (Kim) modified

The following two files **diverge** from upstream.  All other files in this
directory are byte-for-byte verbatim copies (verified on every audit cycle
by `audit/check_provenance.py`).

### 1. `em_core_patched.py` (NEW, adapted_for_bugfix)

Upstream `em_core.py` at the pinned commit contains a 1-character
**IndentationError** at line 202 inside `em_fit_ms_garch`:

```diff
-     for it in range(max_iter):    # 5-space indent (upstream)  -> SyntaxError
+    for it in range(max_iter):     # 4-space indent (patched)
```

The bug prevents Python from parsing the module at all, so we cannot
import upstream's `em_core` directly.  We therefore retain `em_core.py`
verbatim (with the bug) for reference, and add `em_core_patched.py` which
is identical apart from this one-character whitespace fix and a leading
docstring describing the divergence.

Audit-harness handling: manifest declares `em_core_patched.py` with
`policy: adapted_for_bugfix` and `divergence_reason` /
`patch_description` fields; `audit/check_provenance.py` requires both
fields to be present (otherwise classifies as `ADAPTED_UNDOCUMENTED`).

### 2. `__init__.py` (adapted_for_bugfix)

Upstream `__init__.py` imports `em_fit_ms_garch` and `fit_ms_garch_multi`
from `.em_core`.  Because of the upstream bug above we re-route those
imports to `.em_core_patched`.  Everything else (the `utils` /
`params` / `simulator` re-exports) is unchanged.

```diff
- from .em_core    import (forward_backward_EM, M_step,
-                          em_fit_ms_garch, fit_ms_garch_multi)
+ from .em_core_patched import (forward_backward_EM, M_step,
+                              em_fit_ms_garch, fit_ms_garch_multi,
+                              log_sum_exp, param_distance)
```

All other adaptation — the FridayShift wrapper, the optional rpy2 /
proxy fallback backends, the date range gates, and the per-ETF iteration
loop — lives in `code/06_msgarch_via_rpy2.py`, which **imports** from
this package rather than redefining the algorithm.  The audit harness'
originality check enforces that `code/06_msgarch_via_rpy2.py` does not
contain any `def`/`class` definitions of the upstream algorithm
symbols (`scad_clip`, `forward_backward_EM`, `M_step`,
`em_fit_ms_garch`, `MSGARCHParams`, `initialize_parameters`).

## How to update

When you want to re-pin to a newer upstream commit:

1. Update the **Pinned commit** line above to the new SHA.
2. Re-run `audit/check_provenance.py --refresh-verbatim` (which overwrites
   the files in this directory with the new upstream content).
3. Run `bash audit/run.sh` and confirm `PROVENANCE_REPORT.md` shows all
   `VERBATIM` and no `DIVERGENT`.
4. If the upstream LICENSE changes, you may need to revise the
   THIRD_PARTY_LICENSES.md at the repo root.
5. Commit with a message of the form
   `vendor(msgarch_lee2025): repin to <SHA>`.

## How to cite (paper bibliography)

Lee, Im-Hyeon (2025).  *Day-dependent Markov-switching GARCH model.*
GitHub: https://github.com/Im-Hyeon-Lee/Day-dependent-Markov-switching-GARCH-model

(BibTeX entry already present as `\citet{Lee2025}` in `paper/frl_references.bib`.)
