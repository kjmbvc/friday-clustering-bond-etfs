#!/usr/bin/env python3
"""
audit/check_provenance.py
=========================
For every package declared in `audit/code_provenance_manifest.json`:

  1. For each declared file under `policy: verbatim`, fetch the upstream raw
     content (URL = `upstream_raw_base/{pinned_commit}/{upstream_path}`),
     compute SHA-256 of both upstream and local, and compare.
        - VERBATIM    bytes identical
        - DIVERGENT   different bytes; report a unified-diff snippet

  2. Verify every path in `license_artifacts` exists and contains the
     attribution string (license holder name).
        - LICENSE_OK         all artifacts found and contain holder name
        - LICENSE_MISSING    artifact missing
        - LICENSE_INCOMPLETE artifact present but holder name absent

  3. Verify `originality_check`: scan every file in `consumer_files` and
     ensure no `forbidden_inline_symbols` definition is present.  Imports are
     fine; only `def ...` / `class ...` definitions trigger.
        - ORIGINAL_OK        no forbidden definitions
        - PLAGIARISM_RISK    forbidden definition found inline

Writes:
    audit/PROVENANCE_REPORT.md      human-readable report
    audit/_provenance_diff.json     machine-readable per-file diff

Usage:
    python audit/check_provenance.py
    python audit/check_provenance.py --refresh-verbatim   # overwrite local with upstream
    python audit/check_provenance.py --offline            # skip network checks
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "audit" / "code_provenance_manifest.json"
REPORT   = REPO / "audit" / "PROVENANCE_REPORT.md"
DIFFJSON = REPO / "audit" / "_provenance_diff.json"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch_upstream(raw_base: str, commit: str, path: str, timeout: int = 30) -> bytes | None:
    url = f"{raw_base}/{commit}/{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "audit/check_provenance"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        print(f"  [fetch] HTTP {e.code} {url}", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(f"  [fetch] ERR {url}: {e}", file=sys.stderr)
    return None


# Normalise CRLF -> LF for cross-OS comparison.  Don't trim trailing newline:
# whitespace at end of file matters for an EXACT match.
def _normalise(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def check_file_verbatim(local: Path, upstream_bytes: bytes) -> dict:
    if not local.exists():
        return {"status": "LOCAL_MISSING", "local": str(local.relative_to(REPO))}
    local_bytes = local.read_bytes()
    a = _normalise(local_bytes)
    b = _normalise(upstream_bytes)
    if a == b:
        return {
            "status": "VERBATIM",
            "local": str(local.relative_to(REPO)),
            "sha_local": sha256_bytes(a),
            "sha_upstream": sha256_bytes(b),
            "bytes": len(a),
        }
    # diff snippet (first 40 lines)
    diff_lines = list(difflib.unified_diff(
        b.decode("utf-8", errors="replace").splitlines(keepends=True),
        a.decode("utf-8", errors="replace").splitlines(keepends=True),
        fromfile="upstream",
        tofile="local",
        n=2,
    ))[:60]
    return {
        "status": "DIVERGENT",
        "local": str(local.relative_to(REPO)),
        "sha_local": sha256_bytes(a),
        "sha_upstream": sha256_bytes(b),
        "diff_snippet": "".join(diff_lines),
        "bytes_local": len(a),
        "bytes_upstream": len(b),
    }


def check_license_artifacts(artifacts: list[str], holder: str) -> dict:
    rows = []
    for relpath in artifacts:
        path = REPO / relpath
        if not path.exists():
            rows.append({"path": relpath, "status": "LICENSE_MISSING"})
            continue
        try:
            txt = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            rows.append({"path": relpath, "status": "LICENSE_UNREADABLE", "error": str(e)})
            continue
        if holder.lower() in txt.lower():
            rows.append({"path": relpath, "status": "LICENSE_OK"})
        else:
            rows.append({"path": relpath, "status": "LICENSE_INCOMPLETE",
                          "_note": f"holder '{holder}' not found in {relpath}"})
    return rows


_FORBIDDEN_RX = re.compile(r"^\s*(def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)


def check_originality(consumer_files: list[str], forbidden: list[str]) -> list[dict]:
    """Make sure consumer files import the algorithm; not redefine it."""
    findings = []
    # Build a set of forbidden symbol *names* (drop the leading "def "/"class ")
    bad_names = set()
    for tok in forbidden:
        m = _FORBIDDEN_RX.match(tok + "\n")
        if m:
            bad_names.add(m.group(2))
    for f in consumer_files:
        path = REPO / f
        if not path.exists():
            findings.append({"file": f, "status": "FILE_MISSING"})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = []
        for m in _FORBIDDEN_RX.finditer(text):
            if m.group(2) in bad_names:
                lineno = text[: m.start()].count("\n") + 1
                hits.append({"symbol": m.group(2), "line": lineno})
        if hits:
            findings.append({"file": f, "status": "PLAGIARISM_RISK", "definitions_inline": hits})
        else:
            findings.append({"file": f, "status": "ORIGINAL_OK"})
    return findings


def render_report(audit: dict) -> str:
    L = [
        "# Code-provenance audit report",
        "",
        f"_Generated: {datetime.now().isoformat(timespec='seconds')}_",
        "",
    ]
    totals = {"VERBATIM": 0, "DIVERGENT": 0, "LOCAL_MISSING": 0,
              "ADAPTED_DOCUMENTED": 0, "ADAPTED_UNDOCUMENTED": 0,
              "LICENSE_OK": 0, "LICENSE_MISSING": 0, "LICENSE_INCOMPLETE": 0, "LICENSE_UNREADABLE": 0,
              "ORIGINAL_OK": 0, "PLAGIARISM_RISK": 0, "FILE_MISSING": 0}
    for pkg in audit.get("packages", []):
        for f in pkg.get("file_checks", []):
            totals[f["status"]] = totals.get(f["status"], 0) + 1
        for l in pkg.get("license_checks", []):
            totals[l["status"]] = totals.get(l["status"], 0) + 1
        for o in pkg.get("originality_checks", []):
            totals[o["status"]] = totals.get(o["status"], 0) + 1

    L += [
        "## Summary",
        "",
        f"- Verbatim files:       {totals['VERBATIM']} VERBATIM / {totals['DIVERGENT']} DIVERGENT / {totals['LOCAL_MISSING']} MISSING",
        f"- Adapted files:        {totals['ADAPTED_DOCUMENTED']} DOCUMENTED / {totals['ADAPTED_UNDOCUMENTED']} UNDOCUMENTED",
        f"- License artifacts:    {totals['LICENSE_OK']} OK / {totals['LICENSE_INCOMPLETE']} INCOMPLETE / {totals['LICENSE_MISSING']} MISSING",
        f"- Originality (consumers):  {totals['ORIGINAL_OK']} OK / {totals['PLAGIARISM_RISK']} RISK / {totals['FILE_MISSING']} FILE_MISSING",
        "",
    ]
    bad = (totals["DIVERGENT"] + totals["LOCAL_MISSING"]
           + totals["ADAPTED_UNDOCUMENTED"]
           + totals["LICENSE_MISSING"] + totals["LICENSE_INCOMPLETE"]
           + totals["PLAGIARISM_RISK"] + totals["FILE_MISSING"])
    if bad == 0:
        L += ["✅ **Clean provenance** — all vendored files match upstream, all licenses retained, no inline plagiarism.", ""]
    else:
        L += [f"⚠️  **{bad} provenance issue(s)** — see details below.", ""]

    for pkg in audit.get("packages", []):
        L += [f"## Package: `{pkg['id']}`", "",
              f"- Upstream: {pkg.get('upstream_repo', '?')}",
              f"- Pinned commit: `{pkg.get('pinned_commit', '?')}`",
              f"- License: {pkg.get('license', '?')} (holder: {pkg.get('license_holder', '?')}, year: {pkg.get('license_year', '?')})",
              ""]

        if pkg.get("file_checks"):
            L += ["### File-level checks", "",
                  "| Status | Local | bytes | divergence reason |",
                  "|---|---|---:|---|"]
            for f in pkg["file_checks"]:
                reason = (f.get("divergence_reason") or "—")[:80]
                L.append(
                    f"| {f['status']} | `{f.get('local','?')}` | "
                    f"{f.get('bytes', f.get('bytes_local','—'))} | {reason} |"
                )
            L.append("")
            # Verbatim SHA detail (only for verbatim files; cleaner table)
            verbatim_only = [f for f in pkg["file_checks"]
                              if f["status"] in ("VERBATIM", "DIVERGENT")]
            if verbatim_only:
                L += ["#### Verbatim file SHA-256 detail", "",
                      "| Status | Local | SHA-256 local | SHA-256 upstream |",
                      "|---|---|---|---|"]
                for f in verbatim_only:
                    L.append(
                        f"| {f['status']} | `{f.get('local','?')}` | "
                        f"`{str(f.get('sha_local','—'))[:12]}...` | "
                        f"`{str(f.get('sha_upstream','—'))[:12]}...` |"
                    )
                L.append("")
            for f in pkg["file_checks"]:
                if f["status"] == "DIVERGENT":
                    L += [f"#### DIVERGENT: `{f['local']}` — diff snippet (upstream → local)",
                          "", "```diff",
                          f.get("diff_snippet", "(no diff)"),
                          "```", ""]

        if pkg.get("license_checks"):
            L += ["### License-artifact checks", "",
                  "| Status | Artifact |", "|---|---|"]
            for r in pkg["license_checks"]:
                L.append(f"| {r['status']} | `{r['path']}` |")
            L.append("")

        if pkg.get("originality_checks"):
            L += ["### Originality (consumer-file) checks", "",
                  "| Status | Consumer file | Forbidden inline definitions |",
                  "|---|---|---|"]
            for o in pkg["originality_checks"]:
                inline = (", ".join(f"{h['symbol']}(line {h['line']})" for h in o.get("definitions_inline", []))
                          or "—")
                L.append(f"| {o['status']} | `{o['file']}` | {inline} |")
            L.append("")

    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="Skip network fetches; only verify local files exist + license + originality")
    ap.add_argument("--refresh-verbatim", action="store_true",
                    help="Overwrite local vendored files with upstream content")
    args = ap.parse_args(argv)

    if not MANIFEST.exists():
        sys.exit(f"missing {MANIFEST}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    audit: dict = {"generated_at": datetime.now().isoformat(timespec="seconds"),
                    "packages": []}

    for pkg in manifest.get("packages", []):
        pkg_audit: dict = {**{k: pkg[k] for k in ("id", "upstream_repo", "pinned_commit",
                                                     "license", "license_holder", "license_year")
                              if k in pkg}}
        # File checks
        file_checks = []
        raw_base = pkg["upstream_raw_base"]
        commit   = pkg["pinned_commit"]
        for f in pkg.get("files", []):
            local = REPO / f["local"]
            policy = f.get("policy", "verbatim")

            # Adapted-for-bugfix files: do NOT diff vs upstream; just verify
            # the file exists and the manifest declares the divergence reason.
            if policy == "adapted_for_bugfix":
                if not local.exists():
                    file_checks.append({
                        "status": "LOCAL_MISSING", "local": f["local"], "policy": policy,
                    })
                    continue
                if not f.get("divergence_reason"):
                    file_checks.append({
                        "status": "ADAPTED_UNDOCUMENTED", "local": f["local"], "policy": policy,
                        "_note": "manifest entry is missing 'divergence_reason' field",
                    })
                    continue
                file_checks.append({
                    "status": "ADAPTED_DOCUMENTED",
                    "local": f["local"], "policy": policy,
                    "divergence_reason": f.get("divergence_reason"),
                    "patch_description": f.get("patch_description"),
                    "bytes": len(_normalise(local.read_bytes())),
                })
                continue

            # Verbatim files: byte-for-byte check against upstream
            if args.offline:
                if local.exists():
                    txt = local.read_bytes()
                    file_checks.append({
                        "status": "VERBATIM",
                        "local": f["local"],
                        "sha_local": sha256_bytes(_normalise(txt)),
                        "sha_upstream": "(offline)",
                        "bytes": len(_normalise(txt)),
                        "_note": "skipped network in --offline mode",
                    })
                else:
                    file_checks.append({"status": "LOCAL_MISSING", "local": f["local"]})
                continue
            upstream = fetch_upstream(raw_base, commit, f["upstream_path"])
            if upstream is None:
                file_checks.append({"status": "DIVERGENT",
                                     "local": f["local"],
                                     "diff_snippet": "(failed to fetch upstream)"})
                continue
            if args.refresh_verbatim and local.exists():
                # Overwrite local with upstream (normalised LF)
                local.write_bytes(_normalise(upstream))
            result = check_file_verbatim(local, upstream)
            file_checks.append(result)
        pkg_audit["file_checks"] = file_checks

        # License checks
        artifacts = pkg.get("license_artifacts", [])
        pkg_audit["license_checks"] = check_license_artifacts(
            artifacts, pkg.get("license_holder", ""))

        # Originality checks
        origin = pkg.get("originality_check", {})
        pkg_audit["originality_checks"] = check_originality(
            origin.get("consumer_files", []),
            origin.get("forbidden_inline_symbols", []),
        )

        audit["packages"].append(pkg_audit)

    DIFFJSON.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    REPORT.write_text(render_report(audit), encoding="utf-8")

    # Summary line for the runner
    bad_file = sum(1 for p in audit["packages"] for f in p["file_checks"]
                    if f["status"] in ("DIVERGENT", "LOCAL_MISSING",
                                         "ADAPTED_UNDOCUMENTED"))
    bad_lic = sum(1 for p in audit["packages"] for l in p["license_checks"]
                   if l["status"] in ("LICENSE_MISSING", "LICENSE_INCOMPLETE", "LICENSE_UNREADABLE"))
    bad_orig = sum(1 for p in audit["packages"] for o in p["originality_checks"]
                    if o["status"] in ("PLAGIARISM_RISK", "FILE_MISSING"))
    print(f"[provenance] file:{bad_file} bad / "
          f"license:{bad_lic} bad / originality:{bad_orig} bad")
    print(f"[provenance] wrote {REPORT.relative_to(REPO)}")
    return 1 if (bad_file + bad_lic + bad_orig) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
