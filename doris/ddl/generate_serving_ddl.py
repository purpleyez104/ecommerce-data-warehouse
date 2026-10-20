#!/usr/bin/env python3
"""根据 M6 Serving Contract 生成确定性的 Doris DDL。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
TYPE = re.compile(r"^(?:DATE|BIGINT|DATETIME|VARCHAR\([1-9][0-9]*\)|DECIMAL\([1-9][0-9]*,[0-9]+\))$")


def load_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_contract(contract: dict[str, Any]) -> None:
    """拒绝不安全标识符和偏离已确认单表 Contract 的配置。"""
    if contract.get("contract_version") != "m6-serving-v1":
        raise ValueError("unsupported serving contract version")
    if contract.get("database") != "ecommerce_serving" or contract.get("table") != "ads_daily_business_overview":
        raise ValueError("unexpected serving target")
    if contract.get("source") != "ecommerce_ads.ads_daily_business_overview":
        raise ValueError("unexpected serving source")
    if contract.get("key_model") != "UNIQUE KEY" or contract.get("key_columns") != ["business_date"]:
        raise ValueError("serving table must use business_date unique key")
    if contract.get("distribution_columns") != ["business_date"]:
        raise ValueError("unexpected distribution columns")
    if contract.get("buckets") != 2 or contract.get("replication_num") != 2:
        raise ValueError("unexpected serving topology")
    columns = contract.get("columns", [])
    names = [item[0] for item in columns]
    if not columns or len(names) != len(set(names)) or names[0] != "business_date":
        raise ValueError("invalid serving columns")
    for name, data_type, nullable in columns:
        if not IDENTIFIER.fullmatch(name) or not TYPE.fullmatch(data_type) or not isinstance(nullable, bool):
            raise ValueError(f"invalid serving column: {name}")


def render_sql(contract: dict[str, Any]) -> str:
    validate_contract(contract)
    columns = ",\n  ".join(
        f"`{name}` {data_type} {'NULL' if nullable else 'NOT NULL'}"
        for name, data_type, nullable in contract["columns"]
    )
    database = contract["database"]
    table = contract["table"]
    return f"""CREATE DATABASE IF NOT EXISTS `{database}`;

CREATE TABLE IF NOT EXISTS `{database}`.`{table}` (
  {columns}
)
UNIQUE KEY(`business_date`)
DISTRIBUTED BY HASH(`business_date`) BUCKETS {contract['buckets']}
PROPERTIES (
  "enable_unique_key_merge_on_write" = "true",
  "replication_num" = "{contract['replication_num']}"
);
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
