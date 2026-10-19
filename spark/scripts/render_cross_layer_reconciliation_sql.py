#!/usr/bin/env python3
"""生成 M5 六域代表性指标的逐日跨层对账与阻断 SQL。"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import NamedTuple


SAFE_VALUE = re.compile(r"^[A-Za-z0-9._-]+$")


class Reconciliation(NamedTuple):
    """描述一个已发布指标在左右两个物理对象间的逐日对账。"""

    reconciliation_id: str
    metric_id: str
    left_object: str
    right_object: str
    left_sql: str
    right_sql: str


RECONCILIATIONS = (
    Reconciliation(
        "cross_layer.tr_07.paid_amount", "TR-07", "ecommerce_dwd.dwd_payment", "ecommerce_dws.dws_trade_day",
        "SELECT to_date(succeeded_at) business_date, sum(amount_cents) value FROM ecommerce_dwd.dwd_payment GROUP BY to_date(succeeded_at)",
        "SELECT business_date, paid_amount_cents value FROM ecommerce_dws.dws_trade_day",
    ),
    Reconciliation(
        "cross_layer.tf_05.add_cart_count", "TF-05", "ecommerce_dwd.dwd_behavior_event", "ecommerce_dws.dws_behavior_day",
        "SELECT to_date(event_time) business_date, count(*) value FROM ecommerce_dwd.dwd_behavior_event WHERE event_type='ADD_CART' GROUP BY to_date(event_time)",
        "SELECT business_date, add_cart_count value FROM ecommerce_dws.dws_behavior_day",
    ),
    Reconciliation(
        "cross_layer.pr_04.paid_amount", "PR-04", "ecommerce_dwd.dwd_order_item", "ecommerce_dws.dws_product_day_sku",
        "SELECT to_date(p.succeeded_at) business_date, sum(i.payable_amount_cents) value FROM (SELECT order_id, min(succeeded_at) succeeded_at FROM ecommerce_dwd.dwd_payment GROUP BY order_id) p JOIN ecommerce_dwd.dwd_order_item i ON p.order_id=i.order_id GROUP BY to_date(p.succeeded_at)",
        "SELECT business_date, sum(paid_amount_cents) value FROM ecommerce_dws.dws_product_day_sku GROUP BY business_date",
    ),
    Reconciliation(
        "cross_layer.us_05.paid_user_count", "US-05", "ecommerce_dwd.dwd_payment", "ecommerce_dws.dws_user_day",
        "SELECT to_date(p.succeeded_at) business_date, count(DISTINCT o.user_id) value FROM ecommerce_dwd.dwd_payment p JOIN ecommerce_dwd.dwd_order o ON p.order_id=o.order_id GROUP BY to_date(p.succeeded_at)",
        "SELECT business_date, paid_user_count value FROM ecommerce_dws.dws_user_day",
    ),
    Reconciliation(
        "cross_layer.rf_03.refund_amount", "RF-03", "ecommerce_dwd.dwd_refund", "ecommerce_dws.dws_trade_day",
        "SELECT to_date(succeeded_at) business_date, sum(refund_amount_cents) value FROM ecommerce_dwd.dwd_refund WHERE refund_status='SUCCESS' AND succeeded_at IS NOT NULL GROUP BY to_date(succeeded_at)",
        "SELECT business_date, refund_amount_cents value FROM ecommerce_dws.dws_trade_day",
    ),
    Reconciliation(
        "cross_layer.mk_01.issued_coupon_count", "MK-01", "ecommerce_dwd.dwd_coupon_event", "ecommerce_dws.dws_coupon_day",
        "SELECT to_date(occurred_at) business_date, count(*) value FROM ecommerce_dwd.dwd_coupon_event WHERE event_type='ISSUE' GROUP BY to_date(occurred_at)",
        "SELECT business_date, issued_coupon_count value FROM ecommerce_dws.dws_coupon_day",
    ),
    Reconciliation(
        "cross_layer.tr_02.effective_gmv", "TR-02", "ecommerce_dws.dws_trade_day", "ecommerce_ads.ads_daily_business_overview",
        "SELECT business_date, effective_gmv_cents value FROM ecommerce_dws.dws_trade_day",
        "SELECT business_date, effective_gmv_cents value FROM ecommerce_ads.ads_daily_business_overview",
    ),
    Reconciliation(
        "cross_layer.tf_01.pv_count", "TF-01", "ecommerce_dws.dws_behavior_day", "ecommerce_ads.ads_daily_business_overview",
        "SELECT business_date, pv_count value FROM ecommerce_dws.dws_behavior_day",
        "SELECT business_date, pv_count value FROM ecommerce_ads.ads_daily_business_overview",
    ),
    Reconciliation(
        "cross_layer.tr_13.cumulative_net_paid", "TR-13", "ecommerce_dws.dws_trade_cohort_day", "ecommerce_ads.ads_daily_business_overview",
        "SELECT business_date, cumulative_net_paid_cents value FROM ecommerce_dws.dws_trade_cohort_day",
        "SELECT business_date, cumulative_net_paid_cents value FROM ecommerce_ads.ads_daily_business_overview",
    ),
    Reconciliation(
        "cross_layer.tr_14.payment_conversion_rate", "TR-14", "ecommerce_dws.dws_trade_cohort_day", "ecommerce_ads.ads_daily_business_overview",
        "SELECT business_date, CAST(cohort_paid_order_count AS DECIMAL(38,6))/cohort_created_order_count value FROM ecommerce_dws.dws_trade_cohort_day",
        "SELECT business_date, cohort_payment_conversion_rate value FROM ecommerce_ads.ads_daily_business_overview",
    ),
)


def _literal(value: str, name: str) -> str:
    if not SAFE_VALUE.fullmatch(value):
        raise ValueError(f"unsafe {name}: {value}")
    return f"'{value}'"


def render_comparison(item: Reconciliation, batch_literal: str) -> str:
    """生成一个指标的 FULL OUTER JOIN，保留任一侧缺失日期。"""
    return f"""SELECT
  '{item.reconciliation_id}' AS reconciliation_id,
  '{item.metric_id}' AS metric_id,
  '1.0.0' AS definition_version,
  coalesce(l.business_date, r.business_date) AS business_date,
  'CROSS_LAYER' AS comparison_scope,
  '{item.left_object}' AS left_object,
  '{item.right_object}' AS right_object,
  CAST(coalesce(l.value, 0) AS DECIMAL(38,6)) AS left_value,
  CAST(coalesce(r.value, 0) AS DECIMAL(38,6)) AS right_value,
  CAST(coalesce(r.value, 0)-coalesce(l.value, 0) AS DECIMAL(38,6)) AS difference_value,
  CAST(CASE
    WHEN coalesce(l.value, 0)=0 AND coalesce(r.value, 0)=0 THEN 0
    WHEN coalesce(l.value, 0)=0 THEN NULL
    ELSE (coalesce(r.value, 0)-coalesce(l.value, 0))/abs(l.value)
  END AS DECIMAL(38,12)) AS difference_rate,
  CAST(0 AS DECIMAL(38,6)) AS threshold_value,
  CASE WHEN abs(coalesce(r.value, 0)-coalesce(l.value, 0))<=0 THEN 'PASS' ELSE 'FAIL' END AS status,
  {batch_literal} AS batch_id,
  current_timestamp() AS executed_at
