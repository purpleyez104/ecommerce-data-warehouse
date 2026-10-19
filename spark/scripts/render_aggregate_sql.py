#!/usr/bin/env python3
"""Render the M5 daily DWS and ADS metric models."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


SAFE_VALUE = re.compile(r"^[A-Za-z0-9._-]+$")
DATE_VALUE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def render_sql(batch_id: str, as_of_date: str) -> str:
    """生成日交易、日行为 DWS 和日经营概览 ADS 的幂等覆盖 SQL。"""
    if not SAFE_VALUE.fullmatch(batch_id):
        raise ValueError(f"unsafe batch_id: {batch_id}")
    if not DATE_VALUE.fullmatch(as_of_date):
        raise ValueError(f"unsafe as_of_date: {as_of_date}")
    audit = f"'{batch_id}' AS batch_id, current_timestamp() AS load_time"
    as_of_time = f"to_timestamp('{as_of_date} 23:59:59')"
    return f"""SET spark.sql.sources.partitionOverwriteMode=dynamic;
SET spark.sql.ansi.enabled=true;

INSERT OVERWRITE TABLE ecommerce_dws.dws_trade_day PARTITION (dt)
WITH order_day AS (
  SELECT to_date(created_at) AS business_date,
    count(*) AS created_order_count,
    count(DISTINCT user_id) AS created_user_count,
    sum(payable_amount_cents) AS ordered_payable_cents,
    sum(CASE WHEN order_status <> 'CANCELED' THEN 1 ELSE 0 END) AS effective_order_count,
    sum(CASE WHEN order_status <> 'CANCELED' THEN payable_amount_cents ELSE 0 END) AS effective_gmv_cents
  FROM ecommerce_dwd.dwd_order
  GROUP BY to_date(created_at)
), payment_day AS (
  SELECT to_date(p.succeeded_at) AS business_date,
    count(DISTINCT p.order_id) AS paid_order_count,
    count(DISTINCT o.user_id) AS paid_user_count,
    sum(p.amount_cents) AS paid_amount_cents
  FROM ecommerce_dwd.dwd_payment p
  JOIN ecommerce_dwd.dwd_order o ON p.order_id=o.order_id
  GROUP BY to_date(p.succeeded_at)
), refund_request_day AS (
  SELECT to_date(requested_at) AS business_date,
    count(*) AS refund_request_count
  FROM ecommerce_dwd.dwd_refund
  GROUP BY to_date(requested_at)
), refund_success_day AS (
  SELECT to_date(succeeded_at) AS business_date,
    count(*) AS successful_refund_request_count,
    sum(refund_amount_cents) AS refund_amount_cents,
    sum(coalesce(refund_quantity, 0)) AS refund_quantity
  FROM ecommerce_dwd.dwd_refund
  WHERE refund_status='SUCCESS' AND succeeded_at IS NOT NULL
  GROUP BY to_date(succeeded_at)
), date_spine AS (
  SELECT business_date FROM order_day
  UNION SELECT business_date FROM payment_day
  UNION SELECT business_date FROM refund_request_day
  UNION SELECT business_date FROM refund_success_day
)
SELECT d.business_date,
  coalesce(o.created_order_count, 0), coalesce(o.created_user_count, 0), coalesce(o.ordered_payable_cents, 0),
  coalesce(o.effective_order_count, 0), coalesce(o.effective_gmv_cents, 0),
  coalesce(p.paid_order_count, 0), coalesce(p.paid_user_count, 0), coalesce(p.paid_amount_cents, 0),
  coalesce(rr.refund_request_count, 0), coalesce(rs.successful_refund_request_count, 0),
  coalesce(rs.refund_amount_cents, 0), coalesce(rs.refund_quantity, 0),
  coalesce(p.paid_amount_cents, 0) - coalesce(rs.refund_amount_cents, 0) AS cash_net_inflow_cents,
  {audit}, CAST(d.business_date AS STRING) AS dt
FROM date_spine d
LEFT JOIN order_day o ON d.business_date=o.business_date
LEFT JOIN payment_day p ON d.business_date=p.business_date
LEFT JOIN refund_request_day rr ON d.business_date=rr.business_date
LEFT JOIN refund_success_day rs ON d.business_date=rs.business_date;

