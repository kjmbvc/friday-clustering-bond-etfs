#!/usr/bin/env python3
"""
audit/report.py
===============
Read `audit/_diff.json` and write a human-readable `audit/REPORT.md`.

Top of report has a traffic-light banner; below, three sections (RED, YELLOW,
GREEN) each as a table.  Exit code = number of RED entries, capped at 1.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DIFF = REPO / "audit" / "_diff.json"
OUT  = REPO / "audit" / "REPORT.md"


def fmt_val(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4f}" if abs(v) < 100 else f"{v:.2f}"
    return str(v)


def fmt_row(r: dict) -> str:
    return ("| {status} | `{id}` | {section} | {paper} | {code} | {delta} | "
            "{tol} | {severity} | {source} |").format(
        status=r["status"],
        id=r["id"],
        section=r["section"],
        paper=fmt_val(r["paper_value"]),
        code=fmt_val(r["code_value"]),
        delta=fmt_val(r["delta_abs"]),
        tol=f"abs {r['tolerance_abs']}" if r.get("tolerance_abs") is not None
            else (f"rel {r['tolerance_rel']}" if r.get("tolerance_rel") is not None else "—"),
        severity=r["severity"],
        source=str(r["source"])[:60],
    )


def main() -> int:
    if not DIFF.exists():
        sys.exit(f"missing {DIFF} — run audit/compare.py first")
    rows = json.loads(DIFF.read_text(encoding="utf-8"))

    summary = {"GREEN": 0, "RED": 0, "YELLOW": 0, "GRAY": 0}
    for r in rows:
        summary[r["status"]] += 1
    total = len(rows)

    red    = [r for r in rows if r["status"] == "RED"]
    yellow = [r for r in rows if r["status"] == "YELLOW"]
    green  = [r for r in rows if r["status"] == "GREEN"]
    gray   = [r for r in rows if r["status"] == "GRAY"]

    lines = [
        "# Research-integrity audit report",
        "",
        f"_Generated: {datetime.now().isoformat(timespec='seconds')}_",
        "",
        "## Summary",
        "",
        f"- 🔴 **RED**:    {summary['RED']:>3d}  (paper claim contradicts code output)",
        f"- 🟡 **YELLOW**: {summary['YELLOW']:>3d}  (lookup failed / manifest incomplete)",
        f"- 🟢 **GREEN**:  {summary['GREEN']:>3d}  (paper claim matches code output)",
        f"- ⚪ **GRAY**:   {summary['GRAY']:>3d}  (illustrative / deferred per manifest)",
        f"- **Total claims audited**: {total}",
        "",
        ("✅ **Clean audit** — all claims either match code, are explicitly illustrative, "
         "or are deferred future work."
         if summary["RED"] == 0 and summary["YELLOW"] == 0
         else f"⚠️ **{summary['RED']} RED + {summary['YELLOW']} YELLOW** entries need attention "
              "before submission."),
        "",
    ]

    header = "| Status | id | section | paper | code | Δabs | tol | severity | source |"
    sep    = "|---|---|---|---:|---:|---:|---|---|---|"

    if red:
        lines.append("## 🔴 RED — paper claim contradicts code output\n")
        lines.append("These MUST be fixed.  Either the paper number is wrong, the code is buggy, "
                     "or the data is wrong.  Pick one.\n")
        lines.append(header); lines.append(sep)
        for r in red: lines.append(fmt_row(r))
        lines.append("")

    if yellow:
        lines.append("## 🟡 YELLOW — lookup failed / un-anchored\n")
        lines.append("These need EITHER the manifest entry's `code_source` filled in "
                     "OR the corresponding pipeline output produced.\n")
        lines.append(header); lines.append(sep)
        for r in yellow: lines.append(fmt_row(r))
        lines.append("")

    if green:
        lines.append("## 🟢 GREEN — paper matches code\n")
        lines.append(header); lines.append(sep)
        for r in green: lines.append(fmt_row(r))
        lines.append("")

    if gray:
        lines.append("## ⚪ GRAY — illustrative / deferred (audit skipped)\n")
        lines.append(header); lines.append(sep)
        for r in gray: lines.append(fmt_row(r))
        lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] wrote {OUT.relative_to(REPO)}")
    print(f"[report] {summary}")
    return min(summary["RED"], 1)


if __name__ == "__main__":
    sys.exit(main())
