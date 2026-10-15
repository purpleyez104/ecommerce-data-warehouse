#!/usr/bin/env python3
"""Render auditable Spark SQL for ODS staging validation and partition publish."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[2]
DATAX_SCRIPTS = REPO_ROOT / "datax" / "scripts"
if str(DATAX_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DATAX_SCRIPTS))

import generate_job


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _stage_path(stage_root: str, target_table: str, batch_id: str) -> str:
    root = PurePosixPath(generate_job._validate_hdfs_root(stage_root))
    return f"{str(root).rstrip('/')}/{target_table}/batch_id={batch_id}"


def render_batch_sql(contract: dict, batch: dict, stage_root: str, database: str = "ecommerce_ods") -> dict[str, object]:
    if not IDENTIFIER.fullmatch(database):
        raise ValueError("invalid ODS database")
    if batch.get("mode") not in {"bootstrap", "incremental"}:
        raise ValueError("invalid batch mode")
    if not isinstance(batch.get("batch_id"), str) or not generate_job.BATCH_ID_PATTERN.fullmatch(batch["batch_id"]):
        raise ValueError("invalid batch_id")
    generate_job._parse_timestamp("extract_time", batch.get("extract_time"))
    expected_tables = batch.get("expected_tables")
    if not isinstance(expected_tables, dict) or set(expected_tables) != set(contract["tables"]):
        raise ValueError("expected_tables must exactly match the ODS contract")
    validation = ["-- generated validation SQL; execute with Spark SQL before publish", "SET spark.sql.sources.partitionOverwriteMode=dynamic;"]
    publish = ["-- generated publish SQL; execute only after every validation statement succeeds", "SET spark.sql.sources.partitionOverwriteMode=dynamic;"]
    partition_plan = []
    for source_table, policy in contract["tables"].items():
        expected = expected_tables[source_table]
        row_count = expected.get("row_count")
        dates = expected.get("affected_business_dates")
        date_counts = expected.get("business_date_row_counts")
        if not isinstance(row_count, int) or row_count < 0:
            raise ValueError(f"{source_table}: invalid expected row_count")
        if not isinstance(dates, list) or any(not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) for value in dates):
            raise ValueError(f"{source_table}: invalid affected_business_dates")
        if len(dates) != len(set(dates)):
            raise ValueError(f"{source_table}: duplicate affected business date")
        if (
            not isinstance(date_counts, dict)
            or set(date_counts) != set(dates)
            or any(not isinstance(value, int) or value <= 0 for value in date_counts.values())
            or sum(date_counts.values()) != row_count
        ):
            raise ValueError(f"{source_table}: invalid business_date_row_counts")
        target = policy["target_table"]
        stage = _stage_path(stage_root, target, batch["batch_id"])
        source_columns = [item["name"] for item in policy["columns"]]
        all_columns = source_columns + ["business_date", "extract_time", "batch_id", "source_table"]
        projection = ", ".join(f"`{column}`" for column in all_columns)
        pk_condition = " OR ".join(f"`{column}` IS NULL" for column in policy["primary_key"])
        pk_group = ", ".join(f"`{column}`" for column in policy["primary_key"])
        audit_condition = " OR ".join([
            f"NOT (`batch_id` <=> {_quoted(batch['batch_id'])})",
            f"NOT (`source_table` <=> {_quoted(source_table)})",
            f"NOT (`extract_time` <=> {_quoted(batch['extract_time'])})",
        ])
        date_condition = (
            f"business_date IS NULL OR business_date NOT IN ({', '.join(_quoted(value) for value in dates)})"
            if dates else "business_date IS NOT NULL"
        )
        validation.extend([
            f"-- {source_table}: schema projection, row count, PK and business-date checks",
            f"SELECT {projection} FROM orc.`{stage}` LIMIT 0;",
            f"SELECT assert_true(COUNT(*) = {row_count}, '{source_table}: row count mismatch') FROM orc.`{stage}`;",
            f"SELECT assert_true(COUNT(*) = 0, '{source_table}: null primary key') FROM orc.`{stage}` WHERE {pk_condition};",
            f"SELECT assert_true(COUNT(*) = 0, '{source_table}: duplicate primary key') FROM (SELECT {pk_group}, COUNT(*) AS c FROM orc.`{stage}` GROUP BY {pk_group} HAVING c > 1) d;",
            f"SELECT assert_true(COUNT(*) = 0, '{source_table}: unexpected business_date') FROM orc.`{stage}` WHERE {date_condition};",
            f"SELECT assert_true(COUNT(*) = 0, '{source_table}: audit field mismatch') FROM orc.`{stage}` WHERE {audit_condition};",
        ])
        for business_date in sorted(dates):
            validation.append(
                f"SELECT assert_true(COUNT(*) = {date_counts[business_date]}, "
                f"'{source_table}: {business_date} row count mismatch') "
                f"FROM orc.`{stage}` WHERE business_date={_quoted(business_date)};"
            )
            publish.append(f"-- {source_table} -> {database}.{target}, dt={business_date}")
            if batch["mode"] == "bootstrap":
                publish.extend([
                    f"INSERT OVERWRITE TABLE `{database}`.`{target}` PARTITION (`dt`={_quoted(business_date)})",
                    f"SELECT {projection} FROM orc.`{stage}` WHERE business_date={_quoted(business_date)};",
                ])
            else:
                existing_projection = ", ".join(f"t.`{column}`" for column in all_columns)
                stage_projection = ", ".join(f"s.`{column}`" for column in all_columns)
                pk_match = " AND ".join(
                    f"t.`{column}` <=> s.`{column}`" for column in policy["primary_key"]
                )
                merge_name = "_ods_merge_" + hashlib.sha256(
                    f"{batch['batch_id']}|{target}|{business_date}".encode("utf-8")
                ).hexdigest()[:16]
                publish.extend([
                    f"CACHE TABLE `{merge_name}` AS",
                    f"  SELECT {existing_projection} FROM `{database}`.`{target}` t",
                    f"  WHERE t.`dt`={_quoted(business_date)} AND NOT EXISTS (",
                    f"    SELECT 1 FROM orc.`{stage}` s WHERE s.business_date={_quoted(business_date)} AND {pk_match}",
                    "  )",
                    "  UNION ALL",
                    f"  SELECT {stage_projection} FROM orc.`{stage}` s WHERE s.business_date={_quoted(business_date)};",
                    f"INSERT OVERWRITE TABLE `{database}`.`{target}` PARTITION (`dt`={_quoted(business_date)})",
                    f"SELECT {projection} FROM `{merge_name}`;",
                    f"UNCACHE TABLE `{merge_name}`;",
                ])
            publish.append(f"ALTER TABLE `{database}`.`{target}` ADD IF NOT EXISTS PARTITION (`dt`={_quoted(business_date)});")
            partition_plan.append({"source_table": source_table, "target_table": target, "dt": business_date, "stage_path": stage})
    return {
        "validation_sql": "\n".join(validation) + "\n",
        "publish_sql": "\n".join(publish) + "\n",
        "partition_plan": partition_plan,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--batch-contract", type=Path, required=True)
    parser.add_argument("--stage-root", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--database", default="ecommerce_ods")
    args = parser.parse_args(argv)
    contract = generate_job.load_contract(args.contract)
    batch = json.loads(args.batch_contract.read_text(encoding="utf-8"))
    result = render_batch_sql(contract, batch, args.stage_root, args.database)
    if args.output_dir.exists():
        raise FileExistsError(f"output directory already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "validation.sql").write_text(result["validation_sql"], encoding="utf-8", newline="\n")
    (args.output_dir / "publish.sql").write_text(result["publish_sql"], encoding="utf-8", newline="\n")
    (args.output_dir / "partition_plan.json").write_text(json.dumps(result["partition_plan"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
