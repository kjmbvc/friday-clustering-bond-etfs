#!/usr/bin/env bash
#
# audit/run.sh
# ============
# One-shot driver: runs the pipeline if outputs are stale, then audits the
# paper against the pipeline output.
#
# Usage:
#     bash audit/run.sh                   # run everything from scratch
#     SKIP_PIPELINE=1 bash audit/run.sh   # use existing output/, just audit
#
# Exit code:
#     0  — clean audit (no RED, no YELLOW)
#     1  — RED entries (paper contradicts code)
#     2  — pipeline failed
#
set -euo pipefail

# Pick Python: py -3.12 (Windows) or python3 (POSIX)
if command -v py >/dev/null 2>&1; then
  PY="py -3.12"
else
  PY="python3"
fi

# Repo root = parent of audit/
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "============================================================"
echo "  Research-integrity audit"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"

if [[ "${SKIP_PIPELINE:-0}" != "1" ]]; then
  echo "[run] Pipeline stage"
  $PY code/01_fetch_nav_prices.py 2>&1 | tail -3
  $PY code/02_fetch_inav_factsheets.py 2>&1 | tail -3
  $PY code/03_compute_premium.py 2>&1 | tail -3
  $PY code/04_hcug_test.py 2>&1 | tail -3
  $PY code/05_wsas_asymmetry.py 2>&1 | tail -3
  $PY code/06_msgarch_via_rpy2.py --method python 2>&1 | tail -3
  $PY code/07_cross_sectional_ols.py 2>&1 | tail -3
  $PY code/08_shares_outstanding_flow.py 2>&1 | tail -3
  $PY code/09_make_figures.py 2>&1 | tail -3
  $PY code/10_audit_inputs.py 2>&1 | tail -10
fi

echo
echo "[run] Verification stage"
$PY verification/appendix_F_verification.py 2>&1 | tail -3

echo
echo "[run] Audit stage"
$PY audit/extract_claims.py
$PY audit/compare.py
$PY audit/report.py

echo
echo "[run] Report at audit/REPORT.md"
echo "      $REPO/audit/REPORT.md"
