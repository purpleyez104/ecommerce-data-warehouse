#!/usr/bin/env python3
"""Render isolated M7 Spark benchmark setup and equivalent query variants."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SAFE_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")
SAFE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EXPECTED_TABLES = {
    "benchmark_order": ("ecommerce_dwd.dwd_order", 100000, 9, 900000),
    "benchmark_order_item": ("ecommerce_dwd.dwd_order_item", 285000, 9, 2565000),
    "benchmark_behavior_event": ("ecommerce_dwd.dwd_behavior_event", 3000000, 3, 9000000),
    "benchmark_product": ("ecommerce_dim.dim_product_zip", 4000, 1, 4000),
}


def load_contract(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("benchmark contract root must be an object")
    return value


def validate_contract(contract: dict[str, Any]) -> None:
    """固定隔离边界和规模，防止 Benchmark 静默写入正式数仓。"""
    if contract.get("contract_version") != "m7-spark-benchmark-v1":
        raise ValueError("unsupported benchmark contract version")
    if contract.get("database") != "ecommerce_benchmark":
        raise ValueError("benchmark database must remain isolated")
    dataset_version = contract.get("dataset_version", "")
    if not SAFE_NAME.fullmatch(dataset_version):
        raise ValueError("unsafe dataset_version")
    root = contract.get("root", "")
    if root != f"/warehouse/ecommerce/benchmark/{dataset_version}":
        raise ValueError("benchmark root must match dataset_version")
    if contract.get("storage") != {
        "format": "ORC", "compression": "SNAPPY", "partition_column": "dt"
    }:
        raise ValueError("benchmark storage must be ORC + SNAPPY partitioned by dt")
    for name in ("history_start", "history_end", "target_partition"):
        if not SAFE_DATE.fullmatch(contract.get(name, "")):
            raise ValueError(f"invalid {name}")
    if not contract["history_start"] <= contract["target_partition"] <= contract["history_end"]:
        raise ValueError("target_partition is outside the benchmark range")
    if contract.get("id_stride") != 1_000_000_000:
        raise ValueError("benchmark id_stride drift")
    tables = contract.get("tables", {})
    if set(tables) != set(EXPECTED_TABLES):
        raise ValueError("benchmark table set drift")
    for name, expected in EXPECTED_TABLES.items():
        item = tables[name]
        actual = (
            item.get("source"), item.get("source_rows"),
            item.get("multiplier"), item.get("expected_rows"),
        )
        if actual != expected:
            raise ValueError(f"{name}: source or scale drift")
        if item["source_rows"] * item["multiplier"] != item["expected_rows"]:
            raise ValueError(f"{name}: expected row count mismatch")
    if contract.get("warmup_runs") != 1 or contract.get("measured_runs") != 3:
        raise ValueError("benchmark repetition contract drift")


def render_setup_sql(contract: dict[str, Any]) -> str:
    """生成隔离表及确定性放大 SQL；只读取已验收 DIM/DWD。"""
    validate_contract(contract)
    root = contract["root"]
    version = contract["dataset_version"]
    stride = contract["id_stride"]
    return f"""SET spark.sql.ansi.enabled=true;
SET spark.sql.sources.partitionOverwriteMode=dynamic;

CREATE DATABASE IF NOT EXISTS ecommerce_benchmark;

CREATE EXTERNAL TABLE IF NOT EXISTS ecommerce_benchmark.benchmark_order (
  benchmark_order_id BIGINT,
  source_order_id BIGINT,
  order_status STRING,
  payable_amount_cents BIGINT,
  created_at TIMESTAMP,
  replica_id INT,
  dataset_version STRING
) PARTITIONED BY (dt STRING)
STORED AS ORC LOCATION '{root}/benchmark_order'
TBLPROPERTIES ('orc.compress'='SNAPPY');

CREATE EXTERNAL TABLE IF NOT EXISTS ecommerce_benchmark.benchmark_order_item (
  benchmark_order_item_id BIGINT,
  benchmark_order_id BIGINT,
  sku_id BIGINT,
  category_id BIGINT,
  quantity INT,
  payable_amount_cents BIGINT,
  created_at TIMESTAMP,
  replica_id INT,
  dataset_version STRING
) PARTITIONED BY (dt STRING)
STORED AS ORC LOCATION '{root}/benchmark_order_item'
TBLPROPERTIES ('orc.compress'='SNAPPY');

