-- Shared Source Gate. Expected values are injected as @expected_* session
-- variables by the validated bundle runner. Output protocol is exactly:
-- rule_id<TAB>violation_count
DROP TEMPORARY TABLE IF EXISTS source_gate_results;
CREATE TEMPORARY TABLE source_gate_results (
  rule_id VARCHAR(128) NOT NULL PRIMARY KEY,
  violation_count BIGINT NOT NULL
);

-- RULE: count.biz_user
INSERT INTO source_gate_results VALUES ('count.biz_user', ABS((SELECT COUNT(*) FROM biz_user) - @expected_biz_user));
-- RULE: count.biz_visitor
INSERT INTO source_gate_results VALUES ('count.biz_visitor', ABS((SELECT COUNT(*) FROM biz_visitor) - @expected_biz_visitor));
-- RULE: count.biz_identity_mapping
INSERT INTO source_gate_results VALUES ('count.biz_identity_mapping', ABS((SELECT COUNT(*) FROM biz_identity_mapping) - @expected_biz_identity_mapping));
-- RULE: count.biz_category
INSERT INTO source_gate_results VALUES ('count.biz_category', ABS((SELECT COUNT(*) FROM biz_category) - @expected_biz_category));
-- RULE: count.biz_spu
INSERT INTO source_gate_results VALUES ('count.biz_spu', ABS((SELECT COUNT(*) FROM biz_spu) - @expected_biz_spu));
-- RULE: count.biz_sku
INSERT INTO source_gate_results VALUES ('count.biz_sku', ABS((SELECT COUNT(*) FROM biz_sku) - @expected_biz_sku));
-- RULE: count.biz_product_change_event
INSERT INTO source_gate_results VALUES ('count.biz_product_change_event', ABS((SELECT COUNT(*) FROM biz_product_change_event) - @expected_biz_product_change_event));
-- RULE: count.biz_cart
INSERT INTO source_gate_results VALUES ('count.biz_cart', ABS((SELECT COUNT(*) FROM biz_cart) - @expected_biz_cart));
-- RULE: count.biz_cart_item
INSERT INTO source_gate_results VALUES ('count.biz_cart_item', ABS((SELECT COUNT(*) FROM biz_cart_item) - @expected_biz_cart_item));
-- RULE: count.biz_cart_merge_record
INSERT INTO source_gate_results VALUES ('count.biz_cart_merge_record', ABS((SELECT COUNT(*) FROM biz_cart_merge_record) - @expected_biz_cart_merge_record));
-- RULE: count.biz_coupon_template
INSERT INTO source_gate_results VALUES ('count.biz_coupon_template', ABS((SELECT COUNT(*) FROM biz_coupon_template) - @expected_biz_coupon_template));
-- RULE: count.biz_coupon
INSERT INTO source_gate_results VALUES ('count.biz_coupon', ABS((SELECT COUNT(*) FROM biz_coupon) - @expected_biz_coupon));
-- RULE: count.biz_order
INSERT INTO source_gate_results VALUES ('count.biz_order', ABS((SELECT COUNT(*) FROM biz_order) - @expected_biz_order));
-- RULE: count.biz_order_item
INSERT INTO source_gate_results VALUES ('count.biz_order_item', ABS((SELECT COUNT(*) FROM biz_order_item) - @expected_biz_order_item));
-- RULE: count.biz_order_status_event
INSERT INTO source_gate_results VALUES ('count.biz_order_status_event', ABS((SELECT COUNT(*) FROM biz_order_status_event) - @expected_biz_order_status_event));
-- RULE: count.biz_payment_attempt
INSERT INTO source_gate_results VALUES ('count.biz_payment_attempt', ABS((SELECT COUNT(*) FROM biz_payment_attempt) - @expected_biz_payment_attempt));
-- RULE: count.biz_payment_event
INSERT INTO source_gate_results VALUES ('count.biz_payment_event', ABS((SELECT COUNT(*) FROM biz_payment_event) - @expected_biz_payment_event));
-- RULE: count.biz_refund_request
INSERT INTO source_gate_results VALUES ('count.biz_refund_request', ABS((SELECT COUNT(*) FROM biz_refund_request) - @expected_biz_refund_request));
-- RULE: count.biz_refund_transaction
INSERT INTO source_gate_results VALUES ('count.biz_refund_transaction', ABS((SELECT COUNT(*) FROM biz_refund_transaction) - @expected_biz_refund_transaction));
-- RULE: count.biz_refund_event
INSERT INTO source_gate_results VALUES ('count.biz_refund_event', ABS((SELECT COUNT(*) FROM biz_refund_event) - @expected_biz_refund_event));
-- RULE: count.biz_coupon_event
INSERT INTO source_gate_results VALUES ('count.biz_coupon_event', ABS((SELECT COUNT(*) FROM biz_coupon_event) - @expected_biz_coupon_event));

