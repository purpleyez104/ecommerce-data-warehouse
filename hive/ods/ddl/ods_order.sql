CREATE DATABASE IF NOT EXISTS ecommerce_ods;


CREATE TABLE IF NOT EXISTS ecommerce_ods.ods_order
(
    order_id BIGINT,
    order_no STRING,

    user_id BIGINT,
    visitor_id BIGINT,

    coupon_id BIGINT,

    order_status STRING,

    gross_amount_cents BIGINT,
    discount_amount_cents BIGINT,
    payable_amount_cents BIGINT,


    created_at STRING,
    payment_deadline_at STRING,

    paid_at STRING,
    canceled_at STRING,

    updated_at STRING,

    business_date STRING,
    extract_time STRING,
    batch_id STRING,
    source_table STRING
)

PARTITIONED BY
(
    dt STRING
)

STORED AS ORC;
