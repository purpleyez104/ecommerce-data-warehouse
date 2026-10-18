#!/usr/bin/env python3
"""Generate independent final ODS row-count expectations from Source and replay contracts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_contract(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tables = payload.get("tables")
    if not isinstance(tables, dict) or not tables:
        raise ValueError("invalid ODS table contract")
    return payload


def render_source_sql(contract: dict) -> str:
    """为非快照表生成按业务日期聚合的独立 Source 查询。"""
    statements = []
    for source, policy in contract["tables"].items():
        if policy["load_strategy"] == "full_snapshot":
            continue
        business_time = policy["business_time"]
        column = business_time.get("column")
        if not IDENTIFIER.fullmatch(source) or business_time.get("mode") != "column" or not IDENTIFIER.fullmatch(column or ""):
            raise ValueError(f"{source}: invalid business_time contract")
        statements.append(
            f"SELECT '{source}',DATE_FORMAT(`{column}`,'%Y-%m-%d'),COUNT(*) "
            f"FROM `{source}` GROUP BY DATE_FORMAT(`{column}`,'%Y-%m-%d') "
            f"ORDER BY DATE_FORMAT(`{column}`,'%Y-%m-%d');"
        )
    return "\n".join(statements) + "\n"


def load_source_counts(path: Path, expected_tables: set[str]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {table: {} for table in expected_tables}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        fields = line.split("\t")
        if len(fields) != 3 or fields[0] not in counts or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fields[1]):
            raise ValueError(f"invalid source count row at line {number}")
        value = int(fields[2])
        if value <= 0 or fields[1] in counts[fields[0]]:
            raise ValueError(f"invalid or duplicate source count at line {number}")
        counts[fields[0]][fields[1]] = value
    missing = sorted(table for table, values in counts.items() if not values)
    if missing:
        raise ValueError(f"missing source counts: {', '.join(missing)}")
    return counts


def build_expectations(contract: dict, source_counts: dict[str, dict[str, int]], replay_bundle: Path) -> dict:
    """合并最终 Source 分组计数和逐日 full_snapshot 合约。"""
    expected: dict[str, dict] = {}
    snapshot_tables = {
        source for source, policy in contract["tables"].items()
        if policy["load_strategy"] == "full_snapshot"
    }
    if set(source_counts) != set(contract["tables"]) - snapshot_tables:
        raise ValueError("source count table set does not match non-snapshot contract tables")
    for source, dates in source_counts.items():
        expected[source] = {
            "row_count": sum(dates.values()),
            "affected_business_dates": sorted(dates),
            "business_date_row_counts": dict(sorted(dates.items())),
        }

    batch_paths = [replay_bundle / "bootstrap/ods_batch_contract.json"]
    batch_paths.extend(replay_bundle / f"daily/day_{day:02d}/ods_batch_contract.json" for day in range(61, 91))
    snapshot_counts = {table: {} for table in snapshot_tables}
    for batch_path in batch_paths:
        batch = json.loads(batch_path.read_text(encoding="utf-8"))
        business_date = batch["business_date"]
        for table in snapshot_tables:
            item = batch["expected_tables"][table]
            if item["business_date_row_counts"] != {business_date: item["row_count"]}:
                raise ValueError(f"{batch_path}: invalid full_snapshot expectation for {table}")
            snapshot_counts[table][business_date] = item["row_count"]
    for table, dates in snapshot_counts.items():
        if len(dates) != 31:
            raise ValueError(f"{table}: expected 31 snapshot partitions")
        expected[table] = {
            "row_count": sum(dates.values()),
            "affected_business_dates": sorted(dates),
            "business_date_row_counts": dict(sorted(dates.items())),
        }
    return {"expectation_version": 1, "expected_tables": expected}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("datax/config/ods_tables.json"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    render = subparsers.add_parser("render-source-sql")
    render.add_argument("--output", type=Path, required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--source-counts", type=Path, required=True)
    build.add_argument("--replay-bundle", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = load_contract(args.contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.command == "render-source-sql":
        content = render_source_sql(contract)
    else:
        snapshot_tables = {
            source for source, policy in contract["tables"].items()
            if policy["load_strategy"] == "full_snapshot"
        }
        counts = load_source_counts(args.source_counts, set(contract["tables"]) - snapshot_tables)
        content = json.dumps(build_expectations(contract, counts, args.replay_bundle), ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(content, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