-- RULE: unique.primary_keys
INSERT INTO source_gate_results
SELECT 'unique.primary_keys',
  (SELECT COUNT(*)-COUNT(DISTINCT user_id) FROM biz_user) +
  (SELECT COUNT(*)-COUNT(DISTINCT visitor_id) FROM biz_visitor) +
  (SELECT COUNT(*)-COUNT(DISTINCT mapping_id) FROM biz_identity_mapping) +
  (SELECT COUNT(*)-COUNT(DISTINCT category_id) FROM biz_category) +
  (SELECT COUNT(*)-COUNT(DISTINCT spu_id) FROM biz_spu) +
  (SELECT COUNT(*)-COUNT(DISTINCT sku_id) FROM biz_sku) +
  (SELECT COUNT(*)-COUNT(DISTINCT change_id) FROM biz_product_change_event) +
  (SELECT COUNT(*)-COUNT(DISTINCT cart_id) FROM biz_cart) +
  (SELECT COUNT(*)-COUNT(DISTINCT cart_item_id) FROM biz_cart_item) +
  (SELECT COUNT(*)-COUNT(DISTINCT merge_id) FROM biz_cart_merge_record) +
  (SELECT COUNT(*)-COUNT(DISTINCT template_id) FROM biz_coupon_template) +
  (SELECT COUNT(*)-COUNT(DISTINCT coupon_id) FROM biz_coupon) +
  (SELECT COUNT(*)-COUNT(DISTINCT order_id) FROM biz_order) +
  (SELECT COUNT(*)-COUNT(DISTINCT order_item_id) FROM biz_order_item) +
  (SELECT COUNT(*)-COUNT(DISTINCT order_event_id) FROM biz_order_status_event) +
  (SELECT COUNT(*)-COUNT(DISTINCT payment_attempt_id) FROM biz_payment_attempt) +
  (SELECT COUNT(*)-COUNT(DISTINCT payment_event_id) FROM biz_payment_event) +
  (SELECT COUNT(*)-COUNT(DISTINCT refund_request_id) FROM biz_refund_request) +
  (SELECT COUNT(*)-COUNT(DISTINCT refund_txn_id) FROM biz_refund_transaction) +
  (SELECT COUNT(*)-COUNT(DISTINCT refund_event_id) FROM biz_refund_event) +
  (SELECT COUNT(*)-COUNT(DISTINCT coupon_event_id) FROM biz_coupon_event);

-- RULE: unique.business_keys
INSERT INTO source_gate_results
SELECT 'unique.business_keys',
  (SELECT COUNT(*) - COUNT(DISTINCT user_key) FROM biz_user) +
  (SELECT COUNT(*) - COUNT(DISTINCT visitor_key) FROM biz_visitor) +
  (SELECT COUNT(*) - COUNT(DISTINCT category_code) FROM biz_category) +
  (SELECT COUNT(*) - COUNT(DISTINCT spu_code) FROM biz_spu) +
  (SELECT COUNT(*) - COUNT(DISTINCT sku_code) FROM biz_sku) +
  (SELECT COUNT(*) - COUNT(DISTINCT template_code) FROM biz_coupon_template) +
  (SELECT COUNT(*) - COUNT(DISTINCT order_no) FROM biz_order) +
  (SELECT COUNT(*) - COUNT(DISTINCT coupon_code) FROM biz_coupon) +
  (SELECT COUNT(*) - COUNT(DISTINCT refund_request_no) FROM biz_refund_request);

