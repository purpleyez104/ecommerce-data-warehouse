#!/usr/bin/env python3
"""Generate M4 DWS/ADS external-table DDL from the aggregate contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_contracts(semantic: dict[str, Any], physical: dict[str, Any]) -> None:
    """验证模型集合、层级、业务键和安全 HDFS 根路径。"""
    models = semantic.get("models", {})
    physical_models = physical.get("models", {})
    if set(models) != set(physical_models) or not models:
        raise ValueError("aggregate semantic and physical model sets differ")
    if physical.get("hdfs_root") != "/warehouse/ecommerce/model":
        raise ValueError("unsafe aggregate hdfs_root")
    for name, model in models.items():
        target = physical_models[name]
        if not IDENTIFIER.fullmatch(name) or not IDENTIFIER.fullmatch(target["database"]):
            raise ValueError(f"unsafe aggregate identifier: {name}")
        location = target.get("location")
        if location is not None and (
            not isinstance(location, str)
            or not location.startswith("/warehouse/ecommerce/")
            or location.endswith("/")
        ):
            raise ValueError(f"{name}: unsafe explicit location")
        if model.get("layer") not in {"dws", "ads"}:
            raise ValueError(f"{name}: invalid aggregate layer")
        columns = {column for column, _ in target["columns"]}
        if not set(model["business_key"]).issubset(columns):
            raise ValueError(f"{name}: missing business key columns")
        if not set(model.get("measures", [])).issubset(columns):
            raise ValueError(f"{name}: missing measure columns")
        if not {"batch_id", "load_time"}.issubset(columns):
            raise ValueError(f"{name}: missing audit columns")


def render_sql(semantic: dict[str, Any], physical: dict[str, Any]) -> str:
    validate_contracts(semantic, physical)
    root = physical["hdfs_root"]
    blocks = []
    for database in sorted({item["database"] for item in physical["models"].values()}):
        blocks.append(f"CREATE DATABASE IF NOT EXISTS {database};")
    for name in sorted(semantic["models"]):
        target = physical["models"][name]
        columns = ",\n  ".join(f"{column} {data_type}" for column, data_type in target["columns"])
        database = target["database"]
        location = target.get("location", f"{root}/{database}/{name}")
        blocks.append(f"""CREATE EXTERNAL TABLE IF NOT EXISTS {database}.{name} (
  {columns}
)
PARTITIONED BY (dt STRING)
STORED AS ORC
LOCATION '{location}'
TBLPROPERTIES ('orc.compress'='SNAPPY');""")
    return "\n\n".join(blocks) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semantic-contract", type=Path, required=True)
    parser.add_argument("--physical-contract", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sql = render_sql(load_json(args.semantic_contract), load_json(args.physical_contract))
    if args.output:
        args.output.write_text(sql, encoding="utf-8", newline="\n")
    else:
        print(sql, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