FROM ({item.left_sql}) l
FULL OUTER JOIN ({item.right_sql}) r ON l.business_date=r.business_date"""


def render_sql(run_id: str, batch_id: str) -> str:
    """按 run_id 幂等写入八项逐日对账，并在落盘后阻断失败。"""
    run_literal = _literal(run_id, "run_id")
    batch_literal = _literal(batch_id, "batch_id")
    comparisons = "\nUNION ALL\n".join(
        render_comparison(item, batch_literal) for item in RECONCILIATIONS
    )
    return f"""SET spark.sql.ansi.enabled=true;
SET spark.sql.sources.partitionOverwriteMode=dynamic;

INSERT OVERWRITE TABLE ecommerce_quality.reconciliation_result PARTITION (run_id={run_literal})
{comparisons};

SELECT assert_true(
  (SELECT COUNT(DISTINCT reconciliation_id)=10 FROM ecommerce_quality.reconciliation_result WHERE run_id={run_literal}),
  'reconciliation_result.comparison_count'
);
SELECT assert_true(
  (SELECT COUNT(*)>0 FROM ecommerce_quality.reconciliation_result WHERE run_id={run_literal}),
  'reconciliation_result.not_empty'
);
SELECT assert_true(
  (SELECT COUNT(*)=0 FROM ecommerce_quality.reconciliation_result WHERE run_id={run_literal} AND status='FAIL'),
  'reconciliation_result.no_failures'
);
SELECT 'CROSS_LAYER_RECONCILIATION_PASS';
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sql = render_sql(args.run_id, args.batch_id)
    if args.output:
        args.output.write_text(sql, encoding="utf-8", newline="\n")
    else:
        print(sql, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