-- RULE: unique.secondary_keys
INSERT INTO source_gate_results
SELECT 'unique.secondary_keys',
  (SELECT COUNT(*)-COUNT(DISTINCT visitor_id,identity_version) FROM biz_identity_mapping) +
  (SELECT COUNT(*)-COUNT(DISTINCT evidence_type,evidence_id) FROM biz_identity_mapping) +
  (SELECT COUNT(*)-COUNT(DISTINCT event_key) FROM biz_product_change_event) +
  (SELECT COUNT(user_id)-COUNT(DISTINCT user_id) FROM biz_cart) +
  (SELECT COUNT(visitor_id)-COUNT(DISTINCT visitor_id) FROM biz_cart) +
  (SELECT COUNT(*)-COUNT(DISTINCT cart_id,sku_id) FROM biz_cart_item) +
  (SELECT COUNT(*)-COUNT(DISTINCT operation_id) FROM biz_cart_merge_record) +
  (SELECT COUNT(*)-COUNT(DISTINCT order_id,sku_id) FROM biz_order_item) +
  (SELECT COUNT(*)-COUNT(DISTINCT event_key) FROM biz_order_status_event) +
  (SELECT COUNT(*)-COUNT(DISTINCT order_id,attempt_no) FROM biz_payment_attempt) +
  (SELECT COUNT(*)-COUNT(DISTINCT funding_txn_id) FROM biz_payment_attempt) +
  (SELECT COUNT(*)-COUNT(DISTINCT event_key) FROM biz_payment_event) +
  (SELECT COUNT(callback_event_id)-COUNT(DISTINCT callback_event_id) FROM biz_payment_event) +
  (SELECT COUNT(*)-COUNT(DISTINCT refund_request_id,attempt_no) FROM biz_refund_transaction) +
  (SELECT COUNT(*)-COUNT(DISTINCT funding_refund_txn_id) FROM biz_refund_transaction) +
  (SELECT COUNT(*)-COUNT(DISTINCT event_key) FROM biz_refund_event) +
  (SELECT COUNT(*)-COUNT(DISTINCT event_key) FROM biz_coupon_event);

