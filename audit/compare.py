#!/usr/bin/env python3
"""
audit/compare.py
================
Walk every entry of `claims_manifest.json`, resolve its `code_source` via
`lookup_outputs.py`, and produce `audit/_diff.json` with one row per claim:

    { "id", "section", "tex_pattern", "paper_value", "code_value",
      "delta_abs", "delta_rel", "tolerance", "severity", "status", "source" }

`status` is one of:
  GREEN    code value matches paper value within tolerance
  RED      code value differs from paper value by more than tolerance
  YELLOW   code source missing / lookup failed / claim un-anchored
  GRAY     entry has severity ILLUSTRATIVE or DEFERRED — audit skipped
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lookup_outputs import resolve, LookupError

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "audit" / "claims_manifest.json"
TOL      = REPO / "audit" / "tolerances.json"
OUT      = REPO / "audit" / "_diff.json"


def classify(paper: float, code: float, tol_abs: float | None, tol_rel: float | None) -> str:
    if paper is None or code is None or any(map(math.isnan, [paper, code])):
        return "YELLOW"
    if tol_abs is not None and abs(paper - code) <= tol_abs:
        return "GREEN"
    if tol_rel is not None and paper != 0 and abs(paper - code) / abs(paper) <= tol_rel:
        return "GREEN"
    return "RED"


def main() -> int:
    if not MANIFEST.exists():
        sys.exit(f"missing {MANIFEST}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tol_rules = json.loads(TOL.read_text(encoding="utf-8")) if TOL.exists() else {}

    rows = []
    for section in manifest.get("claims", []):
        sec_id = section.get("section_id", "?")
        for entry in section.get("entries", []):
            severity = entry.get("severity", "HARD")
            if severity in ("ILLUSTRATIVE", "DEFERRED"):
                rows.append({
                    "id": entry["id"], "section": sec_id,
                    "paper_value": entry.get("paper_value"),
                    "code_value": None, "delta_abs": None, "delta_rel": None,
                    "tolerance": "skipped",
                    "severity": severity, "status": "GRAY",
                    "source": entry.get("_note", "skipped per manifest"),
                })
                continue
            paper_val = entry.get("paper_value")
            try:
                code_val, source_label = resolve(entry)
                lookup_err = None
            except LookupError as e:
                code_val, source_label = None, f"LOOKUP_ERROR: {e}"
                lookup_err = str(e)

            # tolerance — explicit entry overrides type-rule
            tol_type = entry.get("tolerance_type")
            tol_abs = entry.get("tolerance_abs")
            tol_rel = entry.get("tolerance_rel")
            if tol_type and (tol_abs is None and tol_rel is None):
                rule = tol_rules.get(tol_type, {})
                tol_abs = rule.get("tolerance_abs")
                tol_rel = rule.get("tolerance_rel")

            if lookup_err is not None:
                status = "YELLOW"
                delta_abs = None
                delta_rel = None
            else:
                delta_abs = abs(paper_val - code_val) if (paper_val is not None and code_val is not None) else None
                delta_rel = (delta_abs / abs(paper_val)) if (delta_abs is not None and paper_val) else None
                status = classify(paper_val, code_val, tol_abs, tol_rel)

            rows.append({
                "id": entry["id"], "section": sec_id,
                "tex_line": entry.get("tex_line"),
                "paper_value": paper_val,
                "code_value": code_val,
                "delta_abs": round(delta_abs, 4) if delta_abs is not None else None,
                "delta_rel": round(delta_rel, 4) if delta_rel is not None else None,
                "tolerance_abs": tol_abs,
                "tolerance_rel": tol_rel,
                "tolerance_type": tol_type,
                "severity": severity,
                "status": status,
                "source": source_label,
                "claim_text": entry.get("claim_text"),
            })

    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    summary = {
        "GREEN":  sum(1 for r in rows if r["status"] == "GREEN"),
        "RED":    sum(1 for r in rows if r["status"] == "RED"),
        "YELLOW": sum(1 for r in rows if r["status"] == "YELLOW"),
        "GRAY":   sum(1 for r in rows if r["status"] == "GRAY"),
        "total":  len(rows),
    }
    print(f"[compare] {summary}")
    print(f"[compare] wrote {OUT.relative_to(REPO)}")
    # Exit code reflects RED count so CI can gate on it
    return min(summary["RED"], 1)


if __name__ == "__main__":
    sys.exit(main())
