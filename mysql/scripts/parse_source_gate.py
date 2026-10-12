#!/usr/bin/env python3
"""Parse the strict Source Gate TSV protocol."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


RULE_PATTERN = re.compile(r"^-- RULE: ([a-z0-9_.]+)$", re.MULTILINE)


def parse(sql_path: Path, output_path: Path) -> list[str]:
    expected = RULE_PATTERN.findall(sql_path.read_text(encoding="utf-8"))
    if not expected or len(expected) != len(set(expected)):
        raise ValueError("source_gate.sql contains no rules or duplicate rule markers")
    actual: dict[str, int] = {}
    for line_number, raw in enumerate(output_path.read_text(encoding="utf-8").splitlines(), start=1):
        parts = raw.split("\t")
        if len(parts) != 2:
            raise ValueError(f"line {line_number}: expected exactly two TSV fields")
        rule_id, count_text = parts
        if rule_id not in expected:
            raise ValueError(f"line {line_number}: unknown rule_id {rule_id!r}")
        if rule_id in actual:
            raise ValueError(f"line {line_number}: duplicate rule_id {rule_id!r}")
        if not re.fullmatch(r"0|[1-9][0-9]*", count_text):
            raise ValueError(f"line {line_number}: violation_count is not a non-negative integer")
        actual[rule_id] = int(count_text)
    missing = sorted(set(expected) - set(actual))
    if missing:
        raise ValueError(f"missing rule_id(s): {', '.join(missing)}")
    failed = [f"{rule_id}={actual[rule_id]}" for rule_id in expected if actual[rule_id] != 0]
    if failed:
        raise ValueError("Source Gate violations: " + ", ".join(failed))
    return expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sql", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        rules = parse(args.sql, args.output)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Source Gate passed: {len(rules)} rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
