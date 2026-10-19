#!/usr/bin/env python3
"""根据 P1-QUALITY-01 Contract 生成 Hive 质量结果表 DDL。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
SUPPORTED_TYPES = {"STRING", "DATE", "TIMESTAMP"}


def load_contract(path: Path) -> dict[str, Any]:
    """读取并返回质量结果 Contract。"""
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("quality result contract root must be an object")
    return value


def validate_contract(contract: dict[str, Any]) -> None:
    """验证标识符、列集合和受控 HDFS Location。"""
    database = contract.get("database")
    table = contract.get("table")
    if not all(isinstance(value, str) and IDENTIFIER.fullmatch(value) for value in (database, table)):
        raise ValueError("invalid quality result database or table")
    location = contract.get("location")
    if not isinstance(location, str) or not location.startswith("/warehouse/ecommerce/quality/") or location.endswith("/"):
        raise ValueError("unsafe quality result location")
    columns = contract.get("columns")
    partitions = contract.get("partition_columns")
    if not isinstance(columns, list) or not isinstance(partitions, list):
        raise ValueError("quality result columns and partitions are required")
    names: list[str] = []
    for column in [*columns, *partitions]:
        if not (isinstance(column, list) and len(column) == 2):
            raise ValueError("invalid quality result column")
        name, data_type = column
        if not isinstance(name, str) or not IDENTIFIER.fullmatch(name) or data_type not in SUPPORTED_TYPES:
            raise ValueError(f"invalid quality result column: {column}")
        names.append(name)
    if len(names) != len(set(names)):
        raise ValueError("duplicate quality result column")
    required = {
        "rule_id", "target_object", "business_date", "rule_type", "expected_value",
        "actual_value", "status", "batch_id", "executed_at", "run_id",
    }
    if not required.issubset(names):
        raise ValueError("quality result contract is missing required columns")
    if contract.get("allowed_statuses") != ["PASS", "FAIL"]:
        raise ValueError("quality result statuses must be PASS and FAIL")


def render_sql(contract: dict[str, Any]) -> str:
    """生成 ORC + Snappy 外部表，run_id 用于幂等覆盖单次运行结果。"""
    validate_contract(contract)
    database = contract["database"]
    table = contract["table"]
    columns = ",\n  ".join(f"{name} {data_type}" for name, data_type in contract["columns"])
    partitions = ", ".join(f"{name} {data_type}" for name, data_type in contract["partition_columns"])
    return f"""CREATE DATABASE IF NOT EXISTS {database};

CREATE EXTERNAL TABLE IF NOT EXISTS {database}.{table} (
  {columns}
)
PARTITIONED BY ({partitions})
STORED AS ORC
LOCATION '{contract["location"]}'
TBLPROPERTIES ('orc.compress'='SNAPPY');
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sql = render_sql(load_contract(args.contract))
    if args.output:
        args.output.write_text(sql, encoding="utf-8", newline="\n")
    else:
        print(sql, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