-- RULE: reference.foreign_keys
INSERT INTO source_gate_results
SELECT 'reference.foreign_keys',
  (SELECT COUNT(*) FROM biz_identity_mapping x LEFT JOIN biz_visitor p ON x.visitor_id=p.visitor_id WHERE p.visitor_id IS NULL) +
  (SELECT COUNT(*) FROM biz_identity_mapping x LEFT JOIN biz_user p ON x.user_id=p.user_id WHERE p.user_id IS NULL) +
  (SELECT COUNT(*) FROM biz_spu x LEFT JOIN biz_category p ON x.category_id=p.category_id WHERE p.category_id IS NULL) +
  (SELECT COUNT(*) FROM biz_sku x LEFT JOIN biz_spu p ON x.spu_id=p.spu_id WHERE p.spu_id IS NULL) +
  (SELECT COUNT(*) FROM biz_cart x LEFT JOIN biz_user p ON x.user_id=p.user_id WHERE x.user_id IS NOT NULL AND p.user_id IS NULL) +
  (SELECT COUNT(*) FROM biz_cart x LEFT JOIN biz_visitor p ON x.visitor_id=p.visitor_id WHERE x.visitor_id IS NOT NULL AND p.visitor_id IS NULL) +
  (SELECT COUNT(*) FROM biz_cart_item x LEFT JOIN biz_cart p ON x.cart_id=p.cart_id WHERE p.cart_id IS NULL) +
  (SELECT COUNT(*) FROM biz_cart_item x LEFT JOIN biz_sku p ON x.sku_id=p.sku_id WHERE p.sku_id IS NULL) +
  (SELECT COUNT(*) FROM biz_cart_merge_record x LEFT JOIN biz_cart p ON x.visitor_cart_id=p.cart_id WHERE p.cart_id IS NULL) +
  (SELECT COUNT(*) FROM biz_cart_merge_record x LEFT JOIN biz_cart p ON x.user_cart_id=p.cart_id WHERE p.cart_id IS NULL) +
  (SELECT COUNT(*) FROM biz_cart_merge_record x LEFT JOIN biz_user p ON x.user_id=p.user_id WHERE p.user_id IS NULL) +
  (SELECT COUNT(*) FROM biz_coupon x LEFT JOIN biz_coupon_template p ON x.template_id=p.template_id WHERE p.template_id IS NULL) +
  (SELECT COUNT(*) FROM biz_coupon x LEFT JOIN biz_user p ON x.user_id=p.user_id WHERE p.user_id IS NULL) +
  (SELECT COUNT(*) FROM biz_order x LEFT JOIN biz_user p ON x.user_id=p.user_id WHERE x.user_id IS NOT NULL AND p.user_id IS NULL) +
  (SELECT COUNT(*) FROM biz_order x LEFT JOIN biz_visitor p ON x.visitor_id=p.visitor_id WHERE x.visitor_id IS NOT NULL AND p.visitor_id IS NULL) +
  (SELECT COUNT(*) FROM biz_order x LEFT JOIN biz_coupon p ON x.coupon_id=p.coupon_id WHERE x.coupon_id IS NOT NULL AND p.coupon_id IS NULL) +
  (SELECT COUNT(*) FROM biz_order_item x LEFT JOIN biz_order p ON x.order_id=p.order_id WHERE p.order_id IS NULL) +
  (SELECT COUNT(*) FROM biz_order_item x LEFT JOIN biz_sku p ON x.sku_id=p.sku_id WHERE p.sku_id IS NULL) +
  (SELECT COUNT(*) FROM biz_order_item x LEFT JOIN biz_spu p ON x.spu_id=p.spu_id WHERE p.spu_id IS NULL) +
  (SELECT COUNT(*) FROM biz_order_item x LEFT JOIN biz_category p ON x.category_id=p.category_id WHERE p.category_id IS NULL) +
  (SELECT COUNT(*) FROM biz_order_status_event x LEFT JOIN biz_order p ON x.order_id=p.order_id WHERE p.order_id IS NULL) +
  (SELECT COUNT(*) FROM biz_payment_attempt x LEFT JOIN biz_order p ON x.order_id=p.order_id WHERE p.order_id IS NULL) +
  (SELECT COUNT(*) FROM biz_payment_event x LEFT JOIN biz_payment_attempt p ON x.payment_attempt_id=p.payment_attempt_id WHERE p.payment_attempt_id IS NULL) +
  (SELECT COUNT(*) FROM biz_refund_request x LEFT JOIN biz_order_item p ON x.order_id=p.order_id AND x.order_item_id=p.order_item_id WHERE p.order_item_id IS NULL) +
  (SELECT COUNT(*) FROM biz_refund_transaction x LEFT JOIN biz_refund_request p ON x.refund_request_id=p.refund_request_id WHERE p.refund_request_id IS NULL) +
  (SELECT COUNT(*) FROM biz_refund_event x LEFT JOIN biz_refund_request p ON x.refund_request_id=p.refund_request_id WHERE p.refund_request_id IS NULL) +
  (SELECT COUNT(*) FROM biz_refund_event x LEFT JOIN biz_refund_transaction p ON x.refund_request_id=p.refund_request_id AND x.refund_txn_id=p.refund_txn_id WHERE x.refund_txn_id IS NOT NULL AND p.refund_txn_id IS NULL) +
  (SELECT COUNT(*) FROM biz_coupon_event x LEFT JOIN biz_coupon p ON x.coupon_id=p.coupon_id WHERE p.coupon_id IS NULL) +
  (SELECT COUNT(*) FROM biz_coupon_event x LEFT JOIN biz_order p ON x.order_id=p.order_id WHERE x.order_id IS NOT NULL AND p.order_id IS NULL);

