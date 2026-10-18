#!/usr/bin/env python3
"""根据 Behavior ODS Contract 生成独立的 Hive 外部表 DDL。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from pathlib import PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "hive/ods/behavior_event_contract.json"
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SUPPORTED_TYPES = {"STRING", "TIMESTAMP", "BIGINT", "INT"}


def load_contract(path: Path = CONTRACT_PATH) -> dict:
    """读取并校验 Behavior ODS 表、字段和分区 Contract。"""
    contract = json.loads(path.read_text(encoding="utf-8"))
    target = contract.get("target", {})
    if target.get("table") != "ods_behavior_event":
        raise ValueError("behavior target table must be ods_behavior_event")
    if target.get("partition_column") != "dt" or target.get("partition_source") != "to_date(event_time)":
        raise ValueError("behavior partition contract must use event_time business date")
    columns = [*contract.get("source_schema", []), *contract.get("audit_columns", [])]
    names = [column.get("name") for column in columns]
    if len(names) != len(set(names)) or not names:
        raise ValueError("behavior columns must be non-empty and unique")
    for column in columns:
        if not IDENTIFIER.fullmatch(str(column.get("name", ""))):
            raise ValueError("invalid behavior column name")
        if column.get("type") not in SUPPORTED_TYPES:
            raise ValueError("unsupported behavior Hive type")
    if not contract.get("event_types") or not contract.get("quality_rules"):
        raise ValueError("behavior event types and quality rules are required")
    return contract


def _location(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"/[A-Za-z0-9._/-]+", value):
        raise ValueError("invalid behavior HDFS location")
    path = PurePosixPath(value)
    if path == PurePosixPath("/") or ".." in path.parts:
        raise ValueError("invalid behavior HDFS location")
    return str(path)


def render_ddl(database: str = "ecommerce_ods", contract_path: Path = CONTRACT_PATH) -> str:
    """生成单表 DDL；不执行 Hive，也不接触 Behavior Bundle。"""
    if not IDENTIFIER.fullmatch(database):
        raise ValueError("invalid Hive database identifier")
    contract = load_contract(contract_path)
    target = contract["target"]
    location = _location(target["location"])
    columns = [*contract["source_schema"], *contract["audit_columns"]]
    rendered_columns = ",\n".join(f"  `{item['name']}` {item['type']}" for item in columns)
    return "\n".join([
        "-- Generated from hive/ods/behavior_event_contract.json.",
        "-- Behavior ODS is independent from the 21-table MySQL/DataX contract.",
        f"CREATE DATABASE IF NOT EXISTS `{database}`;",
        "",
        f"CREATE EXTERNAL TABLE IF NOT EXISTS `{database}`.`{target['table']}` (",
        rendered_columns,
        ")",
        "PARTITIONED BY (`dt` STRING)",
        "STORED AS ORC",
        f"LOCATION '{location}'",
        "TBLPROPERTIES ('orc.compress'='SNAPPY');",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="ecommerce_ods")
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_ddl(args.database, args.contract), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
