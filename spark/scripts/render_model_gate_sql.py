#!/usr/bin/env python3
"""Render independent DIM/DWD Model Gate assertions from the frozen contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert(rule_id: str, condition: str) -> str:
    return f"SELECT assert_true(({condition}), '{rule_id}');"


def validate_contracts(semantic: dict[str, Any], physical: dict[str, Any]) -> None:
    models = semantic.get("models", {})
    physical_models = physical.get("models", {})
    if set(models) != set(physical_models):
        raise ValueError("semantic and physical model sets differ")
    for name, model in models.items():
        columns = {column for column, _ in physical_models[name]["columns"]}
        missing = sorted(set(model["business_key"]) - columns)
        if missing:
            raise ValueError(f"{name}: missing gate key columns {missing}")


def render_sql(semantic: dict[str, Any], physical: dict[str, Any]) -> str:
    """生成公共、SCD2、引用、金额和 Behavior Gate。"""
    validate_contracts(semantic, physical)
    models = semantic["models"]
    lines = ["SET spark.sql.ansi.enabled=true;", ""]

    for name in sorted(models):
        database = physical["models"][name]["database"]
        table = f"{database}.{name}"
        keys = models[name]["business_key"]
        null_condition = " AND ".join(f"{key} IS NOT NULL" for key in keys)
        key_list = ", ".join(keys)
        # SCD2 的自然业务键允许出现多个历史版本；版本行应由业务键、
        # 生效时间和代理键共同保证唯一，不能沿用普通模型的业务键唯一断言。
        if models[name].get("history_strategy") == "scd2":
            unique_rule_id = f"{name}.business_key_interval_unique"
            unique_condition = (
                f"SELECT (SELECT COUNT(*)=0 FROM (SELECT {key_list}, effective_from FROM {table} "
                f"GROUP BY {key_list}, effective_from HAVING COUNT(*)>1) d) "
                f"AND (SELECT COUNT(*)=COUNT(DISTINCT product_sk) FROM {table})"
            )
        else:
            unique_rule_id = f"{name}.business_key_unique"
            unique_condition = f"SELECT COUNT(*)=0 FROM (SELECT {key_list} FROM {table} GROUP BY {key_list} HAVING COUNT(*)>1) d"
        lines.extend([
            _assert(f"{name}.business_key_not_null", f"SELECT COUNT(*)=0 FROM {table} WHERE NOT ({null_condition})"),
            _assert(unique_rule_id, unique_condition),
            _assert(f"{name}.audit_columns_not_null", f"SELECT COUNT(*)=0 FROM {table} WHERE batch_id IS NULL OR load_time IS NULL OR dt IS NULL"),
            "",
        ])

    lines.extend([
        _assert("dim_product_zip.one_current_row_per_business_key", "SELECT COUNT(*)=0 FROM (SELECT sku_id FROM ecommerce_dim.dim_product_zip WHERE is_current GROUP BY sku_id HAVING COUNT(*)<>1) d"),
        _assert("dim_product_zip.effective_interval_valid", "SELECT COUNT(*)=0 FROM ecommerce_dim.dim_product_zip WHERE effective_from>=effective_to"),
        _assert("dim_product_zip.effective_interval_non_overlapping", "SELECT COUNT(*)=0 FROM ecommerce_dim.dim_product_zip a JOIN ecommerce_dim.dim_product_zip b ON a.sku_id=b.sku_id AND a.product_sk<b.product_sk AND a.effective_from<b.effective_to AND b.effective_from<a.effective_to"),
        "",
        _assert("dwd_cart_item.cart_reference_complete", "SELECT COUNT(*)=0 FROM ecommerce_dwd.dwd_cart_item WHERE cart_id IS NULL"),
        _assert("dwd_order_item.order_reference_complete", "SELECT COUNT(*)=0 FROM ecommerce_dwd.dwd_order_item i LEFT ANTI JOIN ecommerce_dwd.dwd_order o ON i.order_id=o.order_id"),
        _assert("dwd_order_item.product_time_match", "SELECT COUNT(*)=0 FROM ecommerce_dwd.dwd_order_item WHERE product_sk IS NULL"),
        _assert("dwd_payment.order_reference_complete", "SELECT COUNT(*)=0 FROM ecommerce_dwd.dwd_payment p LEFT ANTI JOIN ecommerce_dwd.dwd_order o ON p.order_id=o.order_id"),
        _assert("dwd_refund.order_item_reference_complete", "SELECT COUNT(*)=0 FROM ecommerce_dwd.dwd_refund r LEFT ANTI JOIN ecommerce_dwd.dwd_order_item i ON r.order_item_id=i.order_item_id"),
        _assert("dwd_behavior_event.product_time_match", "SELECT COUNT(*)=0 FROM ecommerce_dwd.dwd_behavior_event WHERE sku_id IS NOT NULL AND product_sk IS NULL"),
        _assert("dwd_behavior_event.identity_time_match", "SELECT COUNT(*)=0 FROM ecommerce_dwd.dwd_behavior_event WHERE identity_version IS NOT NULL AND user_id IS NULL"),
        "",
        _assert("dwd_order_item.row_amount_conservation", "SELECT COUNT(*)=0 FROM ecommerce_dwd.dwd_order_item WHERE gross_amount_cents<>quantity*unit_price_cents OR payable_amount_cents<>gross_amount_cents-allocated_discount_cents"),
        _assert("dwd_order.amount_conservation", "SELECT COUNT(*)=0 FROM ecommerce_dwd.dwd_order o LEFT JOIN (SELECT order_id, SUM(gross_amount_cents) gross, SUM(allocated_discount_cents) discount, SUM(payable_amount_cents) payable FROM ecommerce_dwd.dwd_order_item GROUP BY order_id) i ON o.order_id=i.order_id WHERE o.gross_amount_cents<>i.gross OR o.discount_amount_cents<>i.discount OR o.payable_amount_cents<>i.payable"),
        _assert("dwd_payment.amount_matches_order", "SELECT COUNT(*)=0 FROM ecommerce_dwd.dwd_payment p JOIN ecommerce_dwd.dwd_order o ON p.order_id=o.order_id WHERE p.amount_cents<>o.payable_amount_cents"),
        _assert("dwd_refund.state_and_funding_consistent", "SELECT COUNT(*)=0 FROM ecommerce_dwd.dwd_refund WHERE (refund_status='SUCCESS' AND (funding_refund_txn_id IS NULL OR refund_txn_id IS NULL OR refund_amount_cents IS NULL OR succeeded_at IS NULL)) OR (refund_status<>'SUCCESS' AND (funding_refund_txn_id IS NOT NULL OR refund_txn_id IS NOT NULL OR refund_amount_cents IS NOT NULL OR succeeded_at IS NOT NULL))"),
        _assert("dwd_refund.not_over_order_item", "SELECT COUNT(*)=0 FROM (SELECT order_item_id, SUM(refund_amount_cents) refunded FROM ecommerce_dwd.dwd_refund WHERE refund_status='SUCCESS' GROUP BY order_item_id) r JOIN ecommerce_dwd.dwd_order_item i ON r.order_item_id=i.order_item_id WHERE r.refunded>i.payable_amount_cents"),
        "",
        _assert("dwd_behavior_event.event_type_allowed", "SELECT COUNT(*)=0 FROM ecommerce_dwd.dwd_behavior_event WHERE event_type NOT IN ('PAGE_VIEW','PRODUCT_EXPOSURE','PRODUCT_CLICK','ADD_CART','REMOVE_CART')"),
        _assert("dwd_behavior_event.partition_matches_business_time", "SELECT COUNT(*)=0 FROM ecommerce_dwd.dwd_behavior_event WHERE dt<>CAST(to_date(event_time) AS STRING)"),
        _assert("MODEL_GATE_PASS", "SELECT true"),
        "",
    ])
    return "\n".join(lines)


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