-- RULE: reference.soft_and_polymorphic
INSERT INTO source_gate_results
SELECT 'reference.soft_and_polymorphic',
  (SELECT COUNT(*) FROM biz_product_change_event e LEFT JOIN biz_category c ON e.target_type='CATEGORY' AND e.target_id=c.category_id LEFT JOIN biz_spu p ON e.target_type='SPU' AND e.target_id=p.spu_id LEFT JOIN biz_sku s ON e.target_type='SKU' AND e.target_id=s.sku_id WHERE c.category_id IS NULL AND p.spu_id IS NULL AND s.sku_id IS NULL) +
  (SELECT COUNT(*) FROM biz_coupon c LEFT JOIN biz_order o ON COALESCE(c.locked_order_id,c.used_order_id)=o.order_id WHERE COALESCE(c.locked_order_id,c.used_order_id) IS NOT NULL AND o.order_id IS NULL);

-- RULE: cart.merge_contract
INSERT INTO source_gate_results
SELECT 'cart.merge_contract', COUNT(*) FROM biz_cart_merge_record m
JOIN biz_cart vc ON vc.cart_id=m.visitor_cart_id
JOIN biz_cart uc ON uc.cart_id=m.user_cart_id
WHERE vc.visitor_id IS NULL OR uc.user_id IS NULL OR uc.user_id<>m.user_id OR m.visitor_cart_id=m.user_cart_id OR m.truncated_quantity<0;

-- RULE: order.header_item_amount
INSERT INTO source_gate_results
SELECT 'order.header_item_amount', COUNT(*) FROM biz_order o
LEFT JOIN (SELECT order_id, SUM(gross_amount_cents) gross, SUM(allocated_discount_cents) discount_amount, SUM(payable_amount_cents) payable FROM biz_order_item GROUP BY order_id) i USING(order_id)
WHERE i.order_id IS NULL OR o.gross_amount_cents<>i.gross OR o.discount_amount_cents<>i.discount_amount OR o.payable_amount_cents<>i.payable;

-- RULE: payment.success_uniqueness_amount
INSERT INTO source_gate_results
SELECT 'payment.success_uniqueness_amount', COUNT(*) FROM (
  SELECT o.order_id FROM biz_order o LEFT JOIN biz_payment_attempt p ON p.order_id=o.order_id AND p.payment_status='SUCCESS'
  GROUP BY o.order_id, o.order_status, o.payable_amount_cents
  HAVING COALESCE(SUM(p.payment_status='SUCCESS'),0) <> IF(o.order_status='PAID',1,0)
     OR COALESCE(MAX(p.amount_cents),o.payable_amount_cents)<>o.payable_amount_cents
) violations;

-- RULE: payment.attempt_amount_and_success_time
INSERT INTO source_gate_results
SELECT 'payment.attempt_amount_and_success_time', COUNT(*)
FROM biz_payment_attempt p JOIN biz_order o USING(order_id)
WHERE p.amount_cents<>o.payable_amount_cents
   OR (p.payment_status='SUCCESS' AND (o.paid_at IS NULL OR p.succeeded_at<>o.paid_at));

-- RULE: payment.fifteen_minute_window
INSERT INTO source_gate_results
SELECT 'payment.fifteen_minute_window', COUNT(*) FROM biz_payment_attempt p JOIN biz_order o USING(order_id)
WHERE NOT (o.payment_deadline_at <=> TIMESTAMPADD(MINUTE,15,o.created_at))
   OR p.initiated_at<o.created_at OR p.initiated_at>o.payment_deadline_at
   OR (p.payment_status='SUCCESS' AND p.succeeded_at>o.payment_deadline_at);

-- RULE: refund.request_item_bounds
INSERT INTO source_gate_results
SELECT 'refund.request_item_bounds', COUNT(*) FROM biz_refund_request r JOIN biz_order_item i ON r.order_id=i.order_id AND r.order_item_id=i.order_item_id
JOIN biz_order o ON o.order_id=r.order_id
WHERE o.order_status<>'PAID'
   OR r.requested_amount_cents>i.payable_amount_cents
   OR (r.refund_quantity IS NOT NULL AND r.refund_quantity>i.quantity);

