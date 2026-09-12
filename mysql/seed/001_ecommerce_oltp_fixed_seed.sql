-- Fixed M2.3 acceptance seed for ecommerce_oltp.
-- Status: implemented static input only; execute only in the isolated T7 test database.
-- Direct rerun contract: the runner must compare expected results first; matching data is not rewritten and drift fails non-zero.
-- Insert order follows DR-020 and must not disable FOREIGN_KEY_CHECKS.

START TRANSACTION;

INSERT INTO `user_account` (`user_account_pk`,`user_id`,`registered_at`,`is_deleted`,`deleted_at`,`create_time`,`update_time`) VALUES
  (1,'USR-001','2025-01-29 08:00:00.000',0,NULL,'2025-01-29 08:00:00.000','2025-01-29 08:00:00.000'),
  (2,'USR-002','2025-01-30 08:00:00.000',0,NULL,'2025-01-30 08:00:00.000','2025-01-30 08:00:00.000'),
  (3,'USR-003','2025-01-31 08:00:00.000',0,NULL,'2025-01-31 08:00:00.000','2025-01-31 08:00:00.000'),
  (4,'USR-004','2025-02-01 08:00:00.000',0,NULL,'2025-02-01 08:00:00.000','2025-02-01 08:00:00.000');

INSERT INTO `visitor` (`visitor_pk`,`visitor_id`,`first_seen_at`,`last_seen_at`,`is_deleted`,`deleted_at`,`create_time`,`update_time`) VALUES
  (1,'VIS-001','2025-01-29 08:00:00.000','2025-01-29 09:00:00.000',0,NULL,'2025-01-29 08:00:00.000','2025-01-29 09:00:00.000'),
  (2,'VIS-002','2025-01-30 08:00:00.000','2025-01-30 09:00:00.000',0,NULL,'2025-01-30 08:00:00.000','2025-01-30 09:00:00.000'),
  (3,'VIS-003','2025-01-31 08:00:00.000','2025-01-31 09:00:00.000',0,NULL,'2025-01-31 08:00:00.000','2025-01-31 09:00:00.000'),
  (4,'VIS-004','2025-02-01 08:00:00.000','2025-02-01 09:00:00.000',0,NULL,'2025-02-01 08:00:00.000','2025-02-01 09:00:00.000'),
  (5,'VIS-005','2025-02-01 10:00:00.000','2025-02-01 10:30:00.000',0,NULL,'2025-02-01 10:00:00.000','2025-02-01 10:30:00.000');

