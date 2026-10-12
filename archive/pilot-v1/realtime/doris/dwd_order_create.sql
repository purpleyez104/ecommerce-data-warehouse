-- R1：订单当前状态 DWD。
-- 本文件记录实时链路 Chat 中实际执行成功的建表语句，不是新的业务模型。
-- 现有 ecommerce_serving.dwd_order 已包含验收数据，不得重复执行或通过 DROP/重建覆盖。

CREATE TABLE ecommerce_serving.dwd_order (
  order_id BIGINT NOT NULL,
  order_no VARCHAR(64) NOT NULL,

  user_id BIGINT NULL,
  visitor_id BIGINT NULL,
  coupon_id BIGINT NULL,

  order_status VARCHAR(32) NOT NULL,

  gross_amount_cents BIGINT NOT NULL,
  discount_amount_cents BIGINT NOT NULL,
  payable_amount_cents BIGINT NOT NULL,

  created_at DATETIME(3) NOT NULL,
  payment_deadline_at DATETIME(3) NOT NULL,
  paid_at DATETIME(3) NULL,
  canceled_at DATETIME(3) NULL,
  updated_at DATETIME(3) NOT NULL,

  kafka_partition INT NOT NULL,
  kafka_offset BIGINT NOT NULL
)
ENGINE = OLAP
UNIQUE KEY(order_id)
DISTRIBUTED BY HASH(order_id) BUCKETS 2
PROPERTIES (
  "replication_num" = "2",
  "enable_unique_key_merge_on_write" = "true",
  "function_column.sequence_col" = "kafka_offset"
);
