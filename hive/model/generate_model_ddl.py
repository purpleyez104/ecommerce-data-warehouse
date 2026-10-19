#!/usr/bin/env python3
"""Generate deterministic Hive DIM/DWD DDL from the physical model contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
ALLOWED_TYPES = {"STRING", "BIGINT", "INT", "TIMESTAMP", "DATE", "BOOLEAN"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def validate_physical_contract(semantic: dict[str, Any], physical: dict[str, Any]) -> None:
    """确保物理表完整覆盖语义模型且使用受控 Hive 类型。"""
    semantic_models = semantic.get("models", {})
    physical_models = physical.get("models", {})
    if set(semantic_models) != set(physical_models):
        missing = sorted(set(semantic_models) - set(physical_models))
        extra = sorted(set(physical_models) - set(semantic_models))
        raise ValueError(f"physical model set mismatch: missing={missing}, extra={extra}")

    storage = physical.get("storage", {})
    if storage != {"format": "ORC", "compression": "SNAPPY", "partition_column": "dt", "partition_type": "STRING"}:
        raise ValueError("storage contract must be ORC + SNAPPY partitioned by STRING dt")

    for name, model in physical_models.items():
        expected_db = "ecommerce_dim" if name.startswith("dim_") else "ecommerce_dwd"
        if model.get("database") != expected_db:
            raise ValueError(f"{name}: invalid target database")
        location = model.get("location")
        if location is not None and (
            not isinstance(location, str)
            or not location.startswith("/warehouse/ecommerce/")
            or location.endswith("/")
        ):
            raise ValueError(f"{name}: unsafe explicit location")
        columns = model.get("columns")
        if not isinstance(columns, list) or not columns:
            raise ValueError(f"{name}: columns are required")
        names: list[str] = []
        for item in columns:
            if not isinstance(item, list) or len(item) != 2:
                raise ValueError(f"{name}: every column must be [name, type]")
            column, data_type = item
            if not isinstance(column, str) or not IDENTIFIER.fullmatch(column):
                raise ValueError(f"{name}: invalid column {column}")
            if data_type not in ALLOWED_TYPES:
                raise ValueError(f"{name}.{column}: unsupported type {data_type}")
            names.append(column)
        if len(names) != len(set(names)):
            raise ValueError(f"{name}: duplicate columns")
        for audit in ("batch_id", "load_time"):
            if audit not in names:
                raise ValueError(f"{name}: missing audit column {audit}")
        for key in semantic_models[name]["business_key"]:
            if key not in names:
                raise ValueError(f"{name}: missing business key column {key}")

    zip_columns = {item[0] for item in physical_models["dim_product_zip"]["columns"]}
    required_zip = {"product_sk", "effective_from", "effective_to", "is_current", "attribute_hash"}
    if not required_zip.issubset(zip_columns):
        raise ValueError("dim_product_zip: incomplete SCD2 columns")


def render_ddl(semantic: dict[str, Any], physical: dict[str, Any], root: str) -> str:
    """生成数据库与 14 张 EXTERNAL ORC 表的确定性 DDL。"""
    validate_physical_contract(semantic, physical)
    if not root.startswith("/warehouse/ecommerce/") or root.endswith("/"):
        raise ValueError("root must be an explicit /warehouse/ecommerce path without trailing slash")

    lines = ["CREATE DATABASE IF NOT EXISTS ecommerce_dim;", "CREATE DATABASE IF NOT EXISTS ecommerce_dwd;", ""]
    for name in sorted(physical["models"]):
        model = physical["models"][name]
        column_sql = ",\n".join(f"  `{column}` {data_type}" for column, data_type in model["columns"])
        location = model.get("location", f"{root}/{model['database']}/{name}")
        lines.extend([
            f"CREATE EXTERNAL TABLE IF NOT EXISTS `{model['database']}`.`{name}` (",
            column_sql,
            ")",
            "PARTITIONED BY (`dt` STRING)",
            "STORED AS ORC",
            "LOCATION '" + location + "'",
            "TBLPROPERTIES ('orc.compress'='SNAPPY');",
            "",
        ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semantic-contract", type=Path, required=True)
    parser.add_argument("--physical-contract", type=Path, required=True)
    parser.add_argument("--root", default="/warehouse/ecommerce/model")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    ddl = render_ddl(load_json(args.semantic_contract), load_json(args.physical_contract), args.root)
    if args.output:
        args.output.write_text(ddl, encoding="utf-8", newline="\n")
    else:
        print(ddl, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
