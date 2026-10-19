#!/usr/bin/env python3
"""Render the fixed-input product SCD2 load and its preflight assertions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SAFE_VALUE = re.compile(r"^[A-Za-z0-9._-]+$")


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_contracts(semantic: dict[str, Any], physical: dict[str, Any]) -> None:
    """校验 SCD2 语义字段与物理字段，防止 Renderer 和 Contract 漂移。"""
    model = semantic.get("models", {}).get("dim_product_zip", {})
    if model.get("history_strategy") != "scd2":
        raise ValueError("dim_product_zip must use scd2")
    if model.get("sources") != ["ods_sku", "ods_spu", "ods_category", "ods_product_change_event"]:
        raise ValueError("dim_product_zip source contract drift")
    physical_columns = {column for column, _ in physical["models"]["dim_product_zip"]["columns"]}
    required = {
        "product_sk", "sku_id", "sale_price_cents", "category_id", "brand_code",
        "effective_from", "effective_to", "is_current", "attribute_hash", "batch_id", "load_time",
    }
    missing = sorted(required - physical_columns)
    if missing:
        raise ValueError(f"dim_product_zip missing physical columns {missing}")


def render_sql(semantic: dict[str, Any], physical: dict[str, Any], batch_id: str) -> str:
    """生成当前固定 Dataset 的商品价格 SCD2 全量重建 SQL。"""
    validate_contracts(semantic, physical)
    if not SAFE_VALUE.fullmatch(batch_id):
        raise ValueError(f"unsafe batch_id: {batch_id}")

    return f"""SET spark.sql.sources.partitionOverwriteMode=dynamic;
SET spark.sql.ansi.enabled=true;

-- 当前正式 Generator 只产生 SKU PRICE 事件；出现其他历史变化时必须先扩展算法。
SELECT assert_true(
  COUNT_IF(target_type <> 'SKU' OR change_type <> 'PRICE') = 0,
  'unsupported product change event for dim_product_zip'
)
FROM ecommerce_ods.ods_product_change_event;

INSERT OVERWRITE TABLE ecommerce_dim.dim_product_zip PARTITION (dt)
WITH latest_sku AS (
  SELECT * FROM (
    SELECT s.*, row_number() OVER (PARTITION BY sku_id ORDER BY dt DESC, extract_time DESC, batch_id DESC) AS rn
    FROM ecommerce_ods.ods_sku s
  ) x WHERE rn = 1
),
latest_spu AS (
  SELECT * FROM (
    SELECT s.*, row_number() OVER (PARTITION BY spu_id ORDER BY dt DESC, extract_time DESC, batch_id DESC) AS rn
    FROM ecommerce_ods.ods_spu s
  ) x WHERE rn = 1
),
latest_category AS (
  SELECT * FROM (
    SELECT c.*, row_number() OVER (PARTITION BY category_id ORDER BY dt DESC, extract_time DESC, batch_id DESC) AS rn
    FROM ecommerce_ods.ods_category c
  ) x WHERE rn = 1
),
price_events AS (
  SELECT * FROM (
    SELECT e.*, row_number() OVER (PARTITION BY change_id ORDER BY dt DESC, extract_time DESC, batch_id DESC) AS rn
    FROM ecommerce_ods.ods_product_change_event e
    WHERE target_type = 'SKU' AND change_type = 'PRICE'
  ) x WHERE rn = 1
),
first_price AS (
  SELECT sku_id, before_price FROM (
    SELECT
      target_id AS sku_id,
      CAST(get_json_object(before_data, '$.sale_price_cents') AS BIGINT) AS before_price,
      row_number() OVER (PARTITION BY target_id ORDER BY effective_at, change_id) AS rn
    FROM price_events
  ) x WHERE rn = 1
),
base_versions AS (
  SELECT
    s.sku_id,
    s.created_at AS effective_from,
    COALESCE(f.before_price, s.sale_price_cents) AS sale_price_cents
  FROM latest_sku s
  LEFT JOIN first_price f ON s.sku_id = f.sku_id
),
event_versions AS (
  SELECT
    target_id AS sku_id,
    effective_at AS effective_from,
    CAST(get_json_object(after_data, '$.sale_price_cents') AS BIGINT) AS sale_price_cents
  FROM price_events
),
version_points AS (
  SELECT * FROM base_versions
  UNION ALL
  SELECT * FROM event_versions
),
versioned AS (
  SELECT
    sku_id,
    effective_from,
    sale_price_cents,
    lead(effective_from) OVER (PARTITION BY sku_id ORDER BY effective_from) AS next_effective_from
  FROM version_points
),
enriched AS (
  SELECT
    sha2(concat_ws('|', CAST(v.sku_id AS STRING), date_format(v.effective_from, 'yyyy-MM-dd HH:mm:ss.SSS')), 256) AS product_sk,
    s.sku_id,
    s.sku_code,
    s.sku_name,
    p.spu_id,
    p.spu_code,
    p.spu_name,
    p.category_id,
    c.category_name,
    p.brand_code,
    p.brand_name,
    v.sale_price_cents,
    s.sku_status,
    p.spu_status,
    v.effective_from,
    COALESCE(v.next_effective_from, TIMESTAMP '9999-12-31 23:59:59.999') AS effective_to,
    v.next_effective_from IS NULL AS is_current,
    sha2(concat_ws('|', CAST(v.sale_price_cents AS STRING), CAST(p.category_id AS STRING), p.brand_code, p.brand_name, s.sku_status, p.spu_status), 256) AS attribute_hash,
    '{batch_id}' AS batch_id,
    current_timestamp() AS load_time,
    CAST(to_date(v.effective_from) AS STRING) AS dt
  FROM versioned v
  JOIN latest_sku s ON v.sku_id = s.sku_id
  JOIN latest_spu p ON s.spu_id = p.spu_id
  JOIN latest_category c ON p.category_id = c.category_id
)
SELECT * FROM enriched;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semantic-contract", type=Path, required=True)
    parser.add_argument("--physical-contract", type=Path, required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sql = render_sql(load_json(args.semantic_contract), load_json(args.physical_contract), args.batch_id)
    if args.output:
        args.output.write_text(sql, encoding="utf-8", newline="\n")
    else:
        print(sql, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
