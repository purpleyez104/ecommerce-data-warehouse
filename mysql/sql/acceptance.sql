-- READ ONLY, replace <RUN_ID> with your actual ASCII run-id after verification.
-- Run against ecommerce_oltp_m2_acceptance. NEVER paste secrets.
-- e.g. replace <RUN_ID> with hist-v1-001 in a local editor.

SELECT COUNT(*) AS generated_orders,
       SUM(order_status = 'PAID') AS paid_orders,
       SUM(order_status = 'CANCELED') AS canceled_orders,
       SUM(gross_amount_cents) AS gross_cents,
       SUM(discount_amount_cents) AS discount_cents,
       SUM(payable_amount_cents) AS payable_cents
FROM biz_order WHERE LEFT(order_no, CHAR_LENGTH('GEN1_<RUN_ID>_ORDER_')) = 'GEN1_<RUN_ID>_ORDER_';

SELECT COUNT(*) AS amount_mismatch
FROM (
  SELECT o.order_id
  FROM biz_order o JOIN biz_order_item i ON i.order_id=o.order_id
  WHERE LEFT(o.order_no, CHAR_LENGTH('GEN1_<RUN_ID>_ORDER_')) = 'GEN1_<RUN_ID>_ORDER_'
  GROUP BY o.order_id
  HAVING COUNT(*) NOT BETWEEN 1 AND 5
     OR SUM(i.gross_amount_cents) <> MAX(o.gross_amount_cents)
     OR SUM(i.allocated_discount_cents) <> MAX(o.discount_amount_cents)
     OR SUM(i.payable_amount_cents) <> MAX(o.payable_amount_cents)
) q;

SELECT COUNT(*) AS deadline_mismatch
FROM biz_order
WHERE LEFT(order_no, CHAR_LENGTH('GEN1_<RUN_ID>_ORDER_')) = 'GEN1_<RUN_ID>_ORDER_'
  AND TIMESTAMPDIFF(SECOND, created_at, payment_deadline_at) <> 900;

SELECT COUNT(*) AS pay_state_mismatch
FROM (
 SELECT o.order_id, o.order_status,
        COALESCE(SUM(p.payment_status='SUCCESS'),0) AS successes
 FROM biz_order o LEFT JOIN biz_payment_attempt p ON p.order_id=o.order_id
 WHERE LEFT(o.order_no, CHAR_LENGTH('GEN1_<RUN_ID>_ORDER_')) = 'GEN1_<RUN_ID>_ORDER_'
 GROUP BY o.order_id
 HAVING successes > 1 OR (order_status='PAID') <> (successes=1)
) q;

SELECT COUNT(*) AS refund_ledger_mismatch
FROM biz_order_item i JOIN biz_order o ON o.order_id=i.order_id
WHERE LEFT(o.order_no, CHAR_LENGTH('GEN1_<RUN_ID>_ORDER_')) = 'GEN1_<RUN_ID>_ORDER_'
  AND (i.refunded_cents + i.refund_reserved_cents > i.payable_amount_cents
       OR i.refunded_quantity > i.quantity);