INSERT OVERWRITE TABLE ecommerce_dws.dws_behavior_day PARTITION (dt)
SELECT to_date(event_time) AS business_date,
  sum(CASE WHEN event_type='PAGE_VIEW' THEN 1 ELSE 0 END) AS pv_count,
  count(DISTINCT CASE WHEN user_id IS NOT NULL THEN concat('U:', CAST(user_id AS STRING)) ELSE concat('V:', CAST(visitor_id AS STRING)) END) AS uv_count,
  sum(CASE WHEN event_type='PRODUCT_EXPOSURE' THEN 1 ELSE 0 END) AS exposure_count,
  sum(CASE WHEN event_type='PRODUCT_CLICK' THEN 1 ELSE 0 END) AS click_count,
  sum(CASE WHEN event_type='ADD_CART' THEN 1 ELSE 0 END) AS add_cart_count,
  sum(CASE WHEN event_type='REMOVE_CART' THEN 1 ELSE 0 END) AS remove_cart_count,
  {audit}, CAST(to_date(event_time) AS STRING) AS dt
FROM ecommerce_dwd.dwd_behavior_event
GROUP BY to_date(event_time);

INSERT OVERWRITE TABLE ecommerce_dws.dws_product_day_sku PARTITION (dt)
WITH paid_order AS (
  SELECT order_id, min(succeeded_at) AS succeeded_at
  FROM ecommerce_dwd.dwd_payment
  GROUP BY order_id
), paid AS (
  SELECT to_date(p.succeeded_at) AS business_date, i.product_sk, i.sku_id, i.spu_id, i.category_id, i.brand_code,
    sum(i.quantity) AS paid_quantity, sum(i.payable_amount_cents) AS paid_amount_cents
  FROM paid_order p JOIN ecommerce_dwd.dwd_order_item i ON p.order_id=i.order_id
  GROUP BY to_date(p.succeeded_at), i.product_sk, i.sku_id, i.spu_id, i.category_id, i.brand_code
), refunded AS (
  SELECT to_date(r.succeeded_at) AS business_date, i.product_sk, i.sku_id, i.spu_id, i.category_id, i.brand_code,
    sum(coalesce(r.refund_quantity, 0)) AS refund_quantity
  FROM ecommerce_dwd.dwd_refund r
  JOIN ecommerce_dwd.dwd_order_item i ON r.order_item_id=i.order_item_id
  WHERE r.refund_status='SUCCESS' AND r.succeeded_at IS NOT NULL
  GROUP BY to_date(r.succeeded_at), i.product_sk, i.sku_id, i.spu_id, i.category_id, i.brand_code
), combined AS (
  SELECT coalesce(p.business_date, r.business_date) AS business_date,
    coalesce(p.product_sk, r.product_sk) AS product_sk, coalesce(p.sku_id, r.sku_id) AS sku_id,
    coalesce(p.spu_id, r.spu_id) AS spu_id, coalesce(p.category_id, r.category_id) AS category_id,
    coalesce(p.brand_code, r.brand_code) AS brand_code,
    coalesce(p.paid_quantity, 0) AS paid_quantity, coalesce(r.refund_quantity, 0) AS refund_quantity,
    coalesce(p.paid_amount_cents, 0) AS paid_amount_cents
  FROM paid p FULL OUTER JOIN refunded r
    ON p.business_date=r.business_date AND p.product_sk=r.product_sk
)
SELECT business_date, product_sk, sku_id, spu_id, category_id, brand_code,
  paid_quantity, refund_quantity, paid_amount_cents,
  {audit}, CAST(business_date AS STRING) AS dt
FROM combined;

