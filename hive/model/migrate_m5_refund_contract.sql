-- M5-02 可回滚切换：旧 EXTERNAL 表仅重命名，原 Location 与数据保持不变。
-- 执行前必须确认三个 HISTORY 表名和三个新 Location 均不存在。

ALTER TABLE ecommerce_dwd.dwd_refund
RENAME TO ecommerce_dwd.m5_20261018_history_dwd_refund;

CREATE EXTERNAL TABLE ecommerce_dwd.dwd_refund (
  refund_request_id BIGINT,
  refund_request_no STRING,
  order_id BIGINT,
  order_item_id BIGINT,
  requested_amount_cents BIGINT,
  refund_quantity INT,
  refund_status STRING,
  requested_at TIMESTAMP,
  completed_at TIMESTAMP,
  funding_refund_txn_id STRING,
  refund_txn_id BIGINT,
  successful_attempt_no INT,
  refund_amount_cents BIGINT,
  succeeded_at TIMESTAMP,
  batch_id STRING,
  load_time TIMESTAMP
)
PARTITIONED BY (dt STRING)
STORED AS ORC
LOCATION '/warehouse/ecommerce/model/m5_20261018/ecommerce_dwd/dwd_refund'
TBLPROPERTIES ('orc.compress'='SNAPPY');

ALTER TABLE ecommerce_dws.dws_trade_day
RENAME TO ecommerce_dws.m5_20261018_history_dws_trade_day;

CREATE EXTERNAL TABLE ecommerce_dws.dws_trade_day (
  business_date DATE,
  created_order_count BIGINT,
  created_user_count BIGINT,
  ordered_payable_cents BIGINT,
  effective_order_count BIGINT,
  effective_gmv_cents BIGINT,
  paid_order_count BIGINT,
  paid_user_count BIGINT,
  paid_amount_cents BIGINT,
  refund_request_count BIGINT,
  successful_refund_request_count BIGINT,
  refund_amount_cents BIGINT,
  refund_quantity BIGINT,
  cash_net_inflow_cents BIGINT,
  batch_id STRING,
  load_time TIMESTAMP
)
PARTITIONED BY (dt STRING)
STORED AS ORC
LOCATION '/warehouse/ecommerce/model/m5_20261018/ecommerce_dws/dws_trade_day'
TBLPROPERTIES ('orc.compress'='SNAPPY');

ALTER TABLE ecommerce_ads.ads_daily_business_overview
RENAME TO ecommerce_ads.m5_20261018_history_ads_daily_business_overview;

CREATE EXTERNAL TABLE ecommerce_ads.ads_daily_business_overview (
  business_date DATE,
  created_order_count BIGINT,
  effective_order_count BIGINT,
  effective_gmv_cents BIGINT,
  paid_order_count BIGINT,
  paid_amount_cents BIGINT,
  refund_request_count BIGINT,
  successful_refund_request_count BIGINT,
  refund_amount_cents BIGINT,
  refund_quantity BIGINT,
  cash_net_inflow_cents BIGINT,
  pv_count BIGINT,
  uv_count BIGINT,
  exposure_count BIGINT,
  click_count BIGINT,
  add_cart_count BIGINT,
  batch_id STRING,
  load_time TIMESTAMP
)
PARTITIONED BY (dt STRING)
STORED AS ORC
LOCATION '/warehouse/ecommerce/model/m5_20261018/ecommerce_ads/ads_daily_business_overview'
TBLPROPERTIES ('orc.compress'='SNAPPY');