CREATE EXTERNAL TABLE IF NOT EXISTS ecommerce_benchmark.benchmark_behavior_event (
  benchmark_event_id STRING,
  source_event_id STRING,
  event_type STRING,
  event_time TIMESTAMP,
  sku_id BIGINT,
  quantity INT,
  replica_id INT,
  dataset_version STRING
) PARTITIONED BY (dt STRING)
STORED AS ORC LOCATION '{root}/benchmark_behavior_event'
TBLPROPERTIES ('orc.compress'='SNAPPY');

CREATE EXTERNAL TABLE IF NOT EXISTS ecommerce_benchmark.benchmark_product (
  sku_id BIGINT,
  category_id BIGINT,
  brand_code STRING,
  sale_price_cents BIGINT,
  dataset_version STRING
) STORED AS ORC LOCATION '{root}/benchmark_product'
TBLPROPERTIES ('orc.compress'='SNAPPY');

INSERT OVERWRITE TABLE ecommerce_benchmark.benchmark_order PARTITION (dt)
SELECT CAST(o.order_id AS BIGINT) + CAST(r.replica_id AS BIGINT) * {stride},
       CAST(o.order_id AS BIGINT), o.order_status,
       o.payable_amount_cents, o.created_at, r.replica_id, '{version}', o.dt
FROM ecommerce_dwd.dwd_order o
CROSS JOIN (SELECT explode(sequence(0, 8)) AS replica_id) r;

INSERT OVERWRITE TABLE ecommerce_benchmark.benchmark_order_item PARTITION (dt)
SELECT CAST(i.order_item_id AS BIGINT) + CAST(r.replica_id AS BIGINT) * {stride},
       CAST(i.order_id AS BIGINT) + CAST(r.replica_id AS BIGINT) * {stride},
       i.sku_id, i.category_id,
       i.quantity, i.payable_amount_cents, i.created_at, r.replica_id,
       '{version}', i.dt
FROM ecommerce_dwd.dwd_order_item i
CROSS JOIN (SELECT explode(sequence(0, 8)) AS replica_id) r;

INSERT OVERWRITE TABLE ecommerce_benchmark.benchmark_behavior_event PARTITION (dt)
SELECT concat(e.event_id, '-', CAST(r.replica_id AS STRING)), e.event_id,
       e.event_type, e.event_time, e.sku_id, e.quantity, r.replica_id,
       '{version}', e.dt
FROM ecommerce_dwd.dwd_behavior_event e
CROSS JOIN (SELECT explode(sequence(0, 2)) AS replica_id) r;

INSERT OVERWRITE TABLE ecommerce_benchmark.benchmark_product
SELECT sku_id, category_id, brand_code, sale_price_cents, '{version}'
FROM ecommerce_dim.dim_product_zip
WHERE is_current;

SELECT assert_true((SELECT COUNT(*)=900000 FROM ecommerce_benchmark.benchmark_order), 'benchmark_order.row_count');
SELECT assert_true((SELECT COUNT(*)=2565000 FROM ecommerce_benchmark.benchmark_order_item), 'benchmark_order_item.row_count');
SELECT assert_true((SELECT COUNT(*)=9000000 FROM ecommerce_benchmark.benchmark_behavior_event), 'benchmark_behavior_event.row_count');
SELECT assert_true((SELECT COUNT(*)=4000 FROM ecommerce_benchmark.benchmark_product), 'benchmark_product.row_count');
SELECT assert_true((SELECT COUNT(*)=COUNT(DISTINCT benchmark_order_id) FROM ecommerce_benchmark.benchmark_order), 'benchmark_order.key_unique');
SELECT assert_true((SELECT COUNT(*)=COUNT(DISTINCT benchmark_order_item_id) FROM ecommerce_benchmark.benchmark_order_item), 'benchmark_order_item.key_unique');
SELECT assert_true((SELECT COUNT(*)=COUNT(DISTINCT benchmark_event_id) FROM ecommerce_benchmark.benchmark_behavior_event), 'benchmark_behavior_event.key_unique');
SELECT 'M7_BENCHMARK_SETUP_PASS';
"""


def render_query_sql(contract: dict[str, Any], experiment: str, variant: str) -> str:
    """生成结果等价的 Baseline/Optimized 查询，由 Runtime 比较 Plan 与指标。"""
    validate_contract(contract)
    allowed = contract.get("experiments", {})
    if experiment not in allowed or variant not in allowed[experiment]:
        raise ValueError("unsupported benchmark experiment or variant")
    target = contract["target_partition"]
    header = "SET spark.sql.adaptive.enabled=false;\nSET spark.sql.ansi.enabled=true;\n"

    def with_plan(query: str) -> str:
        """同一 Application 先保存 Physical Plan，再执行并输出单行结果指纹。"""
        return header + "EXPLAIN FORMATTED\n" + query + ";\n" + query + ";\n"

    if experiment == "partition_pruning":
        predicate = (
            f"CAST(event_time AS DATE)=DATE '{target}'"
            if variant == "baseline" else f"dt='{target}'"
        )
        query = f"""SELECT 'M7_RESULT' AS marker,
       COUNT(*) AS row_count,
       SUM(COALESCE(quantity, 0)) AS quantity_sum,
       SUM(CAST(pmod(xxhash64(benchmark_event_id), 1000000007) AS DECIMAL(38,0))) AS result_hash
