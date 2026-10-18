#!/usr/bin/env python3
"""Render an independent Hive ODS gate for one published replay batch."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DATAX_SCRIPTS = REPO_ROOT / "datax/scripts"
if str(DATAX_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DATAX_SCRIPTS))

import generate_job


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
FOREIGN_KEY = re.compile(
    r"FOREIGN KEY \((?P<child>[^)]+)\)\s+REFERENCES `(?P<parent>[A-Za-z_][A-Za-z0-9_]*)` \((?P<parent_columns>[^)]+)\)",
    re.MULTILINE,
)


def _quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _columns(raw: str) -> list[str]:
    return [item.strip().strip("`") for item in raw.split(",")]


def render_gate_sql(
    contract: dict,
    batch: dict,
    database: str,
    target_expectations: dict | None = None,
    stage_root: str | None = None,
) -> str:
    if not IDENTIFIER.fullmatch(database):
        raise ValueError("invalid ODS database")
    expected_tables = batch.get("expected_tables")
    if not isinstance(expected_tables, dict) or set(expected_tables) != set(contract["tables"]):
        raise ValueError("expected_tables must exactly match the ODS contract")
    mode = batch.get("mode")
    if mode not in {"bootstrap", "incremental"}:
        raise ValueError("invalid batch mode")
    if mode == "incremental":
        if not isinstance(target_expectations, dict) or set(target_expectations) != set(contract["tables"]):
            raise ValueError("incremental gate requires complete target expectations")
        if stage_root is None:
            raise ValueError("incremental gate requires stage_root")
    mysql_types = generate_job.parse_ddl_mysql_types()
    lines = ["-- independent published ODS gate", "SET spark.sql.ansi.enabled=true;"]
    for source_table, policy in contract["tables"].items():
        target = policy["target_table"]
        expected = expected_tables[source_table]
        target_expected = expected if mode == "bootstrap" else target_expectations[source_table]
        target_total = target_expected.get("row_count")
        target_date_counts = target_expected.get("business_date_row_counts")
        if (
            not isinstance(target_total, int)
            or target_total < 0
            or not isinstance(target_date_counts, dict)
            or any(not isinstance(value, int) or value <= 0 for value in target_date_counts.values())
            or sum(target_date_counts.values()) != target_total
        ):
            raise ValueError(f"{source_table}: invalid target expectations")
        dates = expected["affected_business_dates"]
        pk = policy["primary_key"]
        pk_null = " OR ".join(f"`{column}` IS NULL" for column in pk)
        uniqueness_columns = pk + (["dt"] if policy["load_strategy"] == "full_snapshot" else [])
        pk_group = ", ".join(f"`{column}`" for column in uniqueness_columns)
        lines.extend([
            f"-- {source_table} -> {target}",
            f"SELECT assert_true(COUNT(*)={target_total}, '{target}: total row count mismatch') FROM `{database}`.`{target}`;",
            f"SELECT assert_true(COUNT(*)=0, '{target}: null primary key') FROM `{database}`.`{target}` WHERE {pk_null};",
            f"SELECT assert_true(COUNT(*)=0, '{target}: duplicate primary key') FROM (SELECT {pk_group}, COUNT(*) c FROM `{database}`.`{target}` GROUP BY {pk_group} HAVING c>1) d;",
            f"SELECT assert_true(COUNT(*)=0, '{target}: partition/audit mismatch') FROM `{database}`.`{target}` WHERE NOT (`business_date` <=> `dt`) OR `batch_id` IS NULL OR NOT (`source_table` <=> {_quoted(source_table)}) OR `extract_time` IS NULL;",
        ])
        for date, count in sorted(target_date_counts.items()):
            lines.append(
                f"SELECT assert_true(COUNT(*)={count}, '{target}: {date} partition row count mismatch') "
                f"FROM `{database}`.`{target}` WHERE `dt`={_quoted(date)};"
            )
        if mode == "incremental" and expected["row_count"]:
            stage = f"{stage_root.rstrip('/')}/{target}/batch_id={batch['batch_id']}"
            pk_match = " AND ".join(
                [*(f"t.`{column}` <=> s.`{column}`" for column in pk), "t.`dt` <=> s.`business_date`"]
            )
            lines.append(
                f"SELECT assert_true(COUNT(*)=0, '{target}: staged rows missing after publish') "
                f"FROM orc.`{stage}` s LEFT JOIN `{database}`.`{target}` t ON {pk_match} "
                f"WHERE t.`{pk[0]}` IS NULL OR NOT (t.`batch_id` <=> {_quoted(batch['batch_id'])});"
            )
        type_checks = []
        for column in policy["columns"]:
            expected_type = generate_job.mysql_to_hive_type(mysql_types[source_table][column["name"]]).lower()
            type_checks.append(f"typeof(`{column['name']}`)={_quoted(expected_type)}")
        type_checks.extend(f"typeof(`{column}`)='string'" for column in ("business_date", "extract_time", "batch_id", "source_table", "dt"))
        lines.append(
            f"SELECT assert_true({' AND '.join(type_checks)}, '{target}: Hive type mismatch') "
            f"FROM `{database}`.`{target}` LIMIT 1;"
        )

    ddl = generate_job.SOURCE_DDL.read_text(encoding="utf-8")
    targets = {source: policy["target_table"] for source, policy in contract["tables"].items()}
    for table_match in generate_job.DDL_TABLE_PATTERN.finditer(ddl):
        child_table = table_match.group("table")
        for fk in FOREIGN_KEY.finditer(table_match.group("body")):
            parent_table = fk.group("parent")
            child_columns = _columns(fk.group("child"))
            parent_columns = _columns(fk.group("parent_columns"))
            if len(child_columns) != len(parent_columns):
                raise ValueError(f"invalid foreign key column count: {child_table} -> {parent_table}")
            join = " AND ".join(f"c.`{left}`=p.`{right}`" for left, right in zip(child_columns, parent_columns))
            present = " AND ".join(f"c.`{column}` IS NOT NULL" for column in child_columns)
            lines.append(
                f"SELECT assert_true(COUNT(*)=0, '{targets[child_table]} -> {targets[parent_table]}: orphan reference') "
                f"FROM `{database}`.`{targets[child_table]}` c LEFT JOIN `{database}`.`{targets[parent_table]}` p ON {join} "
                f"WHERE {present} AND p.`{parent_columns[0]}` IS NULL;"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=generate_job.DEFAULT_CONTRACT)
    parser.add_argument("--batch-contract", type=Path, required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--target-expectations", type=Path)
    parser.add_argument("--stage-root")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = generate_job.load_contract(args.contract)
    batch = json.loads(args.batch_contract.read_text(encoding="utf-8"))
    target_expectations = (
        json.loads(args.target_expectations.read_text(encoding="utf-8"))["expected_tables"]
        if args.target_expectations else None
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        render_gate_sql(contract, batch, args.database, target_expectations, args.stage_root),
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
