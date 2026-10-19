-- M5 cohort 扩展：新增一张 DWS，现有 ADS 仅增加最终指标字段。
CREATE EXTERNAL TABLE IF NOT EXISTS ecommerce_dws.dws_trade_cohort_day (
  business_date DATE,
  cohort_created_order_count BIGINT,
  cohort_paid_order_count BIGINT,
  cohort_paid_amount_cents BIGINT,
  cohort_refund_amount_cents BIGINT,
  cumulative_net_paid_cents BIGINT,
  as_of_time TIMESTAMP,
  batch_id STRING,
  load_time TIMESTAMP
)
PARTITIONED BY (dt STRING)
STORED AS ORC
LOCATION '/warehouse/ecommerce/model/ecommerce_dws/dws_trade_cohort_day'
TBLPROPERTIES ('orc.compress'='SNAPPY');

ALTER TABLE ecommerce_ads.ads_daily_business_overview ADD COLUMNS (
  cumulative_net_paid_cents BIGINT,
  cohort_created_order_count BIGINT,
  cohort_paid_order_count BIGINT,
  cohort_payment_conversion_rate DECIMAL(18,6)
);