FROM ecommerce_benchmark.benchmark_behavior_event
WHERE {predicate}"""
        return with_plan(query)
    if experiment == "join_strategy":
        strategy = "SET spark.sql.autoBroadcastJoinThreshold=-1;\n"
        hint = "/*+ MERGE(i, p) */" if variant == "sort_merge" else "/*+ BROADCAST(p) */"
        query = f"""WITH grouped AS (
  SELECT {hint} i.category_id,
         COUNT(*) AS item_count,
         SUM(i.payable_amount_cents) AS payable_amount_cents
  FROM ecommerce_benchmark.benchmark_order_item i
  JOIN ecommerce_benchmark.benchmark_product p ON i.sku_id=p.sku_id
  GROUP BY i.category_id
)
SELECT 'M7_RESULT' AS marker, COUNT(*) AS group_count,
       SUM(item_count) AS item_count,
       SUM(payable_amount_cents) AS payable_amount_cents,
       SUM(CAST(pmod(xxhash64(category_id, item_count, payable_amount_cents), 1000000007) AS DECIMAL(38,0))) AS result_hash
FROM grouped"""
        return strategy + with_plan(query)
    skew_key = (
        "CASE WHEN pmod(xxhash64(benchmark_event_id), 100)<40 "
        "THEN CAST(-1 AS BIGINT) ELSE COALESCE(sku_id, 0) END"
    )
    if variant == "single_stage":
        grouped = f"""SELECT {skew_key} AS skew_key,
       COUNT(*) AS event_count, SUM(COALESCE(quantity, 0)) AS quantity_sum
FROM ecommerce_benchmark.benchmark_behavior_event
GROUP BY {skew_key}"""
    else:
        grouped = f"""WITH salted AS (
  SELECT {skew_key} AS skew_key,
         pmod(xxhash64(benchmark_event_id), 16) AS salt,
         COUNT(*) AS event_count,
         SUM(COALESCE(quantity, 0)) AS quantity_sum
  FROM ecommerce_benchmark.benchmark_behavior_event
  GROUP BY {skew_key}, pmod(xxhash64(benchmark_event_id), 16)
)
SELECT skew_key, SUM(event_count) AS event_count,
       SUM(quantity_sum) AS quantity_sum
FROM salted
GROUP BY skew_key"""
    query = f"""WITH grouped AS (
{grouped}
)
SELECT 'M7_RESULT' AS marker, COUNT(*) AS group_count,
       SUM(event_count) AS event_count, SUM(quantity_sum) AS quantity_sum,
       SUM(CAST(pmod(xxhash64(skew_key, event_count, quantity_sum), 1000000007) AS DECIMAL(38,0))) AS result_hash
FROM grouped"""
    return with_plan(query)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--mode", choices=("setup", "query"), required=True)
    parser.add_argument("--experiment")
    parser.add_argument("--variant")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    contract = load_contract(args.contract)
    if args.mode == "setup":
        if args.experiment or args.variant:
            parser.error("setup mode does not accept experiment or variant")
        sql = render_setup_sql(contract)
    else:
        if not args.experiment or not args.variant:
            parser.error("query mode requires experiment and variant")
        sql = render_query_sql(contract, args.experiment, args.variant)
    if args.output:
        args.output.write_text(sql, encoding="utf-8", newline="\n")
    else:
        print(sql, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
