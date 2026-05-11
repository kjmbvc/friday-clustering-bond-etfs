#!/usr/bin/env python3
"""
audit/lookup_outputs.py
=======================
Resolve a manifest entry's `code_source` into an actual numerical value pulled
from pipeline output (CSV / JSON).

Used as a library by `compare.py`.  Not normally invoked directly, but does
provide a CLI for quick lookups:

    python audit/lookup_outputs.py tab1_IEF_fri_pct
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO = Path(__file__).resolve().parent.parent


class LookupError(Exception):
    pass


def _csv_lookup(spec: dict) -> float:
    path = REPO / spec["csv_path"]
    if not path.exists():
        raise LookupError(f"file not found: {spec['csv_path']}")
    df = pd.read_csv(path)
    # Filter by lookup_key=lookup_val if specified
    if "lookup_key" in spec and "lookup_val" in spec:
        rows = df[df[spec["lookup_key"]] == spec["lookup_val"]]
        if len(rows) == 0:
            raise LookupError(f"no row with {spec['lookup_key']}={spec['lookup_val']!r}")
        if len(rows) > 1:
            raise LookupError(f"multiple rows match {spec['lookup_key']}={spec['lookup_val']!r}")
        row = rows.iloc[0]
    else:
        if len(df) != 1:
            raise LookupError(f"{path} has {len(df)} rows but no lookup_key/val given")
        row = df.iloc[0]
    col = spec["value_column"]
    if col not in row.index:
        raise LookupError(f"column {col!r} not in {path}; have {list(row.index)}")
    return float(row[col])


def _csv_aggregate(spec: dict) -> float:
    """Compute a scalar aggregate of a CSV column (count, mean, min, max, etc.)."""
    path = REPO / spec["csv_path"]
    if not path.exists():
        raise LookupError(f"file not found: {spec['csv_path']}")
    df = pd.read_csv(path)
    # Optional pre-filter
    for k, v in spec.get("filter", {}).items():
        df = df[df[k] == v]
    col = spec["value_column"]
    if col not in df.columns:
        raise LookupError(f"column {col!r} not in {path}")
    agg = spec["aggregate"]
    s = df[col]
    if agg == "count_nonzero":
        return float((s != 0).sum())
    if agg == "count_eq_1":
        return float((s == 1).sum())
    if agg == "count":
        return float(len(s))
    if agg == "mean":
        return float(s.mean())
    if agg == "median":
        return float(s.median())
    if agg == "min":
        return float(s.min())
    if agg == "max":
        return float(s.max())
    if agg == "range_low":
        return float(s.min())
    if agg == "range_high":
        return float(s.max())
    raise LookupError(f"unknown aggregate: {agg!r}")


def _json_lookup(spec: dict) -> float:
    path = REPO / spec["json_path"]
    if not path.exists():
        raise LookupError(f"file not found: {spec['json_path']}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    for key in spec["key_path"]:
        if isinstance(obj, list):
            obj = obj[key]
        else:
            if key not in obj:
                raise LookupError(f"key {key!r} not in {obj if isinstance(obj, dict) else type(obj).__name__}")
            obj = obj[key]
    return float(obj)


def _computed(spec: dict) -> float:
    """Inline computation from other manifest entries or fixed Python expr."""
    return float(eval(spec["expr"], {"__builtins__": {}}, {}))


def resolve(spec: dict) -> tuple[float, str]:
    """Return (value, source_label)."""
    kind = spec.get("kind", "csv")
    if kind == "csv":
        return _csv_lookup(spec), f"{spec['csv_path']}[{spec.get('lookup_key', '*')}={spec.get('lookup_val', '*')}].{spec['value_column']}"
    if kind == "csv_aggregate":
        flt = ",".join(f"{k}={v}" for k, v in spec.get("filter", {}).items()) or "*"
        return _csv_aggregate(spec), f"{spec['csv_path']}[{flt}].{spec['aggregate']}({spec['value_column']})"
    if kind == "json":
        return _json_lookup(spec), f"{spec['json_path']}:{'/'.join(map(str, spec['key_path']))}"
    if kind == "computed":
        return _computed(spec), f"computed: {spec['expr']}"
    if kind == "illustrative":
        # Same value as published — by design, harness should not flag.
        return float(spec.get("paper_value", float("nan"))), "(illustrative, manifest-declared)"
    raise LookupError(f"unknown kind: {kind!r}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    target_id = sys.argv[1]
    manifest = json.loads((REPO / "audit" / "claims_manifest.json").read_text(encoding="utf-8"))
    for section in manifest.get("claims", []):
        for entry in section.get("entries", []):
            if entry["id"] == target_id:
                try:
                    val, src = resolve(entry)
                    print(f"{target_id}: {val}  <- {src}")
                    return 0
                except LookupError as e:
                    print(f"{target_id}: LOOKUP_ERROR {e}")
                    return 2
    print(f"no manifest entry with id={target_id!r}")
    return 3


if __name__ == "__main__":
    sys.exit(main())