-- RULE: refund.success_funding
INSERT INTO source_gate_results
SELECT 'refund.success_funding', COUNT(*) FROM (
  SELECT r.refund_request_id FROM biz_refund_request r LEFT JOIN biz_refund_transaction t ON t.refund_request_id=r.refund_request_id AND t.refund_txn_status='SUCCESS'
  GROUP BY r.refund_request_id,r.refund_status,r.requested_amount_cents
  HAVING COALESCE(SUM(t.refund_txn_status='SUCCESS'),0)<>IF(r.refund_status='SUCCESS',1,0)
     OR COALESCE(MAX(t.refund_amount_cents),r.requested_amount_cents)<>r.requested_amount_cents
) violations;

-- RULE: refund.transaction_lifecycle
INSERT INTO source_gate_results
SELECT 'refund.transaction_lifecycle', COUNT(*) FROM (
  SELECT r.refund_request_id, r.refund_status,
    COALESCE(SUM(t.refund_txn_status='INIT'),0) init_count,
    COALESCE(SUM(t.refund_txn_status='FAILED'),0) failed_count,
    COALESCE(SUM(t.refund_txn_status='SUCCESS'),0) success_count,
    COUNT(t.refund_txn_id) txn_count
  FROM biz_refund_request r
  LEFT JOIN biz_refund_transaction t USING(refund_request_id)
  GROUP BY r.refund_request_id, r.refund_status
  HAVING (r.refund_status='REQUESTED' AND txn_count<>0)
     OR (r.refund_status='PROCESSING' AND (init_count<1 OR failed_count<>0 OR success_count<>0))
     OR (r.refund_status='SUCCESS' AND success_count<>1)
     OR (r.refund_status='FAILED' AND (success_count<>0 OR failed_count<1))
) violations;

-- RULE: refund.item_aggregate
INSERT INTO source_gate_results
SELECT 'refund.item_aggregate', COUNT(*) FROM biz_order_item i
LEFT JOIN (SELECT order_item_id, SUM(CASE WHEN refund_status IN ('REQUESTED','PROCESSING') THEN requested_amount_cents ELSE 0 END) reserved_amount, SUM(CASE WHEN refund_status='SUCCESS' THEN requested_amount_cents ELSE 0 END) refunded_amount, SUM(CASE WHEN refund_status='SUCCESS' THEN COALESCE(refund_quantity,0) ELSE 0 END) refunded_qty FROM biz_refund_request GROUP BY order_item_id) r USING(order_item_id)
WHERE i.refund_reserved_cents<>COALESCE(r.reserved_amount,0) OR i.refunded_cents<>COALESCE(r.refunded_amount,0) OR i.refunded_quantity<>COALESCE(r.refunded_qty,0);

-- RULE: coupon.order_bidirectional
INSERT INTO source_gate_results
SELECT 'coupon.order_bidirectional',
  (SELECT COUNT(*) FROM biz_order o JOIN biz_coupon c ON o.coupon_id=c.coupon_id WHERE
    (o.user_id IS NOT NULL AND o.user_id<>c.user_id) OR NOT (
      (o.order_status='CREATED' AND c.coupon_status='LOCKED' AND (c.locked_order_id <=> o.order_id) AND c.used_order_id IS NULL) OR
      (o.order_status='PAID' AND c.coupon_status='USED' AND (c.used_order_id <=> o.order_id) AND c.locked_order_id IS NULL) OR
      (o.order_status='CANCELED' AND c.coupon_status IN ('UNUSED','EXPIRED') AND c.locked_order_id IS NULL AND c.used_order_id IS NULL)
    )) +
  (SELECT COUNT(*) FROM biz_coupon c LEFT JOIN biz_order o ON o.order_id=COALESCE(c.locked_order_id,c.used_order_id) WHERE COALESCE(c.locked_order_id,c.used_order_id) IS NOT NULL AND (o.order_id IS NULL OR NOT (o.coupon_id <=> c.coupon_id)));

