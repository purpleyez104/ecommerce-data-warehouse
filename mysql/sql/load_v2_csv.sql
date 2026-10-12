-- Rendered by validate_v2_csv_bundle.py after a complete bundle preflight.
-- All schema checks, empty-target protection, LOAD DATA statements and the
-- first Source Gate run execute in this single MySQL session.
SET SESSION sql_mode = 'STRICT_ALL_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
SET SESSION autocommit = 0;
SET @source_load_lock = GET_LOCK(CONCAT(DATABASE(), ':v2-source-load'), 0);
SET @source_load_guard = IF(@source_load_lock = 1, 'SELECT NULL WHERE FALSE', 'SELECT * FROM __source_load_advisory_lock_failed__');
PREPARE source_load_guard_stmt FROM @source_load_guard;
EXECUTE source_load_guard_stmt;
DEALLOCATE PREPARE source_load_guard_stmt;

START TRANSACTION;

__EXPECTED_VARIABLES__

CREATE TEMPORARY TABLE source_load_expected_schema AS
__SCHEMA_ASSERTIONS__;

SET @source_load_schema_mismatches = (
  SELECT COUNT(*)
  FROM source_load_expected_schema expected
  LEFT JOIN (
    SELECT table_name, GROUP_CONCAT(column_name ORDER BY ordinal_position SEPARATOR ',') AS actual_columns
    FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name LIKE 'biz\_%' ESCAPE '\\'
      AND extra NOT LIKE '%GENERATED%'
    GROUP BY table_name
  ) actual USING (table_name)
  WHERE actual.actual_columns IS NULL OR actual.actual_columns <> expected.expected_columns
);
SET @source_load_guard = IF(@source_load_schema_mismatches = 0, 'SELECT NULL WHERE FALSE', 'SELECT * FROM __source_load_schema_mismatch__');
PREPARE source_load_guard_stmt FROM @source_load_guard;
EXECUTE source_load_guard_stmt;
DEALLOCATE PREPARE source_load_guard_stmt;

SET @source_load_existing_rows = 0;
-- The renderer replaces this marker with 21 LOAD statements only after the
-- target-row guard below.  Keep the table list visibly shared with the gate.
SELECT
  (SELECT COUNT(*) FROM biz_user) +
  (SELECT COUNT(*) FROM biz_visitor) +
  (SELECT COUNT(*) FROM biz_identity_mapping) +
  (SELECT COUNT(*) FROM biz_category) +
  (SELECT COUNT(*) FROM biz_spu) +
  (SELECT COUNT(*) FROM biz_sku) +
  (SELECT COUNT(*) FROM biz_product_change_event) +
  (SELECT COUNT(*) FROM biz_cart) +
  (SELECT COUNT(*) FROM biz_cart_item) +
  (SELECT COUNT(*) FROM biz_cart_merge_record) +
  (SELECT COUNT(*) FROM biz_coupon_template) +
  (SELECT COUNT(*) FROM biz_coupon) +
  (SELECT COUNT(*) FROM biz_order) +
  (SELECT COUNT(*) FROM biz_order_item) +
  (SELECT COUNT(*) FROM biz_order_status_event) +
  (SELECT COUNT(*) FROM biz_payment_attempt) +
  (SELECT COUNT(*) FROM biz_payment_event) +
  (SELECT COUNT(*) FROM biz_refund_request) +
  (SELECT COUNT(*) FROM biz_refund_transaction) +
  (SELECT COUNT(*) FROM biz_refund_event) +
  (SELECT COUNT(*) FROM biz_coupon_event)
INTO @source_load_existing_rows;
SET @source_load_guard = IF(@source_load_existing_rows = 0, 'SELECT NULL WHERE FALSE', 'SELECT * FROM __source_load_target_not_empty__');
PREPARE source_load_guard_stmt FROM @source_load_guard;
EXECUTE source_load_guard_stmt;
DEALLOCATE PREPARE source_load_guard_stmt;

__LOAD_STATEMENTS__

SOURCE __SOURCE_GATE_PATH__

COMMIT;
DO RELEASE_LOCK(CONCAT(DATABASE(), ':v2-source-load'));