INSERT INTO `traffic_channel` (`traffic_channel_pk`,`channel_code`,`channel_name`,`is_deleted`,`deleted_at`,`create_time`,`update_time`) VALUES
  (1,'DIRECT','Direct',0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (2,'SEARCH','Search',0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (3,'SOCIAL','Social',0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000');

INSERT INTO `brand` (`brand_pk`,`brand_id`,`brand_name`,`is_deleted`,`deleted_at`,`create_time`,`update_time`) VALUES
  (1,'BR-001','Brand One Current',0,NULL,'2025-01-29 00:00:00.000','2025-02-01 14:00:00.000'),
  (2,'BR-002','Brand Two',0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000');

INSERT INTO `category` (`category_pk`,`category_id`,`category_name`,`parent_category_pk`,`category_level`,`is_deleted`,`deleted_at`,`create_time`,`update_time`) VALUES
  (1,'CAT-1','Level 1',NULL,1,0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (2,'CAT-2','Level 2A',1,2,0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (3,'CAT-3','Level 3A',2,3,0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (4,'CAT-4','Level 2B',1,2,0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (5,'CAT-5','Level 3B',4,3,0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (6,'CAT-6','Level 3C',4,3,0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000');

INSERT INTO `coupon` (`coupon_pk`,`coupon_id`,`coupon_name`,`discount_amount`,`minimum_original_amount`,`valid_from`,`valid_to`,`is_deleted`,`deleted_at`,`create_time`,`update_time`) VALUES
  (1,'CP-001','Ten Off',10.00,50.00,'2025-01-29 00:00:00.000','2025-02-28 23:59:59.999',0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (2,'CP-002','Five Off',5.00,20.00,'2025-01-29 00:00:00.000','2025-02-28 23:59:59.999',0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (3,'CP-003','Expired',8.00,30.00,'2025-01-01 00:00:00.000','2025-01-28 23:59:59.999',0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000');

INSERT INTO `user_address` (`user_address_pk`,`address_id`,`user_pk`,`province_code`,`province_name`,`city_code`,`city_name`,`detail_address`,`is_deleted`,`deleted_at`,`create_time`,`update_time`) VALUES
  (1,'ADDR-001',1,'110000','Beijing','110100','Beijing','Road 1',0,NULL,'2025-01-29 08:00:00.000','2025-01-29 08:00:00.000'),
  (2,'ADDR-002',2,'310000','Shanghai','310100','Shanghai','Road 2',0,NULL,'2025-01-30 08:00:00.000','2025-01-30 08:00:00.000'),
  (3,'ADDR-003',3,'440000','Guangdong','440100','Guangzhou','Road 3',0,NULL,'2025-01-31 08:00:00.000','2025-01-31 08:00:00.000'),
  (4,'ADDR-004',4,'330000','Zhejiang','330100','Hangzhou','Road 4',0,NULL,'2025-02-01 08:00:00.000','2025-02-01 08:00:00.000');

INSERT INTO `spu` (`spu_pk`,`spu_id`,`spu_name`,`brand_pk`,`category_pk`,`is_deleted`,`deleted_at`,`create_time`,`update_time`) VALUES
  (1,'SPU-001','SPU One',1,3,0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (2,'SPU-002','SPU Two',1,5,0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (3,'SPU-003','SPU Three',2,5,0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (4,'SPU-004','SPU Four',2,6,0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000');

INSERT INTO `sku` (`sku_pk`,`sku_id`,`sku_name`,`spu_pk`,`sale_price`,`currency`,`is_deleted`,`deleted_at`,`create_time`,`update_time`) VALUES
  (1,'SKU-001','SKU One',1,30.00,'CNY',0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (2,'SKU-002','SKU Two',1,25.00,'CNY',0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (3,'SKU-003','SKU Three',2,40.00,'CNY',0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (4,'SKU-004','SKU Four',2,15.00,'CNY',0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (5,'SKU-005','SKU Five',3,50.00,'CNY',0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000'),
  (6,'SKU-006','SKU Six',4,10.00,'CNY',0,NULL,'2025-01-29 00:00:00.000','2025-01-29 00:00:00.000');

INSERT INTO `visit_session` (`visit_session_pk`,`session_id`,`visitor_pk`,`first_channel_pk`,`started_at`,`last_event_at`,`ended_at`,`create_time`,`update_time`) VALUES
  (1,'SES-001',1,1,'2025-01-29 08:00:00.000','2025-01-29 09:00:00.000','2025-01-29 09:00:00.000','2025-01-29 08:00:00.000','2025-01-29 09:00:00.000'),
  (2,'SES-002',2,2,'2025-01-30 08:00:00.000','2025-01-30 09:00:00.000','2025-01-30 09:00:00.000','2025-01-30 08:00:00.000','2025-01-30 09:00:00.000'),
  (3,'SES-003',3,3,'2025-01-31 08:00:00.000','2025-01-31 09:00:00.000','2025-01-31 09:00:00.000','2025-01-31 08:00:00.000','2025-01-31 09:00:00.000'),
  (4,'SES-004',4,1,'2025-02-01 08:00:00.000','2025-02-01 09:00:00.000','2025-02-01 09:00:00.000','2025-02-01 08:00:00.000','2025-02-01 09:00:00.000'),
  (5,'SES-005',5,2,'2025-02-01 10:00:00.000','2025-02-01 10:30:00.000','2025-02-01 10:30:00.000','2025-02-01 10:00:00.000','2025-02-01 10:30:00.000'),
  (6,'SES-006',1,1,'2025-02-01 23:30:00.000','2025-02-01 23:59:00.000','2025-02-01 23:59:00.000','2025-02-01 23:30:00.000','2025-02-01 23:59:00.000');

INSERT INTO `user_coupon` (`user_coupon_pk`,`user_coupon_no`,`request_id`,`coupon_pk`,`user_pk`,`coupon_status`,`discount_amount_snapshot`,`minimum_original_amount_snapshot`,`valid_from`,`valid_to`,`claimed_at`,`locked_at`,`released_at`,`used_at`,`expired_at`,`create_time`,`update_time`) VALUES
  (1,'UC-001','REQ-UC-001',1,1,'USED',10.00,50.00,'2025-01-29 00:00:00.000','2025-02-28 23:59:59.999','2025-01-29 08:00:00.000','2025-01-29 09:00:00.000',NULL,'2025-01-29 09:05:00.000',NULL,'2025-01-29 08:00:00.000','2025-01-29 09:05:00.000'),
  (2,'UC-002','REQ-UC-002',2,2,'CLAIMED',5.00,20.00,'2025-01-29 00:00:00.000','2025-02-28 23:59:59.999','2025-01-30 08:00:00.000',NULL,NULL,NULL,NULL,'2025-01-30 08:00:00.000','2025-01-30 08:00:00.000'),
  (3,'UC-003','REQ-UC-003',3,3,'EXPIRED',8.00,30.00,'2025-01-01 00:00:00.000','2025-01-28 23:59:59.999','2025-01-29 08:00:00.000',NULL,NULL,NULL,'2025-01-29 08:01:00.000','2025-01-29 08:00:00.000','2025-01-29 08:01:00.000'),
  (4,'UC-004','REQ-UC-004',1,3,'LOCKED',10.00,50.00,'2025-01-29 00:00:00.000','2025-02-28 23:59:59.999','2025-01-31 08:00:00.000','2025-01-31 09:00:00.000',NULL,NULL,NULL,'2025-01-31 08:00:00.000','2025-01-31 09:00:00.000'),
  (5,'UC-005','REQ-UC-005',2,4,'CLAIMED',5.00,20.00,'2025-01-29 00:00:00.000','2025-02-28 23:59:59.999','2025-02-01 08:00:00.000','2025-02-01 08:30:00.000','2025-02-01 08:31:00.000',NULL,NULL,'2025-02-01 08:00:00.000','2025-02-01 08:31:00.000');

INSERT INTO `login_event` (`login_event_pk`,`login_event_id`,`visitor_pk`,`session_pk`,`user_pk`,`login_at`,`create_time`) VALUES
  (1,'LOG-001',1,1,1,'2025-01-29 08:10:00.000','2025-01-29 08:10:00.000'),
  (2,'LOG-002',2,2,2,'2025-01-30 08:10:00.000','2025-01-30 08:10:00.000'),
  (3,'LOG-003',3,3,3,'2025-01-31 08:10:00.000','2025-01-31 08:10:00.000'),
  (4,'LOG-004',4,4,4,'2025-02-01 08:10:00.000','2025-02-01 08:10:00.000');

INSERT INTO `cart_event` (`cart_event_pk`,`cart_event_id`,`request_id`,`visitor_pk`,`session_pk`,`user_pk`,`sku_pk`,`action_type`,`quantity_before`,`quantity_after`,`is_valid`,`invalid_reason`,`action_time`,`create_time`) VALUES
  (1,'CART-001','REQ-CART-001',1,1,1,1,'ADD',0,1,1,NULL,'2025-01-29 08:20:00.000','2025-01-29 08:20:00.000'),
  (2,'CART-002','REQ-CART-002',2,2,2,2,'ADD',0,2,1,NULL,'2025-01-30 08:20:00.000','2025-01-30 08:20:00.000'),
  (3,'CART-003','REQ-CART-003',3,3,3,3,'ADD',0,1,1,NULL,'2025-01-31 08:20:00.000','2025-01-31 08:20:00.000'),
  (4,'CART-004','REQ-CART-004',4,4,4,4,'ADD',0,1,1,NULL,'2025-02-01 08:20:00.000','2025-02-01 08:20:00.000'),
  (5,'CART-005','REQ-CART-005',1,6,1,5,'ADD',0,1,1,NULL,'2025-02-01 23:35:00.000','2025-02-01 23:35:00.000'),
  (6,'CART-006','REQ-CART-006',2,2,2,2,'CHANGE_QUANTITY',2,1,1,NULL,'2025-01-30 08:25:00.000','2025-01-30 08:25:00.000'),
  (7,'CART-007','REQ-CART-007',3,3,3,3,'REMOVE',1,0,1,NULL,'2025-01-31 08:25:00.000','2025-01-31 08:25:00.000'),
  (8,'CART-008','REQ-CART-008',5,5,NULL,6,'ADD',0,1,1,NULL,'2025-02-01 10:10:00.000','2025-02-01 10:10:00.000');

INSERT INTO `page_view_event` (`page_view_event_pk`,`page_view_id`,`visitor_pk`,`session_pk`,`user_pk`,`channel_pk`,`page_type`,`page_path`,`sku_pk`,`event_time`,`create_time`) VALUES
  (1,'PV-001',1,1,NULL,1,'HOME','/',NULL,'2025-01-29 08:01:00.000','2025-01-29 08:01:00.000'),
  (2,'PV-002',1,1,1,1,'PRODUCT_DETAIL','/product/SKU-001',1,'2025-01-29 08:15:00.000','2025-01-29 08:15:00.000'),
  (3,'PV-003',2,2,NULL,2,'HOME','/',NULL,'2025-01-30 08:01:00.000','2025-01-30 08:01:00.000'),
  (4,'PV-004',2,2,2,2,'PRODUCT_DETAIL','/product/SKU-002',2,'2025-01-30 08:15:00.000','2025-01-30 08:15:00.000'),
  (5,'PV-005',3,3,NULL,3,'HOME','/',NULL,'2025-01-31 08:01:00.000','2025-01-31 08:01:00.000'),
  (6,'PV-006',3,3,3,3,'PRODUCT_DETAIL','/product/SKU-003',3,'2025-01-31 08:15:00.000','2025-01-31 08:15:00.000'),
  (7,'PV-007',4,4,NULL,1,'HOME','/',NULL,'2025-02-01 08:01:00.000','2025-02-01 08:01:00.000'),
  (8,'PV-008',4,4,4,1,'PRODUCT_DETAIL','/product/SKU-004',4,'2025-02-01 08:15:00.000','2025-02-01 08:15:00.000'),
  (9,'PV-009',5,5,NULL,2,'HOME','/',NULL,'2025-02-01 10:01:00.000','2025-02-01 10:01:00.000'),
  (10,'PV-010',5,5,NULL,2,'PRODUCT_DETAIL','/product/SKU-006',6,'2025-02-01 10:05:00.000','2025-02-01 10:05:00.000'),
  (11,'PV-011',1,6,1,1,'HOME','/',NULL,'2025-02-01 23:31:00.000','2025-02-01 23:31:00.000'),
  (12,'PV-012',1,6,1,1,'PRODUCT_DETAIL','/product/SKU-005',5,'2025-02-01 23:32:00.000','2025-02-01 23:32:00.000'),
  (13,'PV-013',1,1,1,1,'OTHER','/help',NULL,'2025-01-29 08:30:00.000','2025-01-29 08:30:00.000'),
  (14,'PV-014',2,2,2,2,'OTHER','/cart',NULL,'2025-01-30 08:30:00.000','2025-01-30 08:30:00.000'),
  (15,'PV-015',3,3,3,3,'OTHER','/order',NULL,'2025-01-31 08:30:00.000','2025-01-31 08:30:00.000'),
  (16,'PV-016',4,4,4,1,'OTHER','/coupon',NULL,'2025-02-01 08:30:00.000','2025-02-01 08:30:00.000'),
  (17,'PV-017',1,1,1,1,'PRODUCT_DETAIL','/product/SKU-003',3,'2025-01-29 08:35:00.000','2025-01-29 08:35:00.000'),
  (18,'PV-018',2,2,2,2,'PRODUCT_DETAIL','/product/SKU-004',4,'2025-01-30 08:35:00.000','2025-01-30 08:35:00.000');

INSERT INTO `sales_order` (`sales_order_pk`,`order_no`,`request_id`,`user_pk`,`user_address_pk`,`user_coupon_pk`,`order_status`,`province_code`,`province_name`,`original_amount`,`product_discount_amount`,`coupon_discount_amount`,`payable_amount`,`currency`,`ordered_at`,`cancelled_at`,`cancel_reason`,`create_time`,`update_time`) VALUES
  (1,'ORD-001','REQ-ORD-001',1,1,1,'PAID','110000','Beijing',55.00,0.00,10.00,45.00,'CNY','2025-01-29 09:00:00.000',NULL,NULL,'2025-01-29 09:00:00.000','2025-01-29 09:05:00.000'),
  (2,'ORD-002','REQ-ORD-002',2,2,NULL,'PAID','310000','Shanghai',50.00,0.00,0.00,50.00,'CNY','2025-01-30 09:00:00.000',NULL,NULL,'2025-01-30 09:00:00.000','2025-01-30 09:05:00.000'),
  (3,'ORD-003','REQ-ORD-003',3,3,NULL,'CANCELLED','440000','Guangdong',40.00,0.00,0.00,40.00,'CNY','2025-01-31 09:00:00.000','2025-01-31 09:10:00.000','user_cancelled','2025-01-31 09:00:00.000','2025-01-31 09:10:00.000'),
  (4,'ORD-004','REQ-ORD-004',4,4,NULL,'CANCELLED','330000','Zhejiang',15.00,0.00,0.00,15.00,'CNY','2025-02-01 09:00:00.000','2025-02-01 09:10:00.000','payment_failed','2025-02-01 09:00:00.000','2025-02-01 09:10:00.000'),
  (5,'ORD-005','REQ-ORD-005',1,1,NULL,'PAID','110000','Beijing',30.00,0.00,0.00,30.00,'CNY','2025-01-29 10:00:00.000',NULL,NULL,'2025-01-29 10:00:00.000','2025-01-29 10:05:00.000'),
  (6,'ORD-006','REQ-ORD-006',2,2,NULL,'PAID','310000','Shanghai',25.00,0.00,0.00,25.00,'CNY','2025-01-30 10:00:00.000',NULL,NULL,'2025-01-30 10:00:00.000','2025-01-30 10:05:00.000'),
  (7,'ORD-007','REQ-ORD-007',3,3,NULL,'PAID','440000','Guangdong',50.00,0.00,0.00,50.00,'CNY','2025-01-31 10:00:00.000',NULL,NULL,'2025-01-31 10:00:00.000','2025-01-31 10:05:00.000'),
  (8,'ORD-008','REQ-ORD-008',4,4,NULL,'CREATED','330000','Zhejiang',25.00,0.00,0.00,25.00,'CNY','2025-02-01 10:00:00.000',NULL,NULL,'2025-02-01 10:00:00.000','2025-02-01 10:00:00.000');

INSERT INTO `sales_order_item` (`sales_order_item_pk`,`order_item_no`,`order_pk`,`sku_pk`,`quantity`,`brand_id_snapshot`,`brand_name_snapshot`,`category_level1_id_snapshot`,`category_level1_name_snapshot`,`category_level2_id_snapshot`,`category_level2_name_snapshot`,`category_level3_id_snapshot`,`category_level3_name_snapshot`,`spu_id_snapshot`,`spu_name_snapshot`,`sku_id_snapshot`,`sku_name_snapshot`,`unit_original_price`,`original_amount`,`product_discount_amount`,`coupon_discount_amount`,`payable_amount`,`currency`,`create_time`) VALUES
  (1,'ITEM-001',1,1,1,'BR-001','Brand One','CAT-1','Level 1','CAT-2','Level 2A','CAT-3','Level 3A','SPU-001','SPU One','SKU-001','SKU One',30.00,30.00,0.00,5.45,24.55,'CNY','2025-01-29 09:00:00.000'),
  (2,'ITEM-002',1,2,1,'BR-001','Brand One','CAT-1','Level 1','CAT-2','Level 2A','CAT-3','Level 3A','SPU-001','SPU One','SKU-002','SKU Two',25.00,25.00,0.00,4.55,20.45,'CNY','2025-01-29 09:00:00.000'),
  (3,'ITEM-003',2,3,1,'BR-001','Brand One','CAT-1','Level 1','CAT-4','Level 2B','CAT-5','Level 3B','SPU-002','SPU Two','SKU-003','SKU Three',40.00,40.00,0.00,0.00,40.00,'CNY','2025-01-30 09:00:00.000'),
  (4,'ITEM-004',2,6,1,'BR-002','Brand Two','CAT-1','Level 1','CAT-4','Level 2B','CAT-6','Level 3C','SPU-004','SPU Four','SKU-006','SKU Six',10.00,10.00,0.00,0.00,10.00,'CNY','2025-01-30 09:00:00.000'),
  (5,'ITEM-005',3,3,1,'BR-001','Brand One','CAT-1','Level 1','CAT-4','Level 2B','CAT-5','Level 3B','SPU-002','SPU Two','SKU-003','SKU Three',40.00,40.00,0.00,0.00,40.00,'CNY','2025-01-31 09:00:00.000'),
  (6,'ITEM-006',4,4,1,'BR-001','Brand One','CAT-1','Level 1','CAT-4','Level 2B','CAT-5','Level 3B','SPU-002','SPU Two','SKU-004','SKU Four',15.00,15.00,0.00,0.00,15.00,'CNY','2025-02-01 09:00:00.000'),
  (7,'ITEM-007',5,1,1,'BR-001','Brand One','CAT-1','Level 1','CAT-2','Level 2A','CAT-3','Level 3A','SPU-001','SPU One','SKU-001','SKU One',30.00,30.00,0.00,0.00,30.00,'CNY','2025-01-29 10:00:00.000'),
  (8,'ITEM-008',6,2,1,'BR-001','Brand One','CAT-1','Level 1','CAT-2','Level 2A','CAT-3','Level 3A','SPU-001','SPU One','SKU-002','SKU Two',25.00,25.00,0.00,0.00,25.00,'CNY','2025-01-30 10:00:00.000'),
  (9,'ITEM-009',7,3,1,'BR-001','Brand One','CAT-1','Level 1','CAT-4','Level 2B','CAT-5','Level 3B','SPU-002','SPU Two','SKU-003','SKU Three',40.00,40.00,0.00,0.00,40.00,'CNY','2025-01-31 10:00:00.000'),
  (10,'ITEM-010',7,6,1,'BR-002','Brand Two','CAT-1','Level 1','CAT-4','Level 2B','CAT-6','Level 3C','SPU-004','SPU Four','SKU-006','SKU Six',10.00,10.00,0.00,0.00,10.00,'CNY','2025-01-31 10:00:00.000'),
  (11,'ITEM-011',8,4,1,'BR-001','Brand One','CAT-1','Level 1','CAT-4','Level 2B','CAT-5','Level 3B','SPU-002','SPU Two','SKU-004','SKU Four',15.00,15.00,0.00,0.00,15.00,'CNY','2025-02-01 10:00:00.000'),
  (12,'ITEM-012',8,6,1,'BR-002','Brand Two','CAT-1','Level 1','CAT-4','Level 2B','CAT-6','Level 3C','SPU-004','SPU Four','SKU-006','SKU Six',10.00,10.00,0.00,0.00,10.00,'CNY','2025-02-01 10:00:00.000');

INSERT INTO `payment_attempt` (`payment_attempt_pk`,`payment_no`,`request_id`,`order_pk`,`payment_status`,`payment_amount`,`currency`,`attempted_at`,`paid_at`,`failed_at`,`callback_request_id`,`failure_reason`,`create_time`,`update_time`) VALUES
  (1,'PAY-001','REQ-PAY-001',1,'SUCCESS',45.00,'CNY','2025-01-29 09:00:00.000','2025-01-29 09:05:00.000',NULL,'CALLBACK-PAY-001',NULL,'2025-01-29 09:00:00.000','2025-01-29 09:05:00.000'),
  (2,'PAY-002','REQ-PAY-002',2,'SUCCESS',50.00,'CNY','2025-01-30 09:00:00.000','2025-01-30 09:05:00.000',NULL,'CALLBACK-PAY-002',NULL,'2025-01-30 09:00:00.000','2025-01-30 09:05:00.000'),
  (3,'PAY-003','REQ-PAY-003',3,'FAILED',40.00,'CNY','2025-01-31 09:00:00.000',NULL,'2025-01-31 09:02:00.000','CALLBACK-PAY-003','cancelled order','2025-01-31 09:00:00.000','2025-01-31 09:02:00.000'),
  (4,'PAY-004','REQ-PAY-004',4,'FAILED',15.00,'CNY','2025-02-01 09:00:00.000',NULL,'2025-02-01 09:05:00.000','CALLBACK-PAY-004','gateway declined','2025-02-01 09:00:00.000','2025-02-01 09:05:00.000'),
  (5,'PAY-005','REQ-PAY-005',5,'SUCCESS',30.00,'CNY','2025-01-29 10:00:00.000','2025-01-29 10:05:00.000',NULL,'CALLBACK-PAY-005',NULL,'2025-01-29 10:00:00.000','2025-01-29 10:05:00.000'),
  (6,'PAY-006','REQ-PAY-006',6,'SUCCESS',25.00,'CNY','2025-01-30 10:00:00.000','2025-01-30 10:05:00.000',NULL,'CALLBACK-PAY-006',NULL,'2025-01-30 10:00:00.000','2025-01-30 10:05:00.000'),
  (7,'PAY-007','REQ-PAY-007',7,'SUCCESS',50.00,'CNY','2025-01-31 10:00:00.000','2025-01-31 10:05:00.000',NULL,'CALLBACK-PAY-007',NULL,'2025-01-31 10:00:00.000','2025-01-31 10:05:00.000'),
  (8,'PAY-008','REQ-PAY-008',8,'CREATED',25.00,'CNY','2025-02-01 10:00:00.000',NULL,NULL,NULL,NULL,'2025-02-01 10:00:00.000','2025-02-01 10:00:00.000'),
  (9,'PAY-009','REQ-PAY-009',1,'FAILED',45.00,'CNY','2025-01-29 08:59:00.000',NULL,'2025-01-29 08:59:30.000','CALLBACK-PAY-009','gateway timeout','2025-01-29 08:59:00.000','2025-01-29 08:59:30.000'),
  (10,'PAY-010','REQ-PAY-010',3,'CREATED',40.00,'CNY','2025-01-31 09:03:00.000',NULL,NULL,NULL,NULL,'2025-01-31 09:03:00.000','2025-01-31 09:03:00.000');

INSERT INTO `return_order` (`return_order_pk`,`return_no`,`request_id`,`order_pk`,`order_item_pk`,`return_status`,`return_quantity`,`return_reason`,`refund_amount`,`currency`,`applied_at`,`approved_at`,`rejected_at`,`completed_at`,`reject_reason`,`create_time`,`update_time`) VALUES
  (1,'RET-001','REQ-RET-001',1,1,'COMPLETED',1,'defective',24.55,'CNY','2025-01-30 09:00:00.000','2025-01-30 10:00:00.000',NULL,'2025-01-30 11:00:00.000',NULL,'2025-01-30 09:00:00.000','2025-01-30 11:00:00.000'),
  (2,'RET-002','REQ-RET-002',2,3,'APPROVED',1,'not wanted',40.00,'CNY','2025-01-31 09:00:00.000','2025-01-31 10:00:00.000',NULL,NULL,NULL,'2025-01-31 09:00:00.000','2025-01-31 10:00:00.000'),
  (3,'RET-003','REQ-RET-003',6,8,'REJECTED',1,'outside policy',NULL,'CNY','2025-02-01 11:00:00.000',NULL,'2025-02-01 12:00:00.000',NULL,'outside return window','2025-02-01 11:00:00.000','2025-02-01 12:00:00.000'),
  (4,'RET-004','REQ-RET-004',7,10,'COMPLETED',1,'defective',10.00,'CNY','2025-02-01 11:00:00.000','2025-02-01 12:00:00.000',NULL,'2025-02-01 13:00:00.000',NULL,'2025-02-01 11:00:00.000','2025-02-01 13:00:00.000');

INSERT INTO `refund_attempt` (`refund_attempt_pk`,`refund_no`,`request_id`,`return_order_pk`,`order_pk`,`payment_attempt_pk`,`refund_status`,`refund_amount`,`currency`,`attempted_at`,`refunded_at`,`failed_at`,`callback_request_id`,`failure_reason`,`create_time`,`update_time`) VALUES
  (1,'REF-001','REQ-REF-001',1,1,1,'SUCCESS',24.55,'CNY','2025-01-30 10:30:00.000','2025-01-30 11:00:00.000',NULL,'CALLBACK-REF-001',NULL,'2025-01-30 10:30:00.000','2025-01-30 11:00:00.000'),
  (2,'REF-002','REQ-REF-002',2,2,2,'FAILED',40.00,'CNY','2025-01-31 10:30:00.000',NULL,'2025-01-31 10:31:00.000','CALLBACK-REF-002','gateway timeout','2025-01-31 10:30:00.000','2025-01-31 10:31:00.000'),
  (3,'REF-003','REQ-REF-003',2,2,2,'CREATED',40.00,'CNY','2025-01-31 10:32:00.000',NULL,NULL,NULL,NULL,'2025-01-31 10:32:00.000','2025-01-31 10:32:00.000'),
  (4,'REF-004','REQ-REF-004',4,7,7,'SUCCESS',10.00,'CNY','2025-02-01 12:30:00.000','2025-02-01 13:00:00.000',NULL,'CALLBACK-REF-004',NULL,'2025-02-01 12:30:00.000','2025-02-01 13:00:00.000'),
  (5,'REF-005','REQ-REF-005',1,1,1,'FAILED',24.55,'CNY','2025-01-30 10:20:00.000',NULL,'2025-01-30 10:21:00.000','CALLBACK-REF-005','gateway timeout','2025-01-30 10:20:00.000','2025-01-30 10:21:00.000');

COMMIT;
