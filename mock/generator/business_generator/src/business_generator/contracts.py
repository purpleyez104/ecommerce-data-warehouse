"""CSV and behavior contracts derived from the V2 source specifications."""

TABLE_COLUMNS = {
    "biz_user": ["user_id", "user_key", "user_name", "user_status", "registered_at", "created_at", "updated_at"],
    "biz_visitor": ["visitor_id", "visitor_key", "first_seen_at", "last_seen_at", "created_at", "updated_at"],
    "biz_identity_mapping": ["mapping_id", "visitor_id", "user_id", "session_id", "evidence_type", "evidence_id", "mapping_scope", "identity_version", "effective_from", "effective_to", "mapping_status", "recorded_at"],
    "biz_category": ["category_id", "category_code", "category_name", "category_status", "created_at", "updated_at"],
    "biz_spu": ["spu_id", "spu_code", "category_id", "brand_code", "brand_name", "spu_name", "spu_status", "created_at", "updated_at"],
    "biz_sku": ["sku_id", "sku_code", "spu_id", "sku_name", "sale_price_cents", "sku_status", "created_at", "updated_at"],
    "biz_product_change_event": ["change_id", "event_key", "target_type", "target_id", "change_type", "before_data", "after_data", "effective_at", "recorded_at"],
    "biz_cart": ["cart_id", "user_id", "visitor_id", "created_at", "updated_at"],
    "biz_cart_item": ["cart_item_id", "cart_id", "sku_id", "quantity", "created_at", "updated_at"],
    "biz_cart_merge_record": ["merge_id", "operation_id", "visitor_cart_id", "user_cart_id", "user_id", "merge_detail", "truncated_quantity", "merged_at"],
    "biz_order": ["order_id", "order_no", "user_id", "visitor_id", "coupon_id", "order_status", "gross_amount_cents", "discount_amount_cents", "payable_amount_cents", "created_at", "payment_deadline_at", "paid_at", "canceled_at", "updated_at"],
    "biz_order_item": ["order_item_id", "order_id", "sku_id", "spu_id", "category_id", "brand_code", "sku_name", "quantity", "unit_price_cents", "gross_amount_cents", "allocated_discount_cents", "payable_amount_cents", "refund_reserved_cents", "refunded_cents", "refunded_quantity", "created_at", "updated_at"],
    "biz_order_status_event": ["order_event_id", "event_key", "order_id", "event_type", "from_status", "to_status", "occurred_at", "recorded_at"],
    "biz_payment_attempt": ["payment_attempt_id", "order_id", "attempt_no", "funding_txn_id", "amount_cents", "payment_status", "initiated_at", "succeeded_at", "created_at", "updated_at"],
    "biz_payment_event": ["payment_event_id", "event_key", "payment_attempt_id", "callback_event_id", "from_status", "to_status", "occurred_at", "recorded_at"],
    "biz_refund_request": ["refund_request_id", "refund_request_no", "order_id", "order_item_id", "requested_amount_cents", "refund_quantity", "refund_status", "requested_at", "completed_at", "created_at", "updated_at"],
    "biz_refund_transaction": ["refund_txn_id", "refund_request_id", "attempt_no", "funding_refund_txn_id", "refund_amount_cents", "refund_txn_status", "initiated_at", "succeeded_at", "created_at", "updated_at"],
    "biz_refund_event": ["refund_event_id", "event_key", "refund_request_id", "refund_txn_id", "event_type", "from_status", "to_status", "occurred_at", "recorded_at"],
    "biz_coupon_template": ["template_id", "template_code", "template_name", "face_value_cents", "min_spend_cents", "valid_from", "valid_to", "issue_limit", "template_status", "created_at", "updated_at"],
    "biz_coupon": ["coupon_id", "coupon_code", "template_id", "user_id", "coupon_status", "locked_order_id", "used_order_id", "issued_at", "expires_at", "locked_at", "used_at", "updated_at"],
    "biz_coupon_event": ["coupon_event_id", "event_key", "coupon_id", "order_id", "event_type", "from_status", "to_status", "occurred_at", "recorded_at"],
}

TABLE_ORDER = list(TABLE_COLUMNS)
