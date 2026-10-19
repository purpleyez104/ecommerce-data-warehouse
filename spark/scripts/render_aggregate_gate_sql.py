#!/usr/bin/env python3
"""Render the M4 DWS/ADS reconciliation and quality gate."""

from __future__ import annotations

import argparse
from pathlib import Path


def assertion(rule_id: str, condition: str) -> str:
    return f"SELECT assert_true(({condition}), '{rule_id}');"


def render_sql() -> str:
    """生成键、分区、非负值、逐层对账和 ADS 一致性断言。"""
    lines = ["SET spark.sql.ansi.enabled=true;", ""]
    tables = {
        "ecommerce_dws.dws_trade_day": ["business_date"],
        "ecommerce_dws.dws_behavior_day": ["business_date"],
        "ecommerce_dws.dws_product_day_sku": ["business_date", "product_sk"],
        "ecommerce_dws.dws_user_day": ["business_date"],
        "ecommerce_dws.dws_coupon_day": ["business_date"],
        "ecommerce_dws.dws_trade_cohort_day": ["business_date"],
        "ecommerce_ads.ads_daily_business_overview": ["business_date"],
    }
    for table, keys in tables.items():
        name = table.split(".")[-1]
        null_condition = " OR ".join(f"{key} IS NULL" for key in keys)
        key_expression = ", ".join(keys)
        lines.extend([
            assertion(f"{name}.business_key_not_null", f"SELECT COUNT(*)=0 FROM {table} WHERE {null_condition}"),
            assertion(f"{name}.business_key_unique", f"SELECT COUNT(*)=0 FROM (SELECT {key_expression} FROM {table} GROUP BY {key_expression} HAVING COUNT(*)>1) d"),
            assertion(f"{name}.audit_and_partition_valid", f"SELECT COUNT(*)=0 FROM {table} WHERE batch_id IS NULL OR load_time IS NULL OR dt<>CAST(business_date AS STRING)"),
            "",
        ])
    lines.extend([
        assertion("dws_trade_day.non_negative_measures", "SELECT COUNT(*)=0 FROM ecommerce_dws.dws_trade_day WHERE created_order_count<0 OR effective_order_count<0 OR paid_order_count<0 OR refund_request_count<0 OR successful_refund_request_count<0 OR refund_quantity<0 OR effective_gmv_cents<0 OR paid_amount_cents<0 OR refund_amount_cents<0"),
        assertion("dws_trade_day.cash_net_formula", "SELECT COUNT(*)=0 FROM ecommerce_dws.dws_trade_day WHERE cash_net_inflow_cents<>paid_amount_cents-refund_amount_cents"),
        assertion("dws_trade_day.order_reconciliation", "SELECT (SELECT sum(created_order_count) FROM ecommerce_dws.dws_trade_day)=(SELECT count(*) FROM ecommerce_dwd.dwd_order)"),
        assertion("dws_trade_day.payment_reconciliation", "SELECT (SELECT sum(paid_amount_cents) FROM ecommerce_dws.dws_trade_day)=(SELECT sum(amount_cents) FROM ecommerce_dwd.dwd_payment)"),
        assertion("dws_trade_day.refund_reconciliation", "SELECT (SELECT sum(refund_request_count) FROM ecommerce_dws.dws_trade_day)=(SELECT count(*) FROM ecommerce_dwd.dwd_refund) AND (SELECT sum(successful_refund_request_count) FROM ecommerce_dws.dws_trade_day)=(SELECT count(*) FROM ecommerce_dwd.dwd_refund WHERE refund_status='SUCCESS') AND (SELECT sum(refund_amount_cents) FROM ecommerce_dws.dws_trade_day)=(SELECT sum(refund_amount_cents) FROM ecommerce_dwd.dwd_refund WHERE refund_status='SUCCESS') AND (SELECT sum(refund_quantity) FROM ecommerce_dws.dws_trade_day)=(SELECT sum(coalesce(refund_quantity,0)) FROM ecommerce_dwd.dwd_refund WHERE refund_status='SUCCESS')"),
        assertion("dws_behavior_day.event_reconciliation", "SELECT (SELECT sum(pv_count+exposure_count+click_count+add_cart_count+remove_cart_count) FROM ecommerce_dws.dws_behavior_day)=(SELECT count(*) FROM ecommerce_dwd.dwd_behavior_event)"),
        assertion("dws_product_day_sku.non_negative_measures", "SELECT COUNT(*)=0 FROM ecommerce_dws.dws_product_day_sku WHERE paid_quantity<0 OR refund_quantity<0 OR paid_amount_cents<0"),
        assertion("dws_product_day_sku.payment_reconciliation", "SELECT (SELECT sum(paid_amount_cents) FROM ecommerce_dws.dws_product_day_sku)=(SELECT sum(i.payable_amount_cents) FROM (SELECT DISTINCT order_id FROM ecommerce_dwd.dwd_payment) p JOIN ecommerce_dwd.dwd_order_item i ON p.order_id=i.order_id)"),
        assertion("dws_product_day_sku.refund_reconciliation", "SELECT (SELECT sum(refund_quantity) FROM ecommerce_dws.dws_product_day_sku)=(SELECT sum(coalesce(refund_quantity,0)) FROM ecommerce_dwd.dwd_refund WHERE refund_status='SUCCESS')"),
        assertion("dws_user_day.non_negative_measures", "SELECT COUNT(*)=0 FROM ecommerce_dws.dws_user_day WHERE registered_user_count<0 OR first_purchase_user_count<0 OR active_identity_count<0 OR created_user_count<0 OR paid_user_count<0"),
        assertion("dws_user_day.trade_reconciliation", "SELECT (SELECT sum(created_user_count) FROM ecommerce_dws.dws_user_day)=(SELECT sum(created_user_count) FROM ecommerce_dws.dws_trade_day) AND (SELECT sum(paid_user_count) FROM ecommerce_dws.dws_user_day)=(SELECT sum(paid_user_count) FROM ecommerce_dws.dws_trade_day)"),
        assertion("dws_coupon_day.non_negative_measures", "SELECT COUNT(*)=0 FROM ecommerce_dws.dws_coupon_day WHERE issued_coupon_count<0 OR locked_coupon_count<0 OR used_coupon_count<0 OR unlocked_coupon_count<0 OR coupon_discount_cents<0 OR coupon_paid_order_count<0"),
        assertion("dws_coupon_day.event_reconciliation", "SELECT (SELECT sum(issued_coupon_count+locked_coupon_count+used_coupon_count+unlocked_coupon_count) FROM ecommerce_dws.dws_coupon_day)=(SELECT count(*) FROM ecommerce_dwd.dwd_coupon_event WHERE event_type IN ('ISSUE','LOCK','USE','UNLOCK'))"),
        assertion("dws_trade_cohort_day.non_negative_measures", "SELECT COUNT(*)=0 FROM ecommerce_dws.dws_trade_cohort_day WHERE cohort_created_order_count<0 OR cohort_paid_order_count<0 OR cohort_paid_amount_cents<0 OR cohort_refund_amount_cents<0"),
        assertion("dws_trade_cohort_day.net_formula", "SELECT COUNT(*)=0 FROM ecommerce_dws.dws_trade_cohort_day WHERE cumulative_net_paid_cents<>cohort_paid_amount_cents-cohort_refund_amount_cents"),
        assertion("dws_trade_cohort_day.order_reconciliation", "SELECT (SELECT sum(cohort_created_order_count) FROM ecommerce_dws.dws_trade_cohort_day)=(SELECT count(*) FROM ecommerce_dwd.dwd_order)"),
        assertion("dws_trade_cohort_day.payment_refund_reconciliation", "SELECT (SELECT sum(cohort_paid_amount_cents) FROM ecommerce_dws.dws_trade_cohort_day)=(SELECT sum(p.amount_cents) FROM ecommerce_dwd.dwd_payment p JOIN ecommerce_dwd.dwd_order o ON p.order_id=o.order_id WHERE p.succeeded_at<=o.payment_deadline_at AND p.succeeded_at<=(SELECT max(as_of_time) FROM ecommerce_dws.dws_trade_cohort_day)) AND (SELECT sum(cohort_refund_amount_cents) FROM ecommerce_dws.dws_trade_cohort_day)=(SELECT sum(refund_amount_cents) FROM ecommerce_dwd.dwd_refund WHERE refund_status='SUCCESS' AND succeeded_at<=(SELECT max(as_of_time) FROM ecommerce_dws.dws_trade_cohort_day))"),
        assertion("ads_daily_business_overview.dws_date_coverage", "SELECT COUNT(*)=0 FROM (SELECT business_date FROM ecommerce_dws.dws_trade_day UNION SELECT business_date FROM ecommerce_dws.dws_behavior_day) d FULL OUTER JOIN ecommerce_ads.ads_daily_business_overview a ON d.business_date=a.business_date WHERE d.business_date IS NULL OR a.business_date IS NULL"),
        assertion("ads_daily_business_overview.measure_reconciliation", "SELECT COUNT(*)=0 FROM ecommerce_ads.ads_daily_business_overview a LEFT JOIN ecommerce_dws.dws_trade_day t ON a.business_date=t.business_date LEFT JOIN ecommerce_dws.dws_behavior_day b ON a.business_date=b.business_date LEFT JOIN ecommerce_dws.dws_trade_cohort_day c ON a.business_date=c.business_date WHERE a.effective_gmv_cents<>coalesce(t.effective_gmv_cents,0) OR a.cash_net_inflow_cents<>coalesce(t.cash_net_inflow_cents,0) OR a.refund_request_count<>coalesce(t.refund_request_count,0) OR a.successful_refund_request_count<>coalesce(t.successful_refund_request_count,0) OR a.refund_quantity<>coalesce(t.refund_quantity,0) OR a.pv_count<>coalesce(b.pv_count,0) OR a.uv_count<>coalesce(b.uv_count,0) OR a.cumulative_net_paid_cents<>coalesce(c.cumulative_net_paid_cents,0) OR a.cohort_created_order_count<>coalesce(c.cohort_created_order_count,0) OR a.cohort_paid_order_count<>coalesce(c.cohort_paid_order_count,0)"),
        assertion("AGGREGATE_GATE_PASS", "SELECT true"),
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sql = render_sql()
    if args.output:
        args.output.write_text(sql, encoding="utf-8", newline="\n")
    else:
        print(sql, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
