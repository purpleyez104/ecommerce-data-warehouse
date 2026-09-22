-- M2-03 / Ecommerce OLTP physical schema V1.0
-- Basis: confirmed design in this conversation; not derived from existing VM candidate DDL.
-- Target: MySQL 8.0.46 / InnoDB / utf8mb4 / Asia/Shanghai business timestamps.
-- REVIEW ONLY. Not executed or deployed. Requires an existing ecommerce_oltp schema.
-- SAFETY: no DROP, TRUNCATE, DELETE, INSERT, or ALTER of pre-existing objects.
-- The final ALTER only closes FKs on biz_coupon created earlier in THIS script.
-- CREATE TABLE intentionally has no IF NOT EXISTS: name collisions must fail visibly.
-- All monetary amounts are signed BIGINT in CNY cents (never FLOAT/DOUBLE).
-- IDs are allocated by the generator/business service; events are immutable by contract.
-- Missing cross-table constraints require transactional application logic (see design notes).

USE `ecommerce_oltp`;

-- 01. Registered user; historical attribute changes are captured by CDC during operation.
CREATE TABLE `biz_user` (
  `user_id` BIGINT NOT NULL,
  `user_key` VARCHAR(64) NOT NULL,
  `user_name` VARCHAR(64) NOT NULL,
  `user_status` VARCHAR(32) NOT NULL,
  `registered_at` DATETIME(3) NOT NULL,
  `created_at` DATETIME(3) NOT NULL,
  `updated_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_biz_user_key` (`user_key`),
  CONSTRAINT `ck_biz_user_status` CHECK (`user_status` IN ('ACTIVE', 'DISABLED')),
  CONSTRAINT `ck_biz_user_time` CHECK (`updated_at` >= `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 02. An anonymous visitor is NOT the same entity as a registered user.
CREATE TABLE `biz_visitor` (
  `visitor_id` BIGINT NOT NULL,
  `visitor_key` VARCHAR(64) NOT NULL,
  `first_seen_at` DATETIME(3) NOT NULL,
  `last_seen_at` DATETIME(3) NOT NULL,
  `created_at` DATETIME(3) NOT NULL,
  `updated_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`visitor_id`),
  UNIQUE KEY `uk_biz_visitor_key` (`visitor_key`),
  CONSTRAINT `ck_biz_visitor_seen` CHECK (`last_seen_at` >= `first_seen_at`),
  CONSTRAINT `ck_biz_visitor_time` CHECK (`updated_at` >= `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 03. Versioned, evidence-based identity mappings; overlapping ranges require service validation.
CREATE TABLE `biz_identity_mapping` (
  `mapping_id` BIGINT NOT NULL,
  `visitor_id` BIGINT NOT NULL,
  `user_id` BIGINT NOT NULL,
  `session_id` VARCHAR(64) NULL,
  `evidence_type` VARCHAR(32) NOT NULL,
  `evidence_id` VARCHAR(64) NOT NULL,
  `mapping_scope` VARCHAR(32) NOT NULL,
  `identity_version` BIGINT NOT NULL,
  `effective_from` DATETIME(3) NOT NULL,
  `effective_to` DATETIME(3) NULL,
  `mapping_status` VARCHAR(32) NOT NULL,
  `recorded_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`mapping_id`),
  UNIQUE KEY `uk_biz_identity_version` (`visitor_id`, `identity_version`),
  UNIQUE KEY `uk_biz_identity_evidence` (`evidence_type`, `evidence_id`),
  KEY `ix_biz_identity_user_from` (`user_id`, `effective_from`),
  KEY `ix_biz_identity_visitor_from` (`visitor_id`, `effective_from`),
  CONSTRAINT `fk_biz_identity_visitor` FOREIGN KEY (`visitor_id`) REFERENCES `biz_visitor` (`visitor_id`),
  CONSTRAINT `fk_biz_identity_user` FOREIGN KEY (`user_id`) REFERENCES `biz_user` (`user_id`),
  CONSTRAINT `ck_biz_identity_version` CHECK (`identity_version` > 0),
  CONSTRAINT `ck_biz_identity_evidence_type` CHECK (`evidence_type` IN ('LOGIN', 'VERIFIED')),
  CONSTRAINT `ck_biz_identity_scope` CHECK (`mapping_scope` IN ('SESSION', 'VISITOR')),
  CONSTRAINT `ck_biz_identity_session` CHECK (`mapping_scope` <> 'SESSION' OR `session_id` IS NOT NULL),
  CONSTRAINT `ck_biz_identity_status` CHECK (`mapping_status` IN ('CONFIRMED', 'REVOKED')),
  CONSTRAINT `ck_biz_identity_range` CHECK (`effective_to` IS NULL OR `effective_to` > `effective_from`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 04. Category -> SPU is 1:N; categories are intentionally flat in this version.
CREATE TABLE `biz_category` (
  `category_id` BIGINT NOT NULL,
  `category_code` VARCHAR(64) NOT NULL,
  `category_name` VARCHAR(128) NOT NULL,
  `category_status` VARCHAR(32) NOT NULL,
  `created_at` DATETIME(3) NOT NULL,
  `updated_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`category_id`),
  UNIQUE KEY `uk_biz_category_code` (`category_code`),
  CONSTRAINT `ck_biz_category_status` CHECK (`category_status` IN ('ACTIVE', 'DISABLED')),
  CONSTRAINT `ck_biz_category_time` CHECK (`updated_at` >= `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 05. Brand as a snapshot attribute, not a separate brand table in the frozen 21-table model.
CREATE TABLE `biz_spu` (
  `spu_id` BIGINT NOT NULL,
  `spu_code` VARCHAR(64) NOT NULL,
  `category_id` BIGINT NOT NULL,
  `brand_code` VARCHAR(64) NOT NULL,
  `brand_name` VARCHAR(128) NOT NULL,
  `spu_name` VARCHAR(255) NOT NULL,
  `spu_status` VARCHAR(32) NOT NULL,
  `created_at` DATETIME(3) NOT NULL,
  `updated_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`spu_id`),
  UNIQUE KEY `uk_biz_spu_code` (`spu_code`),
  KEY `ix_biz_spu_category` (`category_id`),
  KEY `ix_biz_spu_brand` (`brand_code`),
  CONSTRAINT `fk_biz_spu_category` FOREIGN KEY (`category_id`) REFERENCES `biz_category` (`category_id`),
  CONSTRAINT `ck_biz_spu_status` CHECK (`spu_status` IN ('ACTIVE', 'DISABLED')),
  CONSTRAINT `ck_biz_spu_time` CHECK (`updated_at` >= `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 06. SKU is the pricing and transaction unit.
CREATE TABLE `biz_sku` (
  `sku_id` BIGINT NOT NULL,
  `sku_code` VARCHAR(64) NOT NULL,
  `spu_id` BIGINT NOT NULL,
  `sku_name` VARCHAR(255) NOT NULL,
  `sale_price_cents` BIGINT NOT NULL,
  `sku_status` VARCHAR(32) NOT NULL,
  `created_at` DATETIME(3) NOT NULL,
  `updated_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`sku_id`),
  UNIQUE KEY `uk_biz_sku_code` (`sku_code`),
  KEY `ix_biz_sku_spu` (`spu_id`),
  KEY `ix_biz_sku_updated` (`updated_at`),
  CONSTRAINT `fk_biz_sku_spu` FOREIGN KEY (`spu_id`) REFERENCES `biz_spu` (`spu_id`),
  CONSTRAINT `ck_biz_sku_price` CHECK (`sale_price_cents` >= 0),
  CONSTRAINT `ck_biz_sku_status` CHECK (`sku_status` IN ('ON_SALE', 'OFF_SALE')),
  CONSTRAINT `ck_biz_sku_time` CHECK (`updated_at` >= `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 07. Polymorphic target_type/target_id: validated transactionally, not a SQL FK.
CREATE TABLE `biz_product_change_event` (
  `change_id` BIGINT NOT NULL,
  `event_key` VARCHAR(64) NOT NULL,
  `target_type` VARCHAR(32) NOT NULL,
  `target_id` BIGINT NOT NULL,
  `change_type` VARCHAR(32) NOT NULL,
  `before_data` JSON NOT NULL,
  `after_data` JSON NOT NULL,
  `effective_at` DATETIME(3) NOT NULL,
  `recorded_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`change_id`),
  UNIQUE KEY `uk_biz_product_change_event` (`event_key`),
  KEY `ix_biz_product_change_target` (`target_type`, `target_id`, `effective_at`),
  CONSTRAINT `ck_biz_product_change_target` CHECK (`target_type` IN ('CATEGORY', 'SPU', 'SKU')),
  CONSTRAINT `ck_biz_product_change_kind` CHECK (`change_type` IN ('PRICE', 'CATEGORY', 'BRAND', 'STATUS', 'ATTRIBUTES'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 08. Cart ownership is XOR. MySQL unique keys allow multiple NULL values.
CREATE TABLE `biz_cart` (
  `cart_id` BIGINT NOT NULL,
  `user_id` BIGINT NULL,
  `visitor_id` BIGINT NULL,
  `created_at` DATETIME(3) NOT NULL,
  `updated_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`cart_id`),
  UNIQUE KEY `uk_biz_cart_user` (`user_id`),
  UNIQUE KEY `uk_biz_cart_visitor` (`visitor_id`),
  CONSTRAINT `fk_biz_cart_user` FOREIGN KEY (`user_id`) REFERENCES `biz_user` (`user_id`),
  CONSTRAINT `fk_biz_cart_visitor` FOREIGN KEY (`visitor_id`) REFERENCES `biz_visitor` (`visitor_id`),
  CONSTRAINT `ck_biz_cart_owner` CHECK (
    (`user_id` IS NOT NULL AND `visitor_id` IS NULL) OR
    (`user_id` IS NULL AND `visitor_id` IS NOT NULL)
  ),
  CONSTRAINT `ck_biz_cart_time` CHECK (`updated_at` >= `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 09. Each SKU appears at most once in a cart; quantity <= 99.
CREATE TABLE `biz_cart_item` (
  `cart_item_id` BIGINT NOT NULL,
  `cart_id` BIGINT NOT NULL,
  `sku_id` BIGINT NOT NULL,
  `quantity` INT NOT NULL,
  `created_at` DATETIME(3) NOT NULL,
  `updated_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`cart_item_id`),
  UNIQUE KEY `uk_biz_cart_item_sku` (`cart_id`, `sku_id`),
  KEY `ix_biz_cart_item_sku` (`sku_id`),
  CONSTRAINT `fk_biz_cart_item_cart` FOREIGN KEY (`cart_id`) REFERENCES `biz_cart` (`cart_id`),
  CONSTRAINT `fk_biz_cart_item_sku` FOREIGN KEY (`sku_id`) REFERENCES `biz_sku` (`sku_id`),
  CONSTRAINT `ck_biz_cart_item_qty` CHECK (`quantity` BETWEEN 1 AND 99),
  CONSTRAINT `ck_biz_cart_item_time` CHECK (`updated_at` >= `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 10. Stable operation_id prevents a login cart merge from being applied twice.
CREATE TABLE `biz_cart_merge_record` (
  `merge_id` BIGINT NOT NULL,
  `operation_id` VARCHAR(64) NOT NULL,
  `visitor_cart_id` BIGINT NOT NULL,
  `user_cart_id` BIGINT NOT NULL,
  `user_id` BIGINT NOT NULL,
  `merge_detail` JSON NOT NULL,
  `truncated_quantity` INT NOT NULL DEFAULT 0,
  `merged_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`merge_id`),
  UNIQUE KEY `uk_biz_cart_merge_operation` (`operation_id`),
  KEY `ix_biz_cart_merge_visitor` (`visitor_cart_id`),
  KEY `ix_biz_cart_merge_user_cart` (`user_cart_id`),
  KEY `ix_biz_cart_merge_user_time` (`user_id`, `merged_at`),
  CONSTRAINT `fk_biz_cart_merge_visitor` FOREIGN KEY (`visitor_cart_id`) REFERENCES `biz_cart` (`cart_id`),
  CONSTRAINT `fk_biz_cart_merge_cart` FOREIGN KEY (`user_cart_id`) REFERENCES `biz_cart` (`cart_id`),
  CONSTRAINT `fk_biz_cart_merge_user` FOREIGN KEY (`user_id`) REFERENCES `biz_user` (`user_id`),
  CONSTRAINT `ck_biz_cart_merge_different` CHECK (`visitor_cart_id` <> `user_cart_id`),
  CONSTRAINT `ck_biz_cart_merge_truncated` CHECK (`truncated_quantity` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 11. A coupon template defines fixed-amount discount rules for this version.
CREATE TABLE `biz_coupon_template` (
  `template_id` BIGINT NOT NULL,
  `template_code` VARCHAR(64) NOT NULL,
  `template_name` VARCHAR(128) NOT NULL,
  `face_value_cents` BIGINT NOT NULL,
  `min_spend_cents` BIGINT NOT NULL,
  `valid_from` DATETIME(3) NOT NULL,
  `valid_to` DATETIME(3) NOT NULL,
  `issue_limit` INT NOT NULL,
  `template_status` VARCHAR(32) NOT NULL,
  `created_at` DATETIME(3) NOT NULL,
  `updated_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`template_id`),
  UNIQUE KEY `uk_biz_coupon_template_code` (`template_code`),
  CONSTRAINT `ck_biz_coupon_tpl_value` CHECK (`face_value_cents` > 0),
  CONSTRAINT `ck_biz_coupon_tpl_spend` CHECK (`min_spend_cents` >= 0),
  CONSTRAINT `ck_biz_coupon_tpl_valid` CHECK (`valid_to` > `valid_from`),
  CONSTRAINT `ck_biz_coupon_tpl_limit` CHECK (`issue_limit` > 0),
  CONSTRAINT `ck_biz_coupon_tpl_status` CHECK (`template_status` IN ('ACTIVE', 'DISABLED')),
  CONSTRAINT `ck_biz_coupon_tpl_time` CHECK (`updated_at` >= `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 12. Coupon points to order IDs; circular FKs are added after biz_order exists.
-- LOCKED coupon remains usable for the locked order until its 15-minute payment deadline.
CREATE TABLE `biz_coupon` (
  `coupon_id` BIGINT NOT NULL,
  `coupon_code` VARCHAR(64) NOT NULL,
  `template_id` BIGINT NOT NULL,
  `user_id` BIGINT NOT NULL,
  `coupon_status` VARCHAR(32) NOT NULL,
  `locked_order_id` BIGINT NULL,
  `used_order_id` BIGINT NULL,
  `issued_at` DATETIME(3) NOT NULL,
  `expires_at` DATETIME(3) NOT NULL,
  `locked_at` DATETIME(3) NULL,
  `used_at` DATETIME(3) NULL,
  `updated_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`coupon_id`),
  UNIQUE KEY `uk_biz_coupon_code` (`coupon_code`),
  KEY `ix_biz_coupon_template` (`template_id`),
  KEY `ix_biz_coupon_user_status_expiry` (`user_id`, `coupon_status`, `expires_at`),
  KEY `ix_biz_coupon_locked_order` (`locked_order_id`),
  KEY `ix_biz_coupon_used_order` (`used_order_id`),
  CONSTRAINT `fk_biz_coupon_template` FOREIGN KEY (`template_id`) REFERENCES `biz_coupon_template` (`template_id`),
  CONSTRAINT `fk_biz_coupon_user` FOREIGN KEY (`user_id`) REFERENCES `biz_user` (`user_id`),
  CONSTRAINT `ck_biz_coupon_valid` CHECK (`expires_at` > `issued_at`),
  CONSTRAINT `ck_biz_coupon_state` CHECK (
    (`coupon_status` IN ('UNUSED', 'EXPIRED') AND `locked_order_id` IS NULL AND `used_order_id` IS NULL AND `locked_at` IS NULL AND `used_at` IS NULL) OR
    (`coupon_status` = 'LOCKED' AND `locked_order_id` IS NOT NULL AND `locked_at` IS NOT NULL AND `used_order_id` IS NULL AND `used_at` IS NULL) OR
    (`coupon_status` = 'USED' AND `locked_order_id` IS NULL AND `locked_at` IS NULL AND `used_order_id` IS NOT NULL AND `used_at` IS NOT NULL)
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 13. One order has exactly one owner (user or visitor) and at most one coupon.
CREATE TABLE `biz_order` (
  `order_id` BIGINT NOT NULL,
  `order_no` VARCHAR(64) NOT NULL,
  `user_id` BIGINT NULL,
  `visitor_id` BIGINT NULL,
  `coupon_id` BIGINT NULL,
  `order_status` VARCHAR(32) NOT NULL,
  `gross_amount_cents` BIGINT NOT NULL,
  `discount_amount_cents` BIGINT NOT NULL,
  `payable_amount_cents` BIGINT NOT NULL,
  `created_at` DATETIME(3) NOT NULL,
  `payment_deadline_at` DATETIME(3) NOT NULL,
  `paid_at` DATETIME(3) NULL,
  `canceled_at` DATETIME(3) NULL,
  `updated_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`order_id`),
  UNIQUE KEY `uk_biz_order_no` (`order_no`),
  KEY `ix_biz_order_user_time` (`user_id`, `created_at`),
  KEY `ix_biz_order_visitor_time` (`visitor_id`, `created_at`),
  KEY `ix_biz_order_status_time` (`order_status`, `created_at`),
  KEY `ix_biz_order_coupon` (`coupon_id`),
  CONSTRAINT `fk_biz_order_user` FOREIGN KEY (`user_id`) REFERENCES `biz_user` (`user_id`),
  CONSTRAINT `fk_biz_order_visitor` FOREIGN KEY (`visitor_id`) REFERENCES `biz_visitor` (`visitor_id`),
  CONSTRAINT `fk_biz_order_coupon` FOREIGN KEY (`coupon_id`) REFERENCES `biz_coupon` (`coupon_id`),
  CONSTRAINT `ck_biz_order_owner` CHECK (
    (`user_id` IS NOT NULL AND `visitor_id` IS NULL) OR
    (`user_id` IS NULL AND `visitor_id` IS NOT NULL)
  ),
  CONSTRAINT `ck_biz_order_amount` CHECK (
    `gross_amount_cents` >= 0 AND `discount_amount_cents` >= 0 AND
    `discount_amount_cents` <= `gross_amount_cents` AND
    `payable_amount_cents` = `gross_amount_cents` - `discount_amount_cents`
  ),
  CONSTRAINT `ck_biz_order_deadline` CHECK (`payment_deadline_at` > `created_at`),
  CONSTRAINT `ck_biz_order_state` CHECK (
    (`order_status` = 'CREATED' AND `paid_at` IS NULL AND `canceled_at` IS NULL) OR
    (`order_status` = 'PAID' AND `paid_at` IS NOT NULL AND `canceled_at` IS NULL AND `paid_at` <= `payment_deadline_at`) OR
    (`order_status` = 'CANCELED' AND `paid_at` IS NULL AND `canceled_at` IS NOT NULL)
  ),
  CONSTRAINT `ck_biz_order_time` CHECK (`updated_at` >= `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 14. Immutable sale snapshots plus mutable, bounded refund accounting columns.
CREATE TABLE `biz_order_item` (
  `order_item_id` BIGINT NOT NULL,
  `order_id` BIGINT NOT NULL,
  `sku_id` BIGINT NOT NULL,
  `spu_id` BIGINT NOT NULL,
  `category_id` BIGINT NOT NULL,
  `brand_code` VARCHAR(64) NOT NULL,
  `sku_name` VARCHAR(255) NOT NULL,
  `quantity` INT NOT NULL,
  `unit_price_cents` BIGINT NOT NULL,
  `gross_amount_cents` BIGINT NOT NULL,
  `allocated_discount_cents` BIGINT NOT NULL,
  `payable_amount_cents` BIGINT NOT NULL,
  `refund_reserved_cents` BIGINT NOT NULL DEFAULT 0,
  `refunded_cents` BIGINT NOT NULL DEFAULT 0,
  `refunded_quantity` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME(3) NOT NULL,
  `updated_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`order_item_id`),
  UNIQUE KEY `uk_biz_order_item_sku` (`order_id`, `sku_id`),
  UNIQUE KEY `uk_biz_order_item_pair` (`order_id`, `order_item_id`),
  KEY `ix_biz_order_item_sku` (`sku_id`),
  KEY `ix_biz_order_item_spu` (`spu_id`),
  KEY `ix_biz_order_item_category` (`category_id`),
  CONSTRAINT `fk_biz_order_item_order` FOREIGN KEY (`order_id`) REFERENCES `biz_order` (`order_id`),
  CONSTRAINT `fk_biz_order_item_sku` FOREIGN KEY (`sku_id`) REFERENCES `biz_sku` (`sku_id`),
  CONSTRAINT `fk_biz_order_item_spu` FOREIGN KEY (`spu_id`) REFERENCES `biz_spu` (`spu_id`),
  CONSTRAINT `fk_biz_order_item_category` FOREIGN KEY (`category_id`) REFERENCES `biz_category` (`category_id`),
  CONSTRAINT `ck_biz_order_item_qty` CHECK (`quantity` > 0),
  CONSTRAINT `ck_biz_order_item_amount` CHECK (
    `unit_price_cents` >= 0 AND
    `gross_amount_cents` = `unit_price_cents` * `quantity` AND
    `allocated_discount_cents` >= 0 AND `allocated_discount_cents` <= `gross_amount_cents` AND
    `payable_amount_cents` = `gross_amount_cents` - `allocated_discount_cents`
  ),
  CONSTRAINT `ck_biz_order_item_refund` CHECK (
    `refund_reserved_cents` >= 0 AND `refunded_cents` >= 0 AND
    `refunded_cents` + `refund_reserved_cents` <= `payable_amount_cents` AND
    `refunded_quantity` BETWEEN 0 AND `quantity`
  ),
  CONSTRAINT `ck_biz_order_item_time` CHECK (`updated_at` >= `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 15. Append-only order transitions, recorded atomically with biz_order updates.
CREATE TABLE `biz_order_status_event` (
  `order_event_id` BIGINT NOT NULL,
  `event_key` VARCHAR(64) NOT NULL,
  `order_id` BIGINT NOT NULL,
  `event_type` VARCHAR(32) NOT NULL,
  `from_status` VARCHAR(32) NULL,
  `to_status` VARCHAR(32) NOT NULL,
  `occurred_at` DATETIME(3) NOT NULL,
  `recorded_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`order_event_id`),
  UNIQUE KEY `uk_biz_order_event_key` (`event_key`),
  KEY `ix_biz_order_event_order_time` (`order_id`, `occurred_at`),
  CONSTRAINT `fk_biz_order_event_order` FOREIGN KEY (`order_id`) REFERENCES `biz_order` (`order_id`),
  CONSTRAINT `ck_biz_order_event_type` CHECK (`event_type` IN ('CREATE', 'PAY', 'CANCEL')),
  CONSTRAINT `ck_biz_order_event_from` CHECK (`from_status` IS NULL OR `from_status` IN ('CREATED', 'PAID', 'CANCELED')),
  CONSTRAINT `ck_biz_order_event_to` CHECK (`to_status` IN ('CREATED', 'PAID', 'CANCELED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 16. Payment retries have new attempt/funding IDs; repeat callbacks keep the same IDs.
CREATE TABLE `biz_payment_attempt` (
  `payment_attempt_id` BIGINT NOT NULL,
  `order_id` BIGINT NOT NULL,
  `attempt_no` INT NOT NULL,
  `funding_txn_id` VARCHAR(64) NOT NULL,
  `amount_cents` BIGINT NOT NULL,
  `payment_status` VARCHAR(32) NOT NULL,
  `initiated_at` DATETIME(3) NOT NULL,
  `succeeded_at` DATETIME(3) NULL,
  `created_at` DATETIME(3) NOT NULL,
  `updated_at` DATETIME(3) NOT NULL,
  `successful_order_id` BIGINT GENERATED ALWAYS AS (
    CASE WHEN `payment_status` = 'SUCCESS' THEN `order_id` ELSE NULL END
  ) STORED,
  PRIMARY KEY (`payment_attempt_id`),
  UNIQUE KEY `uk_biz_payment_order_attempt` (`order_id`, `attempt_no`),
  UNIQUE KEY `uk_biz_payment_funding` (`funding_txn_id`),
  UNIQUE KEY `uk_biz_payment_one_success` (`successful_order_id`),
  CONSTRAINT `fk_biz_payment_order` FOREIGN KEY (`order_id`) REFERENCES `biz_order` (`order_id`),
  CONSTRAINT `ck_biz_payment_attempt_no` CHECK (`attempt_no` > 0),
  CONSTRAINT `ck_biz_payment_amount` CHECK (`amount_cents` >= 0),
  CONSTRAINT `ck_biz_payment_status` CHECK (
    (`payment_status` = 'SUCCESS' AND `succeeded_at` IS NOT NULL AND `succeeded_at` >= `initiated_at`) OR
    (`payment_status` IN ('INIT', 'FAILED') AND `succeeded_at` IS NULL)
  ),
  CONSTRAINT `ck_biz_payment_time` CHECK (`updated_at` >= `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 17. Events describe attempts; do NOT add payment_event and payment_attempt as two payments.
CREATE TABLE `biz_payment_event` (
  `payment_event_id` BIGINT NOT NULL,
  `event_key` VARCHAR(64) NOT NULL,
  `payment_attempt_id` BIGINT NOT NULL,
  `callback_event_id` VARCHAR(64) NULL,
  `from_status` VARCHAR(32) NULL,
  `to_status` VARCHAR(32) NOT NULL,
  `occurred_at` DATETIME(3) NOT NULL,
  `recorded_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`payment_event_id`),
  UNIQUE KEY `uk_biz_payment_event_key` (`event_key`),
  UNIQUE KEY `uk_biz_payment_callback` (`callback_event_id`),
  KEY `ix_biz_payment_event_attempt` (`payment_attempt_id`, `occurred_at`),
  CONSTRAINT `fk_biz_payment_event_attempt` FOREIGN KEY (`payment_attempt_id`) REFERENCES `biz_payment_attempt` (`payment_attempt_id`),
  CONSTRAINT `ck_biz_payment_event_from` CHECK (`from_status` IS NULL OR `from_status` IN ('INIT', 'FAILED', 'SUCCESS')),
  CONSTRAINT `ck_biz_payment_event_to` CHECK (`to_status` IN ('INIT', 'FAILED', 'SUCCESS'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 18. One refund request belongs to exactly one order item; partial requests may coexist.
CREATE TABLE `biz_refund_request` (
  `refund_request_id` BIGINT NOT NULL,
  `refund_request_no` VARCHAR(64) NOT NULL,
  `order_id` BIGINT NOT NULL,
  `order_item_id` BIGINT NOT NULL,
  `requested_amount_cents` BIGINT NOT NULL,
  `refund_quantity` INT NULL,
  `refund_status` VARCHAR(32) NOT NULL,
  `requested_at` DATETIME(3) NOT NULL,
  `completed_at` DATETIME(3) NULL,
  `created_at` DATETIME(3) NOT NULL,
  `updated_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`refund_request_id`),
  UNIQUE KEY `uk_biz_refund_request_no` (`refund_request_no`),
  KEY `ix_biz_refund_req_order_item` (`order_id`, `order_item_id`),
  KEY `ix_biz_refund_req_item_status` (`order_item_id`, `refund_status`),
  CONSTRAINT `fk_biz_refund_req_item` FOREIGN KEY (`order_id`, `order_item_id`)
    REFERENCES `biz_order_item` (`order_id`, `order_item_id`),
  CONSTRAINT `ck_biz_refund_req_amount` CHECK (`requested_amount_cents` > 0),
  CONSTRAINT `ck_biz_refund_req_quantity` CHECK (`refund_quantity` IS NULL OR `refund_quantity` > 0),
  CONSTRAINT `ck_biz_refund_req_state` CHECK (
    (`refund_status` IN ('REQUESTED', 'PROCESSING') AND `completed_at` IS NULL) OR
    (`refund_status` IN ('SUCCESS', 'FAILED') AND `completed_at` IS NOT NULL AND `completed_at` >= `requested_at`)
  ),
  CONSTRAINT `ck_biz_refund_req_time` CHECK (`updated_at` >= `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 19. One request has at most one successful full refund funding attempt.
CREATE TABLE `biz_refund_transaction` (
  `refund_txn_id` BIGINT NOT NULL,
  `refund_request_id` BIGINT NOT NULL,
  `attempt_no` INT NOT NULL,
  `funding_refund_txn_id` VARCHAR(64) NOT NULL,
  `refund_amount_cents` BIGINT NOT NULL,
  `refund_txn_status` VARCHAR(32) NOT NULL,
  `initiated_at` DATETIME(3) NOT NULL,
  `succeeded_at` DATETIME(3) NULL,
  `created_at` DATETIME(3) NOT NULL,
  `updated_at` DATETIME(3) NOT NULL,
  `successful_request_id` BIGINT GENERATED ALWAYS AS (
    CASE WHEN `refund_txn_status` = 'SUCCESS' THEN `refund_request_id` ELSE NULL END
  ) STORED,
  PRIMARY KEY (`refund_txn_id`),
  UNIQUE KEY `uk_biz_refund_txn_attempt` (`refund_request_id`, `attempt_no`),
  UNIQUE KEY `uk_biz_refund_funding` (`funding_refund_txn_id`),
  UNIQUE KEY `uk_biz_refund_one_success` (`successful_request_id`),
  UNIQUE KEY `uk_biz_refund_txn_pair` (`refund_request_id`, `refund_txn_id`),
  CONSTRAINT `fk_biz_refund_txn_request` FOREIGN KEY (`refund_request_id`) REFERENCES `biz_refund_request` (`refund_request_id`),
  CONSTRAINT `ck_biz_refund_txn_attempt_no` CHECK (`attempt_no` > 0),
  CONSTRAINT `ck_biz_refund_txn_amount` CHECK (`refund_amount_cents` > 0),
  CONSTRAINT `ck_biz_refund_txn_state` CHECK (
    (`refund_txn_status` = 'SUCCESS' AND `succeeded_at` IS NOT NULL AND `succeeded_at` >= `initiated_at`) OR
    (`refund_txn_status` IN ('INIT', 'FAILED') AND `succeeded_at` IS NULL)
  ),
  CONSTRAINT `ck_biz_refund_txn_time` CHECK (`updated_at` >= `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 20. Composite FK ensures an optional funding attempt belongs to this request.
CREATE TABLE `biz_refund_event` (
  `refund_event_id` BIGINT NOT NULL,
  `event_key` VARCHAR(64) NOT NULL,
  `refund_request_id` BIGINT NOT NULL,
  `refund_txn_id` BIGINT NULL,
  `event_type` VARCHAR(32) NOT NULL,
  `from_status` VARCHAR(32) NULL,
  `to_status` VARCHAR(32) NOT NULL,
  `occurred_at` DATETIME(3) NOT NULL,
  `recorded_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`refund_event_id`),
  UNIQUE KEY `uk_biz_refund_event_key` (`event_key`),
  KEY `ix_biz_refund_event_request` (`refund_request_id`, `occurred_at`),
  KEY `ix_biz_refund_event_pair` (`refund_request_id`, `refund_txn_id`),
  CONSTRAINT `fk_biz_refund_event_request` FOREIGN KEY (`refund_request_id`) REFERENCES `biz_refund_request` (`refund_request_id`),
  CONSTRAINT `fk_biz_refund_event_txn_pair` FOREIGN KEY (`refund_request_id`, `refund_txn_id`)
    REFERENCES `biz_refund_transaction` (`refund_request_id`, `refund_txn_id`),
  CONSTRAINT `ck_biz_refund_event_type` CHECK (`event_type` IN ('REQUEST', 'PROCESS', 'SUCCESS', 'FAIL')),
  CONSTRAINT `ck_biz_refund_event_from` CHECK (`from_status` IS NULL OR `from_status` IN ('REQUESTED', 'PROCESSING', 'SUCCESS', 'FAILED')),
  CONSTRAINT `ck_biz_refund_event_to` CHECK (`to_status` IN ('REQUESTED', 'PROCESSING', 'SUCCESS', 'FAILED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 21. Coupon events preserve history after a canceled order releases the coupon.
CREATE TABLE `biz_coupon_event` (
  `coupon_event_id` BIGINT NOT NULL,
  `event_key` VARCHAR(64) NOT NULL,
  `coupon_id` BIGINT NOT NULL,
  `order_id` BIGINT NULL,
  `event_type` VARCHAR(32) NOT NULL,
  `from_status` VARCHAR(32) NULL,
  `to_status` VARCHAR(32) NOT NULL,
  `occurred_at` DATETIME(3) NOT NULL,
  `recorded_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`coupon_event_id`),
  UNIQUE KEY `uk_biz_coupon_event_key` (`event_key`),
  KEY `ix_biz_coupon_event_coupon` (`coupon_id`, `occurred_at`),
  KEY `ix_biz_coupon_event_order` (`order_id`),
  CONSTRAINT `fk_biz_coupon_event_coupon` FOREIGN KEY (`coupon_id`) REFERENCES `biz_coupon` (`coupon_id`),
  CONSTRAINT `fk_biz_coupon_event_order` FOREIGN KEY (`order_id`) REFERENCES `biz_order` (`order_id`),
  CONSTRAINT `ck_biz_coupon_event_type` CHECK (`event_type` IN ('ISSUE', 'LOCK', 'USE', 'UNLOCK', 'EXPIRE')),
  CONSTRAINT `ck_biz_coupon_event_from` CHECK (`from_status` IS NULL OR `from_status` IN ('UNUSED', 'LOCKED', 'USED', 'EXPIRED')),
  CONSTRAINT `ck_biz_coupon_event_to` CHECK (`to_status` IN ('UNUSED', 'LOCKED', 'USED', 'EXPIRED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Deferred references close the coupon <-> order dependency after both tables exist.
-- In a transaction: INSERT coupon first, INSERT order with coupon_id, UPDATE coupon.locked_order_id.
ALTER TABLE `biz_coupon`
  ADD CONSTRAINT `fk_biz_coupon_locked_order` FOREIGN KEY (`locked_order_id`) REFERENCES `biz_order` (`order_id`),
  ADD CONSTRAINT `fk_biz_coupon_used_order` FOREIGN KEY (`used_order_id`) REFERENCES `biz_order` (`order_id`);

-- End of review-only DDL; no data migration or database execution performed.
