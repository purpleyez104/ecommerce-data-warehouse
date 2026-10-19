#!/usr/bin/env python3
"""Render the eight first-scope DWD transformations from verified ODS inputs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SAFE_VALUE = re.compile(r"^[A-Za-z0-9._-]+$")
DWD_MODELS = {
    "dwd_cart_item", "dwd_cart_merge", "dwd_order", "dwd_order_item",
    "dwd_payment", "dwd_refund", "dwd_coupon_event", "dwd_behavior_event",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_contracts(semantic: dict[str, Any], physical: dict[str, Any]) -> None:
    """确保 DWD 表集合、业务键与物理字段在生成前一致。"""
    semantic_models = semantic.get("models", {})
    physical_models = physical.get("models", {})
    actual = {name for name, model in semantic_models.items() if model.get("layer") == "dwd"}
    if actual != DWD_MODELS:
        raise ValueError(f"DWD model set drift: {sorted(actual ^ DWD_MODELS)}")
    for name in DWD_MODELS:
        columns = {column for column, _ in physical_models[name]["columns"]}
        missing = sorted(set(semantic_models[name]["business_key"]) - columns)
        if missing:
            raise ValueError(f"{name}: missing business key columns {missing}")
        if not {"batch_id", "load_time"}.issubset(columns):
            raise ValueError(f"{name}: missing audit columns")


def _insert(table: str, select_sql: str) -> str:
    return f"INSERT OVERWRITE TABLE ecommerce_dwd.{table} PARTITION (dt)\n{select_sql.strip()}\n;\n"


def render_sql(
    semantic: dict[str, Any],
    physical: dict[str, Any],
    batch_id: str,
    selected_models: set[str] | None = None,
) -> str:
    """生成全部或指定 DWD 的幂等重建 SQL，支持失败后的表级恢复。"""
    validate_contracts(semantic, physical)
    if not SAFE_VALUE.fullmatch(batch_id):
        raise ValueError(f"unsafe batch_id: {batch_id}")
    selected = DWD_MODELS if selected_models is None else selected_models
    unknown = selected - DWD_MODELS
    if unknown or not selected:
        raise ValueError(f"invalid selected DWD models: {sorted(unknown)}")
    audit = f"'{batch_id}' AS batch_id, current_timestamp() AS load_time"

    blocks = ["SET spark.sql.sources.partitionOverwriteMode=dynamic;", "SET spark.sql.ansi.enabled=true;", ""]
    blocks.append(_insert("dwd_cart_item", f"""
WITH item AS (
  SELECT * FROM (SELECT i.*, row_number() OVER (PARTITION BY cart_item_id ORDER BY dt DESC, extract_time DESC, batch_id DESC) rn FROM ecommerce_ods.ods_cart_item i) x WHERE rn=1
), cart AS (
  SELECT * FROM (SELECT c.*, row_number() OVER (PARTITION BY cart_id ORDER BY dt DESC, extract_time DESC, batch_id DESC) rn FROM ecommerce_ods.ods_cart c) x WHERE rn=1
)
SELECT i.cart_item_id, i.cart_id, c.user_id, c.visitor_id, i.sku_id, i.quantity, i.created_at, i.updated_at,
  {audit}, CAST(to_date(i.created_at) AS STRING) AS dt
FROM item i JOIN cart c ON i.cart_id=c.cart_id
"""))
    blocks.append(_insert("dwd_cart_merge", f"""
SELECT merge_id, operation_id, visitor_cart_id, user_cart_id, user_id, merge_detail, truncated_quantity, merged_at,
  {audit}, CAST(to_date(merged_at) AS STRING) AS dt
FROM (SELECT m.*, row_number() OVER (PARTITION BY merge_id ORDER BY dt DESC, extract_time DESC, batch_id DESC) rn FROM ecommerce_ods.ods_cart_merge_record m) x
WHERE rn=1
"""))
    blocks.append(_insert("dwd_order", f"""
SELECT order_id, order_no, user_id, visitor_id, coupon_id, order_status, gross_amount_cents, discount_amount_cents,
  payable_amount_cents, created_at, payment_deadline_at, paid_at, canceled_at, updated_at,
  {audit}, CAST(to_date(created_at) AS STRING) AS dt
FROM (SELECT o.*, row_number() OVER (PARTITION BY order_id ORDER BY dt DESC, extract_time DESC, batch_id DESC) rn FROM ecommerce_ods.ods_order o) x
WHERE rn=1
"""))
    blocks.append(_insert("dwd_order_item", f"""
WITH item AS (
  SELECT * FROM (SELECT i.*, row_number() OVER (PARTITION BY order_item_id ORDER BY dt DESC, extract_time DESC, batch_id DESC) rn FROM ecommerce_ods.ods_order_item i) x WHERE rn=1
)
SELECT i.order_item_id, i.order_id, p.product_sk, i.sku_id, i.spu_id, i.category_id, i.brand_code, i.sku_name,
  i.quantity, i.unit_price_cents, i.gross_amount_cents, i.allocated_discount_cents, i.payable_amount_cents,
  i.refund_reserved_cents, i.refunded_cents, i.refunded_quantity, i.created_at, i.updated_at,
  {audit}, CAST(to_date(i.created_at) AS STRING) AS dt
