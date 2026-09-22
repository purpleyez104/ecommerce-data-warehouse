-- M2 OLTP Acceptance Seed
-- Generated for ecommerce_oltp_m2_acceptance
-- Based on the confirmed M2 schema
-- Fixed deterministic seed data

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS=0;

START TRANSACTION;

INSERT INTO biz_user
(user_id,user_key,user_name,user_status,registered_at,created_at,updated_at)
VALUES
(10001,'user_10001','alice','ACTIVE','2026-01-01 10:00:00.000','2026-01-01 10:00:00.000','2026-01-01 10:00:00.000'),
(10002,'user_10002','bob','ACTIVE','2026-01-02 10:00:00.000','2026-01-02 10:00:00.000','2026-01-02 10:00:00.000');

INSERT INTO biz_visitor
(visitor_id,visitor_key,first_seen_at,last_seen_at,created_at,updated_at)
VALUES
(20001,'visitor_20001','2026-01-03 09:00:00.000','2026-01-03 10:00:00.000','2026-01-03 09:00:00.000','2026-01-03 10:00:00.000');

INSERT INTO biz_category
(category_id,category_code,category_name,category_status,created_at,updated_at)
VALUES
(30001,'CAT_DIGITAL','Digital','ACTIVE','2026-01-01 00:00:00.000','2026-01-01 00:00:00.000');

INSERT INTO biz_spu
(spu_id,spu_code,category_id,brand_code,brand_name,spu_name,spu_status,created_at,updated_at)
VALUES
(40001,'SPU_PHONE',30001,'BRAND_A','BrandA','Phone','ACTIVE','2026-01-01 00:00:00.000','2026-01-01 00:00:00.000');

INSERT INTO biz_sku
(sku_id,sku_code,spu_id,sku_name,sale_price_cents,sku_status,created_at,updated_at)
VALUES
(50001,'SKU_PHONE_001',40001,'Phone Black',100000,'ON_SALE','2026-01-01 00:00:00.000','2026-01-01 00:00:00.000'),
(50002,'SKU_PHONE_002',40001,'Phone White',120000,'ON_SALE','2026-01-01 00:00:00.000','2026-01-01 00:00:00.000');

INSERT INTO biz_cart
(cart_id,user_id,visitor_id,created_at,updated_at)
VALUES
(60001,10001,NULL,'2026-01-05 10:00:00.000','2026-01-05 10:00:00.000'),
(60002,NULL,20001,'2026-01-05 11:00:00.000','2026-01-05 11:00:00.000');

INSERT INTO biz_cart_item
(cart_item_id,cart_id,sku_id,quantity,created_at,updated_at)
VALUES
(61001,60001,50001,2,'2026-01-05 10:01:00.000','2026-01-05 10:01:00.000');

INSERT INTO biz_order
(order_id,order_no,user_id,visitor_id,coupon_id,order_status,gross_amount_cents,discount_amount_cents,payable_amount_cents,created_at,payment_deadline_at,paid_at,canceled_at,updated_at)
VALUES
(70001,'ORDER_70001',10001,NULL,NULL,'PAID',200000,10000,190000,'2026-01-06 10:00:00.000','2026-01-06 11:00:00.000','2026-01-06 10:30:00.000',NULL,'2026-01-06 10:30:00.000');

INSERT INTO biz_order_item
(order_item_id,order_id,sku_id,spu_id,category_id,brand_code,sku_name,quantity,unit_price_cents,gross_amount_cents,allocated_discount_cents,payable_amount_cents,created_at,updated_at)
VALUES
(71001,70001,50001,40001,30001,'BRAND_A','Phone Black',2,100000,200000,10000,190000,'2026-01-06 10:00:00.000','2026-01-06 10:00:00.000');

INSERT INTO biz_payment_attempt
(payment_attempt_id,order_id,attempt_no,funding_txn_id,amount_cents,payment_status,initiated_at,succeeded_at,created_at,updated_at)
VALUES
(80001,70001,1,'PAY_TXN_80001',190000,'SUCCESS','2026-01-06 10:10:00.000','2026-01-06 10:30:00.000','2026-01-06 10:10:00.000','2026-01-06 10:30:00.000');

