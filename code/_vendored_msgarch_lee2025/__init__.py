"""
Day-dependent MSGARCH research package (vendored copy of Lee 2025).

ADAPTED FROM UPSTREAM
---------------------
Upstream `__init__.py` imports `em_fit_ms_garch` and `fit_ms_garch_multi`
from `.em_core`.  However the upstream `em_core.py` at commit
c84bc297d11e430cd459a20919fee1a425e1dd41 contains a single-character
IndentationError at line 202 (an extra leading space on
`for it in range(max_iter):`), which prevents Python from parsing the
module at all.

To work around the upstream bug while keeping a byte-for-byte verbatim
record of what upstream actually publishes, we:

  1. Preserve `em_core.py` VERBATIM (with the bug) for reference.
  2. Provide `em_core_patched.py` with the 1-line whitespace fix, clearly
     attributed (see its docstring and audit/code_provenance_manifest.json).
  3. Re-route imports here so the *fixed* implementation is what users get.

The audit harness (`audit/check_provenance.py`) verifies this divergence is
the declared one and not any other adaptation.
"""
from .utils         import EPS, S, HUBER_C, TEMP0, RIDGE_TAU, scad_clip
from .params        import MSGARCHParams, initialize_parameters
# ADAPTED: was `from .em_core import (...)` upstream; routed to patched file.
from .em_core_patched import (forward_backward_EM, M_step,
                              em_fit_ms_garch, fit_ms_garch_multi,
                              log_sum_exp, param_distance)
from .simulator     import simulate_ms_garch
