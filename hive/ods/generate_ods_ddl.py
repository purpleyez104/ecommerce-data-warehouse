#!/usr/bin/env python3
"""Generate the formal 21-table Hive ODS schema from the source contract."""

from __future__ import annotations

import argparse
import importlib.util
import re
from pathlib import Path
from pathlib import PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATE_JOB_PATH = REPO_ROOT / "datax/scripts/generate_job.py"
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
AUDIT_COLUMNS = (
    ("business_date", "STRING", "源记录归属的业务日期"),
    ("extract_time", "STRING", "批次抽取时间"),
    ("batch_id", "STRING", "可审计的批次标识"),
    ("source_table", "STRING", "源表名称"),
)


def _load_generate_job():
    spec = importlib.util.spec_from_file_location("generate_job", GENERATE_JOB_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GENERATE_JOB = _load_generate_job()


def _validate_location_root(location_root: str) -> str:
    if not isinstance(location_root, str) or not re.fullmatch(r"/[A-Za-z0-9._/-]+", location_root):
        raise ValueError("invalid HDFS location root")
    path = PurePosixPath(location_root)
    if path == PurePosixPath("/") or ".." in path.parts:
        raise ValueError("invalid HDFS location root")
    return str(path).rstrip("/")


def render_ddl(database: str, location_root: str = "/warehouse/ecommerce/ods") -> str:
    if not IDENTIFIER.fullmatch(database):
        raise ValueError("invalid Hive database identifier")
    location_root = _validate_location_root(location_root)
    contract = GENERATE_JOB.load_contract()
    mysql_types = GENERATE_JOB.parse_ddl_mysql_types()
    statements = [
        "-- Generated from mysql/ddl/001_ecommerce_oltp.sql and datax/config/ods_tables.json.",
        "-- ODS preserves source semantics and adds four audit columns plus the dt partition.",
        f"CREATE DATABASE IF NOT EXISTS `{database}`;",
        "",
    ]
    for source_table, policy in contract["tables"].items():
        columns = [
            (item["name"], GENERATE_JOB.mysql_to_hive_type(mysql_types[source_table][item["name"]]))
            for item in policy["columns"]
        ]
        column_lines = [f"  `{name}` {column_type}" for name, column_type in columns]
        column_lines.extend(f"  `{name}` {column_type} COMMENT '{comment}'" for name, column_type, comment in AUDIT_COLUMNS)
        statements.extend([
            f"CREATE EXTERNAL TABLE IF NOT EXISTS `{database}`.`{policy['target_table']}` (",
            ",\n".join(column_lines),
            ")",
            "PARTITIONED BY (`dt` STRING)",
            "STORED AS ORC",
            f"LOCATION '{location_root}/{policy['target_table']}'",
            "TBLPROPERTIES ('orc.compress'='SNAPPY');",
            "",
        ])
    return "\n".join(statements)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--location-root", default="/warehouse/ecommerce/ods")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_ddl(args.database, args.location_root), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