INSERT OVERWRITE TABLE ecommerce_dws.dws_user_day PARTITION (dt)
WITH registration AS (
  SELECT to_date(registered_at) AS business_date, count(DISTINCT user_id) AS registered_user_count
  FROM ecommerce_dim.dim_user GROUP BY to_date(registered_at)
), first_purchase AS (
  SELECT business_date, count(*) AS first_purchase_user_count FROM (
    SELECT o.user_id, to_date(min(p.succeeded_at)) AS business_date
    FROM ecommerce_dwd.dwd_payment p JOIN ecommerce_dwd.dwd_order o ON p.order_id=o.order_id
    GROUP BY o.user_id
  ) x GROUP BY business_date
), active AS (
  SELECT to_date(event_time) AS business_date,
    count(DISTINCT CASE WHEN user_id IS NOT NULL THEN concat('U:', CAST(user_id AS STRING)) ELSE concat('V:', CAST(visitor_id AS STRING)) END) AS active_identity_count
  FROM ecommerce_dwd.dwd_behavior_event GROUP BY to_date(event_time)
), ordered AS (
  SELECT to_date(created_at) AS business_date, count(DISTINCT user_id) AS created_user_count
  FROM ecommerce_dwd.dwd_order GROUP BY to_date(created_at)
), paid AS (
  SELECT to_date(p.succeeded_at) AS business_date, count(DISTINCT o.user_id) AS paid_user_count
  FROM ecommerce_dwd.dwd_payment p JOIN ecommerce_dwd.dwd_order o ON p.order_id=o.order_id
  GROUP BY to_date(p.succeeded_at)
), date_spine AS (
  SELECT business_date FROM registration UNION SELECT business_date FROM first_purchase
  UNION SELECT business_date FROM active UNION SELECT business_date FROM ordered UNION SELECT business_date FROM paid
)
SELECT d.business_date, coalesce(r.registered_user_count, 0), coalesce(f.first_purchase_user_count, 0),
  coalesce(a.active_identity_count, 0), coalesce(o.created_user_count, 0), coalesce(p.paid_user_count, 0),
  {audit}, CAST(d.business_date AS STRING) AS dt
FROM date_spine d
LEFT JOIN registration r ON d.business_date=r.business_date
LEFT JOIN first_purchase f ON d.business_date=f.business_date
LEFT JOIN active a ON d.business_date=a.business_date
LEFT JOIN ordered o ON d.business_date=o.business_date
LEFT JOIN paid p ON d.business_date=p.business_date;

INSERT OVERWRITE TABLE ecommerce_dws.dws_coupon_day PARTITION (dt)
WITH event_day AS (
  SELECT to_date(occurred_at) AS business_date,
    sum(CASE WHEN event_type='ISSUE' THEN 1 ELSE 0 END) AS issued_coupon_count,
    sum(CASE WHEN event_type='LOCK' THEN 1 ELSE 0 END) AS locked_coupon_count,
    sum(CASE WHEN event_type='USE' THEN 1 ELSE 0 END) AS used_coupon_count,
    sum(CASE WHEN event_type='UNLOCK' THEN 1 ELSE 0 END) AS unlocked_coupon_count
  FROM ecommerce_dwd.dwd_coupon_event GROUP BY to_date(occurred_at)
), paid_coupon AS (
  SELECT to_date(p.succeeded_at) AS business_date, sum(o.discount_amount_cents) AS coupon_discount_cents,
    count(DISTINCT o.order_id) AS coupon_paid_order_count
  FROM (SELECT order_id, min(succeeded_at) AS succeeded_at FROM ecommerce_dwd.dwd_payment GROUP BY order_id) p
  JOIN ecommerce_dwd.dwd_order o ON p.order_id=o.order_id
  LEFT SEMI JOIN (SELECT DISTINCT order_id FROM ecommerce_dwd.dwd_coupon_event WHERE event_type='USE') u
    ON o.order_id=u.order_id
  GROUP BY to_date(p.succeeded_at)
), date_spine AS (
  SELECT business_date FROM event_day UNION SELECT business_date FROM paid_coupon
)
SELECT d.business_date, coalesce(e.issued_coupon_count, 0), coalesce(e.locked_coupon_count, 0),
  coalesce(e.used_coupon_count, 0), coalesce(e.unlocked_coupon_count, 0),
  coalesce(p.coupon_discount_cents, 0), coalesce(p.coupon_paid_order_count, 0),
  {audit}, CAST(d.business_date AS STRING) AS dt
FROM date_spine d
LEFT JOIN event_day e ON d.business_date=e.business_date
LEFT JOIN paid_coupon p ON d.business_date=p.business_date;