-- RULE: coupon.event_order_reference
INSERT INTO source_gate_results
SELECT 'coupon.event_order_reference', COUNT(*) FROM biz_coupon_event e
JOIN biz_order o ON o.order_id=e.order_id
WHERE e.order_id IS NOT NULL AND NOT (o.coupon_id <=> e.coupon_id);

-- RULE: event.order_final_state
INSERT INTO source_gate_results
SELECT 'event.order_final_state', COUNT(*) FROM biz_order o
LEFT JOIN (SELECT e.order_id,e.to_status FROM biz_order_status_event e JOIN (SELECT order_id,MAX(occurred_at) occurred_at FROM biz_order_status_event GROUP BY order_id) x ON x.order_id=e.order_id AND x.occurred_at=e.occurred_at) final USING(order_id)
WHERE final.to_status IS NULL OR final.to_status<>o.order_status;

-- RULE: event.refund_final_state
INSERT INTO source_gate_results
SELECT 'event.refund_final_state', COUNT(*) FROM biz_refund_request r
LEFT JOIN (SELECT e.refund_request_id,e.to_status FROM biz_refund_event e JOIN (SELECT refund_request_id,MAX(occurred_at) occurred_at FROM biz_refund_event GROUP BY refund_request_id) x ON x.refund_request_id=e.refund_request_id AND x.occurred_at=e.occurred_at) final USING(refund_request_id)
WHERE final.to_status IS NULL OR final.to_status<>r.refund_status;

-- RULE: event.payment_final_state
INSERT INTO source_gate_results
SELECT 'event.payment_final_state', COUNT(*) FROM biz_payment_attempt p
LEFT JOIN (SELECT e.payment_attempt_id,e.to_status FROM biz_payment_event e JOIN (SELECT payment_attempt_id,MAX(occurred_at) occurred_at FROM biz_payment_event GROUP BY payment_attempt_id) x ON x.payment_attempt_id=e.payment_attempt_id AND x.occurred_at=e.occurred_at) final USING(payment_attempt_id)
WHERE final.to_status IS NULL OR final.to_status<>p.payment_status;

-- RULE: event.coupon_final_state
INSERT INTO source_gate_results
SELECT 'event.coupon_final_state', COUNT(*) FROM biz_coupon c
LEFT JOIN (SELECT e.coupon_id,e.to_status FROM biz_coupon_event e JOIN (SELECT coupon_id,MAX(occurred_at) occurred_at FROM biz_coupon_event GROUP BY coupon_id) x ON x.coupon_id=e.coupon_id AND x.occurred_at=e.occurred_at) final USING(coupon_id)
WHERE final.to_status IS NULL OR final.to_status<>c.coupon_status;

-- RULE: event.recorded_after_occurred
INSERT INTO source_gate_results
SELECT 'event.recorded_after_occurred',
  (SELECT COUNT(*) FROM biz_order_status_event WHERE recorded_at<occurred_at) +
  (SELECT COUNT(*) FROM biz_payment_event WHERE recorded_at<occurred_at) +
  (SELECT COUNT(*) FROM biz_refund_event WHERE recorded_at<occurred_at) +
  (SELECT COUNT(*) FROM biz_coupon_event WHERE recorded_at<occurred_at) +
  (SELECT COUNT(*) FROM biz_product_change_event WHERE recorded_at<effective_at);