FROM item i
LEFT JOIN ecommerce_dim.dim_product_zip p
  ON i.sku_id=p.sku_id AND i.created_at>=p.effective_from AND i.created_at<p.effective_to
"""))
    blocks.append(_insert("dwd_payment", f"""
SELECT funding_txn_id, payment_attempt_id, order_id, attempt_no, amount_cents, payment_status, initiated_at, succeeded_at,
  {audit}, CAST(to_date(succeeded_at) AS STRING) AS dt
FROM (
  SELECT p.*, row_number() OVER (PARTITION BY funding_txn_id ORDER BY updated_at DESC, payment_attempt_id DESC, dt DESC, extract_time DESC) rn
  FROM ecommerce_ods.ods_payment_attempt p
  WHERE payment_status='SUCCESS' AND succeeded_at IS NOT NULL
) x WHERE rn=1
"""))
    blocks.append(_insert("dwd_refund", f"""
WITH successful_txn AS (
  SELECT * FROM (
    SELECT t.*, row_number() OVER (PARTITION BY refund_request_id ORDER BY attempt_no DESC, updated_at DESC, refund_txn_id DESC, dt DESC, extract_time DESC) rn
    FROM ecommerce_ods.ods_refund_transaction t
    WHERE refund_txn_status='SUCCESS' AND succeeded_at IS NOT NULL
  ) x WHERE rn=1
), request AS (
  SELECT * FROM (SELECT r.*, row_number() OVER (PARTITION BY refund_request_id ORDER BY updated_at DESC, dt DESC, extract_time DESC) rn FROM ecommerce_ods.ods_refund_request r) x WHERE rn=1
)
SELECT r.refund_request_id, r.refund_request_no, r.order_id, r.order_item_id, r.requested_amount_cents,
  r.refund_quantity, r.refund_status, r.requested_at, r.completed_at,
  t.funding_refund_txn_id, t.refund_txn_id, t.attempt_no AS successful_attempt_no,
  t.refund_amount_cents, t.succeeded_at,
  {audit}, CAST(to_date(r.requested_at) AS STRING) AS dt
FROM request r LEFT JOIN successful_txn t ON r.refund_request_id=t.refund_request_id
"""))
    blocks.append(_insert("dwd_coupon_event", f"""
WITH event AS (
  SELECT * FROM (SELECT e.*, row_number() OVER (PARTITION BY coupon_event_id ORDER BY dt DESC, extract_time DESC, batch_id DESC) rn FROM ecommerce_ods.ods_coupon_event e) x WHERE rn=1
), coupon AS (
  SELECT * FROM (SELECT c.*, row_number() OVER (PARTITION BY coupon_id ORDER BY dt DESC, extract_time DESC, batch_id DESC) rn FROM ecommerce_ods.ods_coupon c) x WHERE rn=1
)
SELECT e.coupon_event_id, e.event_key, e.coupon_id, c.template_id, e.order_id, e.event_type, e.from_status, e.to_status,
  e.occurred_at, e.recorded_at, {audit}, CAST(to_date(e.occurred_at) AS STRING) AS dt
FROM event e JOIN coupon c ON e.coupon_id=c.coupon_id
"""))
    blocks.append(_insert("dwd_behavior_event", f"""
WITH event AS (
  SELECT * FROM (SELECT e.*, row_number() OVER (PARTITION BY event_id ORDER BY dt DESC, load_time DESC, batch_id DESC) rn FROM ecommerce_ods.ods_behavior_event e) x WHERE rn=1
)
SELECT e.event_id, e.event_type, e.event_time, e.ingest_time, e.visitor_id,
  COALESCE(e.user_id, m.user_id) AS user_id, e.identity_version, e.session_id, p.product_sk, e.sku_id, e.page_id, e.quantity,
  e.source_file, {audit}, CAST(to_date(e.event_time) AS STRING) AS dt
FROM event e
LEFT JOIN ecommerce_dim.dim_identity_mapping m
  ON e.visitor_id=m.visitor_id
  AND e.identity_version=m.identity_version
  AND e.event_time>=m.effective_from
  AND (m.effective_to IS NULL OR e.event_time<m.effective_to)
  AND m.mapping_status='CONFIRMED'
LEFT JOIN ecommerce_dim.dim_product_zip p
  ON e.sku_id=p.sku_id AND e.event_time>=p.effective_from AND e.event_time<p.effective_to
"""))
    settings, inserts = blocks[:3], blocks[3:]
    selected_inserts = [
        block for block in inserts
        if any(f"ecommerce_dwd.{model} " in block for model in selected)
    ]
    return "\n".join(settings + selected_inserts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semantic-contract", type=Path, required=True)
    parser.add_argument("--physical-contract", type=Path, required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--model", action="append", choices=sorted(DWD_MODELS))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    selected_models = set(args.model) if args.model else None
    sql = render_sql(
        load_json(args.semantic_contract),
        load_json(args.physical_contract),
        args.batch_id,
        selected_models,
    )
    if args.output:
        args.output.write_text(sql, encoding="utf-8", newline="\n")
    else:
        print(sql, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