INSERT OVERWRITE TABLE ecommerce_dws.dws_trade_cohort_day PARTITION (dt)
WITH qualified_payment AS (
  SELECT o.order_id, o.created_at, p.amount_cents
  FROM ecommerce_dwd.dwd_order o
  JOIN ecommerce_dwd.dwd_payment p ON o.order_id=p.order_id
  WHERE p.succeeded_at<=o.payment_deadline_at AND p.succeeded_at<={as_of_time}
), cohort_payment AS (
  SELECT to_date(created_at) business_date, count(DISTINCT order_id) cohort_paid_order_count,
    sum(amount_cents) cohort_paid_amount_cents
  FROM qualified_payment GROUP BY to_date(created_at)
), cohort_refund AS (
  SELECT to_date(o.created_at) business_date, sum(r.refund_amount_cents) cohort_refund_amount_cents
  FROM ecommerce_dwd.dwd_refund r JOIN ecommerce_dwd.dwd_order o ON r.order_id=o.order_id
  WHERE r.refund_status='SUCCESS' AND r.succeeded_at<={as_of_time}
  GROUP BY to_date(o.created_at)
), cohort_order AS (
  SELECT to_date(created_at) business_date, count(*) cohort_created_order_count
  FROM ecommerce_dwd.dwd_order WHERE created_at<={as_of_time} GROUP BY to_date(created_at)
)
SELECT o.business_date, o.cohort_created_order_count,
  coalesce(p.cohort_paid_order_count,0), coalesce(p.cohort_paid_amount_cents,0),
  coalesce(r.cohort_refund_amount_cents,0),
  coalesce(p.cohort_paid_amount_cents,0)-coalesce(r.cohort_refund_amount_cents,0) cumulative_net_paid_cents,
  {as_of_time} AS as_of_time, {audit}, CAST(o.business_date AS STRING) AS dt
FROM cohort_order o
LEFT JOIN cohort_payment p ON o.business_date=p.business_date
LEFT JOIN cohort_refund r ON o.business_date=r.business_date;

INSERT OVERWRITE TABLE ecommerce_ads.ads_daily_business_overview PARTITION (dt)
WITH date_spine AS (
  SELECT business_date FROM ecommerce_dws.dws_trade_day
  UNION SELECT business_date FROM ecommerce_dws.dws_behavior_day
  UNION SELECT business_date FROM ecommerce_dws.dws_trade_cohort_day
)
SELECT d.business_date,
  coalesce(t.created_order_count, 0), coalesce(t.effective_order_count, 0), coalesce(t.effective_gmv_cents, 0),
  coalesce(t.paid_order_count, 0), coalesce(t.paid_amount_cents, 0),
  coalesce(t.refund_request_count, 0), coalesce(t.successful_refund_request_count, 0),
  coalesce(t.refund_amount_cents, 0), coalesce(t.refund_quantity, 0), coalesce(t.cash_net_inflow_cents, 0),
  coalesce(b.pv_count, 0), coalesce(b.uv_count, 0), coalesce(b.exposure_count, 0),
  coalesce(b.click_count, 0), coalesce(b.add_cart_count, 0),
  {audit},
  coalesce(c.cumulative_net_paid_cents, 0), coalesce(c.cohort_created_order_count, 0),
  coalesce(c.cohort_paid_order_count, 0),
  CASE WHEN coalesce(c.cohort_created_order_count,0)=0 THEN NULL
    ELSE CAST(c.cohort_paid_order_count AS DECIMAL(38,6))/c.cohort_created_order_count END,
  CAST(d.business_date AS STRING) AS dt
FROM date_spine d
LEFT JOIN ecommerce_dws.dws_trade_day t ON d.business_date=t.business_date
LEFT JOIN ecommerce_dws.dws_behavior_day b ON d.business_date=b.business_date
LEFT JOIN ecommerce_dws.dws_trade_cohort_day c ON d.business_date=c.business_date;
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sql = render_sql(args.batch_id, args.as_of_date)
    if args.output:
        args.output.write_text(sql, encoding="utf-8", newline="\n")
    else:
        print(sql, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
