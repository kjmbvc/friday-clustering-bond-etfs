# Code-provenance audit report

_Generated: 2026-05-13T16:38:04_

## Summary

- Verbatim files:       5 VERBATIM / 0 DIVERGENT / 0 MISSING
- Adapted files:        2 DOCUMENTED / 0 UNDOCUMENTED
- License artifacts:    3 OK / 0 INCOMPLETE / 0 MISSING
- Originality (consumers):  1 OK / 0 RISK / 0 FILE_MISSING

✅ **Clean provenance** — all vendored files match upstream, all licenses retained, no inline plagiarism.

## Package: `msgarch_lee2025`

- Upstream: https://github.com/Im-Hyeon-Lee/Day-dependent-Markov-switching-GARCH-model
- Pinned commit: `c84bc297d11e430cd459a20919fee1a425e1dd41`
- License: MIT (holder: Im Hyeon Lee, year: 2025)

### File-level checks

| Status | Local | bytes | divergence reason |
|---|---|---:|---|
| ADAPTED_DOCUMENTED | `code/_vendored_msgarch_lee2025/__init__.py` | 1449 | Reroutes EM imports to em_core_patched.py because upstream em_core.py has Indent |
| VERBATIM | `code\_vendored_msgarch_lee2025\utils.py` | 438 | — |
| VERBATIM | `code\_vendored_msgarch_lee2025\params.py` | 1405 | — |
| VERBATIM | `code\_vendored_msgarch_lee2025\em_core.py` | 8072 | — |
| ADAPTED_DOCUMENTED | `code/_vendored_msgarch_lee2025/em_core_patched.py` | 9405 | Fixes 1-character indentation typo at line 202 of em_fit_ms_garch that breaks Py |
| VERBATIM | `code\_vendored_msgarch_lee2025\simulator.py` | 1585 | — |
| VERBATIM | `code\_vendored_msgarch_lee2025\LICENSE` | 1069 | — |

#### Verbatim file SHA-256 detail

| Status | Local | SHA-256 local | SHA-256 upstream |
|---|---|---|---|
| VERBATIM | `code\_vendored_msgarch_lee2025\utils.py` | `1f6d164a351d...` | `1f6d164a351d...` |
| VERBATIM | `code\_vendored_msgarch_lee2025\params.py` | `45dbbbd3ec57...` | `45dbbbd3ec57...` |
| VERBATIM | `code\_vendored_msgarch_lee2025\em_core.py` | `bc92ce9544c5...` | `bc92ce9544c5...` |
| VERBATIM | `code\_vendored_msgarch_lee2025\simulator.py` | `32c2a3cef11a...` | `32c2a3cef11a...` |
| VERBATIM | `code\_vendored_msgarch_lee2025\LICENSE` | `b44a21d41ccf...` | `b44a21d41ccf...` |

### License-artifact checks

| Status | Artifact |
|---|---|
| LICENSE_OK | `code/_vendored_msgarch_lee2025/LICENSE` |
| LICENSE_OK | `code/_vendored_msgarch_lee2025/PROVENANCE.md` |
| LICENSE_OK | `THIRD_PARTY_LICENSES.md` |

### Originality (consumer-file) checks

| Status | Consumer file | Forbidden inline definitions |
|---|---|---|
| ORIGINAL_OK | `code/06_msgarch_via_rpy2.py` | — |

