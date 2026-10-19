#!/usr/bin/env python3
"""根据 P1-RECONCILIATION-01 Contract 生成 Hive 对账结果表 DDL。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
SUPPORTED_TYPES = {"STRING", "DATE", "TIMESTAMP", "DECIMAL(38,6)", "DECIMAL(38,12)"}


def load_contract(path: Path) -> dict[str, Any]:
    """读取对账结果 Contract。"""
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("reconciliation contract root must be an object")
    return value


def validate_contract(contract: dict[str, Any]) -> None:
    """验证公共字段、枚举与受控 HDFS Location。"""
    database = contract.get("database")
    table = contract.get("table")
    if not all(isinstance(value, str) and IDENTIFIER.fullmatch(value) for value in (database, table)):
        raise ValueError("invalid reconciliation database or table")
    location = contract.get("location")
    if not isinstance(location, str) or not location.startswith("/warehouse/ecommerce/quality/") or location.endswith("/"):
        raise ValueError("unsafe reconciliation location")
    columns = contract.get("columns")
    partitions = contract.get("partition_columns")
    if not isinstance(columns, list) or not isinstance(partitions, list):
        raise ValueError("reconciliation columns and partitions are required")
    names: list[str] = []
    for column in [*columns, *partitions]:
        if not (isinstance(column, list) and len(column) == 2):
            raise ValueError("invalid reconciliation column")
        name, data_type = column
        if not isinstance(name, str) or not IDENTIFIER.fullmatch(name) or data_type not in SUPPORTED_TYPES:
            raise ValueError(f"invalid reconciliation column: {column}")
        names.append(name)
    required = {
        "reconciliation_id", "metric_id", "definition_version", "business_date",
        "comparison_scope", "left_object", "right_object", "left_value", "right_value",
        "difference_value", "difference_rate", "threshold_value", "status", "batch_id",
        "executed_at", "run_id",
    }
    if not required.issubset(names) or len(names) != len(set(names)):
        raise ValueError("reconciliation contract columns are incomplete or duplicated")
    if contract.get("comparison_scopes") != ["CROSS_LAYER", "OFFLINE_REALTIME"]:
        raise ValueError("reconciliation comparison scopes are invalid")
    if contract.get("allowed_statuses") != ["PASS", "FAIL"]:
        raise ValueError("reconciliation statuses must be PASS and FAIL")


def render_sql(contract: dict[str, Any]) -> str:
    """生成一张同时容纳跨层及未来离实时结果的外部表。"""
    validate_contract(contract)
    columns = ",\n  ".join(f"{name} {data_type}" for name, data_type in contract["columns"])
    partitions = ", ".join(f"{name} {data_type}" for name, data_type in contract["partition_columns"])
    return f"""CREATE DATABASE IF NOT EXISTS {contract['database']};

CREATE EXTERNAL TABLE IF NOT EXISTS {contract['database']}.{contract['table']} (
  {columns}
)
PARTITIONED BY ({partitions})
STORED AS ORC
LOCATION '{contract['location']}'
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
