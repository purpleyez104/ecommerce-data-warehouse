-- Replay runtime audit table. This is not one of the 21 business source tables.
-- Apply once to an isolated replay database after 001_ecommerce_oltp.sql.
-- A row is committed in the same transaction as its Daily Package, so the
-- database remains the source of truth when local evidence files are missing.

CREATE TABLE `replay_batch_ledger` (
  `batch_id` VARCHAR(128) NOT NULL,
  `day_number` SMALLINT UNSIGNED NOT NULL,
  `business_hash` CHAR(64) NOT NULL,
  `package_manifest_sha256` CHAR(64) NOT NULL,
  `operation_count` BIGINT UNSIGNED NOT NULL,
  `applied_at` TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`batch_id`),
  UNIQUE KEY `uk_replay_batch_day` (`day_number`),
  CONSTRAINT `ck_replay_batch_day` CHECK (`day_number` BETWEEN 61 AND 90),
  CONSTRAINT `ck_replay_batch_business_hash` CHECK (`business_hash` REGEXP '^[0-9a-f]{64}$'),
  CONSTRAINT `ck_replay_batch_package_hash` CHECK (`package_manifest_sha256` REGEXP '^[0-9a-f]{64}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
