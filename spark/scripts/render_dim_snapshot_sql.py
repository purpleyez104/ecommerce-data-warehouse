#!/usr/bin/env python3
"""Render the five snapshot/interval DIM loads that do not require SCD2 replay."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


SAFE_VALUE = re.compile(r"^[A-Za-z0-9._-]+$")
MODEL_SPECS = {
    "dim_user": ("ods_user", "user_id", ["user_id", "user_key", "user_name", "user_status", "registered_at"]),
    "dim_visitor": ("ods_visitor", "visitor_id", ["visitor_id", "visitor_key", "first_seen_at", "last_seen_at"]),
    "dim_identity_mapping": (
        "ods_identity_mapping",
        "mapping_id, identity_version",
        ["mapping_id", "visitor_id", "user_id", "session_id", "evidence_type", "evidence_id", "mapping_scope", "identity_version", "effective_from", "effective_to", "mapping_status"],
    ),
    "dim_category": ("ods_category", "category_id", ["category_id", "category_code", "category_name", "category_status"]),
    "dim_coupon_template": (
        "ods_coupon_template",
        "template_id",
        ["template_id", "template_code", "template_name", "face_value_cents", "min_spend_cents", "valid_from", "valid_to", "issue_limit", "template_status"],
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _literal(value: str, name: str) -> str:
    if not SAFE_VALUE.fullmatch(value):
        raise ValueError(f"unsafe {name}: {value}")
    return value


def validate_contracts(semantic: dict[str, Any], physical: dict[str, Any]) -> None:
    """检查五张非 SCD2 维度与物理字段保持一致。"""
    semantic_models = semantic.get("models", {})
    physical_models = physical.get("models", {})
    for model_name, (_, _, source_columns) in MODEL_SPECS.items():
        model = semantic_models.get(model_name)
        if not model or model.get("history_strategy") not in {"type_1", "source_effective_interval"}:
            raise ValueError(f"{model_name}: unsupported history strategy")
        physical_names = {column for column, _ in physical_models[model_name]["columns"]}
        required = set(source_columns) | {"snapshot_date", "batch_id", "load_time"}
        missing = sorted(required - physical_names)
        if missing:
            raise ValueError(f"{model_name}: missing physical columns {missing}")


def render_sql(semantic: dict[str, Any], physical: dict[str, Any], snapshot_date: str, batch_id: str) -> str:
    """生成五张维度的去重快照 SQL；同日重跑覆盖目标分区。"""
    validate_contracts(semantic, physical)
    try:
        date.fromisoformat(snapshot_date)
    except ValueError as exc:
        raise ValueError(f"invalid snapshot_date: {snapshot_date}") from exc
    _literal(batch_id, "batch_id")

    blocks = [
        "SET spark.sql.sources.partitionOverwriteMode=dynamic;",
        "SET spark.sql.ansi.enabled=true;",
        "",
    ]
    for model_name, (source_table, key_expression, source_columns) in MODEL_SPECS.items():
        select_columns = ",\n  ".join(source_columns)
        output_columns = ",\n  ".join(source_columns + [
            f"DATE '{snapshot_date}' AS snapshot_date",
            f"'{batch_id}' AS batch_id",
            "current_timestamp() AS load_time",
            f"'{snapshot_date}' AS dt",
        ])
        blocks.extend([
            f"INSERT OVERWRITE TABLE ecommerce_dim.{model_name} PARTITION (dt)",
            "WITH ranked AS (",
            "  SELECT",
            f"    {select_columns.replace(chr(10), chr(10) + '  ')},",
            # ODS 的抽取审计时间是 extract_time；DIM 自身的写入审计时间才是 load_time。
            f"    row_number() OVER (PARTITION BY {key_expression} ORDER BY dt DESC, extract_time DESC, batch_id DESC) AS rn",
            f"  FROM ecommerce_ods.{source_table}",
            f"  WHERE dt <= '{snapshot_date}'",
            ")",
            "SELECT",
            f"  {output_columns}",
            "FROM ranked",
            "WHERE rn = 1;",
            "",
        ])
    return "\n".join(blocks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semantic-contract", type=Path, required=True)
    parser.add_argument("--physical-contract", type=Path, required=True)
    parser.add_argument("--snapshot-date", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sql = render_sql(load_json(args.semantic_contract), load_json(args.physical_contract), args.snapshot_date, args.batch_id)
    if args.output:
        args.output.write_text(sql, encoding="utf-8", newline="\n")
    else:
        print(sql, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
