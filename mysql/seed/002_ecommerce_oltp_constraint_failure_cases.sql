-- T5 isolated MySQL constraint-failure cases. Execute with a client that records each expected error and issues ROLLBACK.
-- These statements are not normal seed data and must never be run as part of 001.

START TRANSACTION;
INSERT INTO `user_account` (`user_account_pk`,`user_id`,`registered_at`,`is_deleted`,`deleted_at`,`create_time`,`update_time`) VALUES (99,'USR-001','2025-02-01 12:00:00.000',0,NULL,'2025-02-01 12:00:00.000','2025-02-01 12:00:00.000');
ROLLBACK;

START TRANSACTION;
INSERT INTO `traffic_channel` (`traffic_channel_pk`,`channel_code`,`channel_name`,`is_deleted`,`deleted_at`,`create_time`,`update_time`) VALUES (99,NULL,'Missing code',0,NULL,'2025-02-01 12:00:00.000','2025-02-01 12:00:00.000');
ROLLBACK;

START TRANSACTION;
INSERT INTO `sku` (`sku_pk`,`sku_id`,`sku_name`,`spu_pk`,`sale_price`,`currency`,`is_deleted`,`deleted_at`,`create_time`,`update_time`) VALUES (99,'SKU-BAD','Bad',1,1.00,'USD',0,NULL,'2025-02-01 12:00:00.000','2025-02-01 12:00:00.000');
ROLLBACK;

START TRANSACTION;
INSERT INTO `user_address` (`user_address_pk`,`address_id`,`user_pk`,`province_code`,`province_name`,`city_code`,`city_name`,`detail_address`,`is_deleted`,`deleted_at`,`create_time`,`update_time`) VALUES (99,'ADDR-BAD',999,'110000','Beijing','110100','Beijing','Missing user',0,NULL,'2025-02-01 12:00:00.000','2025-02-01 12:00:00.000');
ROLLBACK;

START TRANSACTION;
INSERT INTO `payment_attempt` (`payment_attempt_pk`,`payment_no`,`request_id`,`order_pk`,`payment_status`,`payment_amount`,`currency`,`attempted_at`,`paid_at`,`failed_at`,`callback_request_id`,`failure_reason`,`create_time`,`update_time`) VALUES (99,'PAY-BAD','REQ-PAY-BAD',1,'SUCCESS',45.00,'CNY','2025-02-01 12:00:00.000','2025-02-01 12:00:01.000',NULL,'CALLBACK-BAD',NULL,'2025-02-01 12:00:00.000','2025-02-01 12:00:01.000');
ROLLBACK;