-- RULE: event.transition_contract
INSERT INTO source_gate_results
SELECT 'event.transition_contract',
  (SELECT COALESCE(SUM(CASE WHEN
    (event_type='CREATE' AND from_status IS NULL AND to_status='CREATED') OR
    (event_type='PAY' AND from_status='CREATED' AND to_status='PAID') OR
    (event_type='CANCEL' AND from_status='CREATED' AND to_status='CANCELED') THEN 0 ELSE 1 END),0)
   FROM biz_order_status_event) +
  (SELECT COALESCE(SUM(CASE WHEN from_status='INIT' AND to_status IN ('INIT','FAILED','SUCCESS') THEN 0 ELSE 1 END),0)
   FROM biz_payment_event) +
  (SELECT COALESCE(SUM(CASE WHEN
    (event_type='REQUEST' AND from_status IS NULL AND to_status='REQUESTED') OR
    (event_type='PROCESS' AND from_status='REQUESTED' AND to_status='PROCESSING') OR
    (event_type='SUCCESS' AND from_status='PROCESSING' AND to_status='SUCCESS') OR
    (event_type='FAIL' AND from_status='PROCESSING' AND to_status='FAILED') THEN 0 ELSE 1 END),0)
   FROM biz_refund_event) +
  (SELECT COALESCE(SUM(CASE WHEN
    (event_type='ISSUE' AND from_status IS NULL AND to_status='UNUSED') OR
    (event_type='LOCK' AND from_status='UNUSED' AND to_status='LOCKED') OR
    (event_type='USE' AND from_status='LOCKED' AND to_status='USED') OR
    (event_type='UNLOCK' AND from_status='LOCKED' AND to_status IN ('UNUSED','EXPIRED')) OR
    (event_type='EXPIRE' AND from_status='UNUSED' AND to_status='EXPIRED') THEN 0 ELSE 1 END),0)
   FROM biz_coupon_event);

-- RULE: event.chain_continuity
INSERT INTO source_gate_results
SELECT 'event.chain_continuity',
  (SELECT COUNT(*) FROM (
    SELECT from_status,ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY occurred_at,order_event_id) rn,
      LAG(to_status) OVER (PARTITION BY order_id ORDER BY occurred_at,order_event_id) prior_to
    FROM biz_order_status_event) x
   WHERE (rn=1 AND from_status IS NOT NULL) OR (rn>1 AND NOT (from_status <=> prior_to))) +
  (SELECT COUNT(*) FROM (
    SELECT from_status,ROW_NUMBER() OVER (PARTITION BY payment_attempt_id ORDER BY occurred_at,payment_event_id) rn,
      LAG(to_status) OVER (PARTITION BY payment_attempt_id ORDER BY occurred_at,payment_event_id) prior_to
    FROM biz_payment_event) x
   WHERE (rn=1 AND NOT (from_status <=> 'INIT')) OR (rn>1 AND NOT (from_status <=> prior_to))) +
  (SELECT COUNT(*) FROM (
    SELECT from_status,ROW_NUMBER() OVER (PARTITION BY refund_request_id ORDER BY occurred_at,refund_event_id) rn,
      LAG(to_status) OVER (PARTITION BY refund_request_id ORDER BY occurred_at,refund_event_id) prior_to
    FROM biz_refund_event) x
   WHERE (rn=1 AND from_status IS NOT NULL) OR (rn>1 AND NOT (from_status <=> prior_to))) +
  (SELECT COUNT(*) FROM (
    SELECT from_status,ROW_NUMBER() OVER (PARTITION BY coupon_id ORDER BY occurred_at,coupon_event_id) rn,
      LAG(to_status) OVER (PARTITION BY coupon_id ORDER BY occurred_at,coupon_event_id) prior_to
    FROM biz_coupon_event) x
   WHERE (rn=1 AND from_status IS NOT NULL) OR (rn>1 AND NOT (from_status <=> prior_to)));

-- RULE: manifest.order_status_distribution
INSERT INTO source_gate_results
SELECT 'manifest.order_status_distribution',
  ABS(SUM(order_status='PAID')-@expected_paid_orders) +
  ABS(SUM(order_status='CANCELED')-@expected_canceled_orders) +
  ABS(SUM(order_status='CREATED')-@expected_created_orders)
FROM biz_order;

SELECT rule_id, violation_count FROM source_gate_results ORDER BY rule_id;
SET @source_gate_violation_total = (SELECT SUM(violation_count) FROM source_gate_results);
SET @source_gate_guard = IF(@source_gate_violation_total = 0, 'SELECT NULL WHERE FALSE', 'SELECT * FROM __source_gate_failed__');
PREPARE source_gate_guard_stmt FROM @source_gate_guard;
EXECUTE source_gate_guard_stmt;
DEALLOCATE PREPARE source_gate_guard_stmt;
