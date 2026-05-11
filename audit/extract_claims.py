#!/usr/bin/env python3
"""
audit/extract_claims.py
=======================
Scan `paper/frl_paper.tex` for every numerical token and write
`audit/_extracted_numbers.json`.

Two output forms:

    "by_line":    [ {line, col, token, context_30char}, ... ]
    "by_pattern": {regex_id: [matches]}

The downstream `compare.py` cross-references these against the manifest.

A YELLOW result in REPORT.md means a number was extracted here but no entry in
`claims_manifest.json` registers it — that's a research-integrity smell.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO  = Path(__file__).resolve().parent.parent
TEX   = REPO / "paper" / "frl_paper.tex"
OUT   = REPO / "audit" / "_extracted_numbers.json"

# Regex for any decimal number, signed or unsigned, with optional thousands sep
#   Examples: 58.3   +0.62   -0.05   1,213   <0.001   p<0.05  21\%   $43.7$
NUM_RX = re.compile(
    r"(?P<lead>[<>=]\s*|[+\-]?)"                          # leading op / sign
    r"(?P<val>\d{1,3}(?:[, ]\d{3})+|\d+(?:\.\d+)?)"  # number (with optional thousands)
    r"(?P<suf>\\?\s*\%|\bpp\b|\\pp\b)?"                   # optional %, pp suffix
)

# Skip patterns: things that LOOK like numbers but are structural (page nos, labels, dates)
SKIP_CONTEXT = (
    r"\\label\{",
    r"\\ref\{",
    r"\\cite",
    r"\\pageref",
    r"\\bibitem",
    r"\\section",
    r"\\subsection",
    r"\\documentclass",
    r"\\usepackage",
    r"\\setlength",
    r"\\titleformat",
    r"\\addbibresource",
    r"font(size|series)",
    r"@",     # email addresses
    r"http",  # URLs
    r"ORCID", # ORCID literal
)


def looks_structural(line: str) -> bool:
    return any(re.search(p, line) for p in SKIP_CONTEXT)


def extract(tex_path: Path) -> dict:
    if not tex_path.exists():
        sys.exit(f"ERROR: {tex_path} not found")
    lines = tex_path.read_text(encoding="utf-8").splitlines()
    by_line = []
    for i, raw in enumerate(lines, start=1):
        if looks_structural(raw):
            continue
        # Skip commented-out lines
        clean = raw.split("%", 1)[0] if not raw.lstrip().startswith("%") else ""
        for m in NUM_RX.finditer(clean):
            val_str = m.group("val")
            # Remove thousands separators
            try:
                val = float(val_str.replace(",", "").replace(" ", ""))
            except ValueError:
                continue
            suf = (m.group("suf") or "").strip()
            is_pct = bool(suf and "%" in suf)
            is_pp  = bool(suf and "pp" in suf)
            context = raw[max(0, m.start() - 20): m.end() + 20].strip()
            by_line.append({
                "line": i,
                "col": m.start() + 1,
                "value": val,
                "raw": m.group(0),
                "is_pct": is_pct,
                "is_pp": is_pp,
                "lead_op": m.group("lead").strip(),
                "context": context,
            })
    return {"tex": str(tex_path.relative_to(REPO)), "by_line": by_line}


def main() -> int:
    out = extract(TEX)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    n = len(out["by_line"])
    print(f"[extract] {n} numerical tokens found in {out['tex']}")
    print(f"[extract] wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