INSERT INTO biz_payment_event
(payment_event_id,event_key,payment_attempt_id,callback_event_id,from_status,to_status,occurred_at,recorded_at)
VALUES
(81001,'PAY_EVENT_81001',80001,'CALLBACK_81001','INIT','SUCCESS','2026-01-06 10:30:00.000','2026-01-06 10:30:01.000');

INSERT INTO biz_order_status_event
(order_event_id,event_key,order_id,event_type,from_status,to_status,occurred_at,recorded_at)
VALUES
(82001,'ORDER_EVENT_82001',70001,'PAY','CREATED','PAID','2026-01-06 10:30:00.000','2026-01-06 10:30:01.000');

INSERT INTO biz_coupon_template
(template_id,template_code,template_name,face_value_cents,min_spend_cents,valid_from,valid_to,issue_limit,template_status,created_at,updated_at)
VALUES
(90001,'COUPON_10','10 discount',1000,50000,'2026-01-01 00:00:00.000','2026-12-31 23:59:59.000',100,'ACTIVE','2026-01-01 00:00:00.000','2026-01-01 00:00:00.000');

INSERT INTO biz_coupon
(coupon_id,coupon_code,template_id,user_id,coupon_status,locked_order_id,used_order_id,issued_at,expires_at,used_at,updated_at)
VALUES
(91001,'USER_COUPON_91001',90001,10001,'USED',NULL,70001,'2026-01-05 00:00:00.000','2026-12-31 23:59:59.000','2026-01-06 10:30:00.000','2026-01-06 10:30:00.000');

UPDATE biz_order SET coupon_id=91001 WHERE order_id=70001;

INSERT INTO biz_coupon_event
(coupon_event_id,event_key,coupon_id,order_id,event_type,from_status,to_status,occurred_at,recorded_at)
VALUES
(92001,'COUPON_EVENT_92001',91001,70001,'USE','LOCKED','USED','2026-01-06 10:30:00.000','2026-01-06 10:30:01.000');

INSERT INTO biz_refund_request
(refund_request_id,refund_request_no,order_id,order_item_id,requested_amount_cents,refund_quantity,refund_status,requested_at,completed_at,created_at,updated_at)
VALUES
(93001,'REFUND_93001',70001,71001,50000,1,'SUCCESS','2026-01-10 10:00:00.000','2026-01-10 12:00:00.000','2026-01-10 10:00:00.000','2026-01-10 12:00:00.000');

INSERT INTO biz_refund_transaction
(refund_txn_id,refund_request_id,attempt_no,funding_refund_txn_id,refund_amount_cents,refund_txn_status,initiated_at,succeeded_at,created_at,updated_at)
VALUES
(94001,93001,1,'REFUND_TXN_94001',50000,'SUCCESS','2026-01-10 10:30:00.000','2026-01-10 12:00:00.000','2026-01-10 10:30:00.000','2026-01-10 12:00:00.000');

INSERT INTO biz_refund_event
(refund_event_id,event_key,refund_request_id,refund_txn_id,event_type,from_status,to_status,occurred_at,recorded_at)
VALUES
(95001,'REFUND_EVENT_95001',93001,94001,'SUCCESS','PROCESSING','SUCCESS','2026-01-10 12:00:00.000','2026-01-10 12:00:01.000');

INSERT INTO biz_product_change_event
(change_id,event_key,target_type,target_id,change_type,before_data,after_data,effective_at,recorded_at)
VALUES
(96001,'PRODUCT_CHANGE_96001','SKU',50001,'PRICE',
JSON_OBJECT('price',100000),
JSON_OBJECT('price',110000),
'2026-01-11 00:00:00.000',
'2026-01-11 00:00:01.000');

COMMIT;

SET FOREIGN_KEY_CHECKS=1;
