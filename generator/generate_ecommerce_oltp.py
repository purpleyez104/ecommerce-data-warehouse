"""Generate deterministic, candidate ecommerce_oltp INSERT SQL without MySQL access."""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

from generator.rules import (
    RuleViolation,
    allocate_discount,
    assert_coupon_use,
    assert_payment_amount,
    assert_refund_limit,
    assert_return_limit,
    refund_amount_for_completed_return,
    assert_successful_payment,
    assert_transition,
    money,
    next_active_return_quantity,
)


TABLE_ORDER = [
    "user_account", "visitor", "traffic_channel", "brand", "category", "coupon",
    "user_address", "visit_session", "spu", "sku", "user_coupon", "login_event",
    "page_view_event", "cart_event", "sales_order", "sales_order_item", "payment_attempt",
    "return_order", "refund_attempt",
]


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("start-date must use yyyy-MM-dd") from error


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("value must be an integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("seed must be an integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("seed must not be negative")
    return parsed


def timestamp(day: date, hour: int, minute: int = 0) -> str:
    return datetime.combine(day, time(hour, minute)).strftime("%Y-%m-%d %H:%M:%S.000")


def quote(value: object | None) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(value)


def insert(table: str, columns: list[str], rows: list[tuple[object, ...]]) -> str:
    values = ",\n".join("  (" + ",".join(quote(value) for value in row) + ")" for row in rows)
    return f"INSERT INTO `{table}` (" + ",".join(f"`{column}`" for column in columns) + f") VALUES\n{values};\n"


def validate_payment_rows(order_rows: list[tuple[object, ...]], payment_rows: list[tuple[object, ...]]) -> None:
    payable_by_order = {row[0]: row[12] for row in order_rows}
    for payment in payment_rows:
        if payment[4] == "SUCCESS":
            assert_payment_amount(payment[5], payable_by_order[payment[3]])


def validate_coupon_rows(
    coupon_rows: list[tuple[object, ...]],
    user_coupon_rows: list[tuple[object, ...]],
    order_rows: list[tuple[object, ...]],
) -> None:
    coupons = {row[0]: row for row in coupon_rows}
    user_coupons = {row[0]: row for row in user_coupon_rows}
    used_by_order: set[int] = set()
    for order in order_rows:
        user_coupon_pk = order[5]
        if user_coupon_pk is None:
            continue
        coupon = user_coupons[user_coupon_pk]
        definition = coupons[coupon[3]]
        lock_time = coupon[11]
        assert_coupon_use(
            "LOCKED",
            lock_time is not None and coupon[8] <= lock_time <= coupon[9],
            user_coupon_pk in used_by_order,
            coupon[4] == order[3],
            order[9],
            coupon[7],
            coupon[6],
        )
        if coupon[5] != "USED" or coupon[13] is None or order[11] != coupon[6]:
            raise RuleViolation("used coupon row does not match its order")
        if coupon[6] != definition[3] or coupon[7] != definition[4] or coupon[8] != definition[5] or coupon[9] != definition[6]:
            raise RuleViolation("coupon snapshot does not match coupon definition")
        used_by_order.add(user_coupon_pk)


def build_sql(seed: int, start_date: date, days: int, scale: int) -> str:
    """Build candidate SQL. Each scale unit contains the confirmed 19-table shape."""

    rng = random.Random(seed)
    business_days = [start_date + timedelta(days=index % days) for index in range(max(days, 4 * scale))]
    users = 4 * scale
    visitors = 5 * scale
    channels = 3 * scale
    brands = 2 * scale
    categories = 6 * scale
    spus = 4 * scale
    skus = 6 * scale
    orders = 8 * scale

    user_rows = [(index, f"USR-{index:03d}", timestamp(business_days[(index - 1) % len(business_days)], 8), 0, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)) for index in range(1, users + 1)]
    visitor_rows = [(index, f"VIS-{index:03d}", timestamp(business_days[(index - 1) % len(business_days)], 8), timestamp(business_days[(index - 1) % len(business_days)], 23), 0, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)) for index in range(1, visitors + 1)]
    channel_rows = [(index, f"CH-{index:03d}", f"Channel {index}", 0, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)) for index in range(1, channels + 1)]
    brand_rows = [(index, f"BR-{index:03d}", f"Brand {index}", 0, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)) for index in range(1, brands + 1)]

    category_rows: list[tuple[object, ...]] = []
    for group in range(scale):
        offset = group * 6
        category_rows.extend([
            (offset + 1, f"CAT-{offset + 1:03d}", f"Level 1-{group + 1}", None, 1, 0, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)),
            (offset + 2, f"CAT-{offset + 2:03d}", f"Level 2A-{group + 1}", offset + 1, 2, 0, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)),
            (offset + 3, f"CAT-{offset + 3:03d}", f"Level 3A-{group + 1}", offset + 2, 3, 0, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)),
            (offset + 4, f"CAT-{offset + 4:03d}", f"Level 2B-{group + 1}", offset + 1, 2, 0, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)),
            (offset + 5, f"CAT-{offset + 5:03d}", f"Level 3B-{group + 1}", offset + 4, 3, 0, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)),
            (offset + 6, f"CAT-{offset + 6:03d}", f"Level 3C-{group + 1}", offset + 4, 3, 0, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)),
        ])
    coupon_discounts = {index: money(5 + index) for index in range(1, 3 * scale + 1)}
    coupon_rows = [(index, f"CP-{index:03d}", f"Coupon {index}", coupon_discounts[index], money(20), timestamp(business_days[0], 0), timestamp(start_date + timedelta(days=days - 1), 23, 59), 0, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)) for index in range(1, 3 * scale + 1)]
    address_rows = [(index, f"ADDR-{index:03d}", index, "110000", "Beijing", "110100", "Beijing", f"Road {index}", 0, None, timestamp(business_days[(index - 1) % len(business_days)], 8), timestamp(business_days[(index - 1) % len(business_days)], 8)) for index in range(1, users + 1)]
    session_rows = [(index, f"SES-{index:03d}", ((index - 1) % visitors) + 1, ((index - 1) % channels) + 1, timestamp(business_days[(index - 1) % len(business_days)], 8), timestamp(business_days[(index - 1) % len(business_days)], 9), timestamp(business_days[(index - 1) % len(business_days)], 9), timestamp(business_days[(index - 1) % len(business_days)], 8), timestamp(business_days[(index - 1) % len(business_days)], 9)) for index in range(1, 6 * scale + 1)]
    spu_rows = [(index, f"SPU-{index:03d}", f"SPU {index}", ((index - 1) % brands) + 1, ((index - 1) % scale) * 6 + (3 if index % 2 else 5), 0, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)) for index in range(1, spus + 1)]
    sku_prices = {
        index: money(10 + index * 5 + rng.randint(0, 4))
        for index in range(1, skus + 1)
    }
    sku_rows = [(index, f"SKU-{index:03d}", f"SKU {index}", ((index - 1) % spus) + 1, sku_prices[index], "CNY", 0, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)) for index in range(1, skus + 1)]
    coupon_orders: dict[int, int] = {}
    used_coupon_pks: set[int] = set()
    for index in range(1, orders + 1):
        user_coupon_pk = ((index - 1) % users) + 1
        if index % 3 == 1 and index <= 4 * scale and user_coupon_pk not in used_coupon_pks:
            coupon_orders[index] = user_coupon_pk
            used_coupon_pks.add(user_coupon_pk)
    user_coupon_discounts = {
        index: coupon_discounts[((index - 1) % (3 * scale)) + 1]
        for index in range(1, 5 * scale + 1)
    }
    user_coupon_rows = [(index, f"UC-{index:03d}", f"REQ-UC-{index:03d}", ((index - 1) % (3 * scale)) + 1, ((index - 1) % users) + 1, "USED" if index in used_coupon_pks else "CLAIMED", user_coupon_discounts[index], money(20), timestamp(business_days[0], 0), timestamp(start_date + timedelta(days=days - 1), 23, 59), timestamp(business_days[(index - 1) % len(business_days)], 8), timestamp(business_days[(index - 1) % len(business_days)], 8, 30) if index in used_coupon_pks else None, None, timestamp(business_days[(index - 1) % len(business_days)], 9) if index in used_coupon_pks else None, None, timestamp(business_days[0], 0), timestamp(business_days[0], 0)) for index in range(1, 5 * scale + 1)]
    session_visitors = {row[0]: row[2] for row in session_rows}
    login_rows = [(index, f"LOG-{index:03d}", session_visitors[((index - 1) % (6 * scale)) + 1], ((index - 1) % (6 * scale)) + 1, ((index - 1) % users) + 1, timestamp(business_days[(index - 1) % len(business_days)], 8, 10), timestamp(business_days[(index - 1) % len(business_days)], 8, 10)) for index in range(1, 4 * scale + 1)]
    session_users = {row[3]: row[4] for row in login_rows}

    page_rows = []
    for index in range(1, 18 * scale + 1):
        day = business_days[(index - 1) % len(business_days)]
        is_product = index % 2 == 0
        session_pk = ((index - 1) % (6 * scale)) + 1
        page_rows.append((index, f"PV-{index:03d}", session_visitors[session_pk], session_pk, session_users.get(session_pk), ((index - 1) % channels) + 1, "PRODUCT_DETAIL" if is_product else "HOME", f"/product/SKU-{((index - 1) % skus) + 1:03d}" if is_product else "/", ((index - 1) % skus) + 1 if is_product else None, timestamp(day, 8, 15), timestamp(day, 8, 15)))
    cart_rows = [(index, f"CART-{index:03d}", f"REQ-CART-{index:03d}", session_visitors[((index - 1) % (6 * scale)) + 1], ((index - 1) % (6 * scale)) + 1, session_users.get(((index - 1) % (6 * scale)) + 1), ((index - 1) % skus) + 1, "ADD", 0, 1, 1, None, timestamp(business_days[(index - 1) % len(business_days)], 8, 20), timestamp(business_days[(index - 1) % len(business_days)], 8, 20)) for index in range(1, 8 * scale + 1)]

    order_rows = []
    item_rows = []
    payment_rows = []
    successful_orders: set[str] = set()
    item_pk = 1
    for index in range(1, orders + 1):
        day = business_days[(index - 1) % len(business_days)]
        order_id = f"ORD-{index:03d}"
        line_count = 2 if index <= 4 * scale else 1
        line_sku_ids = [((index + line - 1) % skus) + 1 for line in range(line_count)]
        line_amounts = [sku_prices[sku_id] for sku_id in line_sku_ids]
        original = sum(line_amounts, money(0))
        user_coupon_pk = coupon_orders.get(index)
        coupon_discount = user_coupon_discounts[user_coupon_pk] if user_coupon_pk else money(0)
        if user_coupon_pk:
            coupon_user_pk = ((user_coupon_pk - 1) % users) + 1
            assert_coupon_use(
                "LOCKED",
                start_date <= day <= start_date + timedelta(days=days - 1),
                False,
                coupon_user_pk == ((index - 1) % users) + 1,
                original,
                money(20),
                coupon_discount,
            )
        allocations = allocate_discount(line_amounts, coupon_discount)
        payable = money(original - coupon_discount)
        status = "CANCELLED" if index % 8 == 3 else "PAID"
        order_rows.append((index, order_id, f"REQ-ORD-{index:03d}", ((index - 1) % users) + 1, ((index - 1) % users) + 1, user_coupon_pk, status, "110000", "Beijing", original, money(0), coupon_discount, payable, "CNY", timestamp(day, 9), timestamp(day, 9, 10) if status == "CANCELLED" else None, "user_cancelled" if status == "CANCELLED" else None, timestamp(day, 9), timestamp(day, 9, 10) if status == "CANCELLED" else timestamp(day, 9, 5)))
        for line, amount in enumerate(line_amounts):
            sku_id = line_sku_ids[line]
            spu_id = ((sku_id - 1) % spus) + 1
            category_group = (spu_id - 1) % scale
            category_base = category_group * 6
            category_level3 = 3 if spu_id % 2 else 5
            category_level2 = 2 if category_level3 == 3 else 4
            category_label = "A" if category_level3 == 3 else "B"
            item_rows.append((item_pk, f"ITEM-{item_pk:03d}", index, sku_id, 1, f"BR-{((sku_id - 1) % brands) + 1:03d}", f"Brand {((sku_id - 1) % brands) + 1}", f"CAT-{category_base + 1:03d}", f"Level 1-{category_group + 1}", f"CAT-{category_base + category_level2:03d}", f"Level 2{category_label}-{category_group + 1}", f"CAT-{category_base + category_level3:03d}", f"Level 3{category_label}-{category_group + 1}", f"SPU-{spu_id:03d}", f"SPU {spu_id}", f"SKU-{sku_id:03d}", f"SKU {sku_id}", amount, amount, money(0), allocations[line], money(amount - allocations[line]), "CNY", timestamp(day, 9)))
            item_pk += 1
        payment_status = "FAILED" if status == "CANCELLED" else "SUCCESS"
        if payment_status == "SUCCESS":
            assert_successful_payment(order_id, successful_orders)
        payment_rows.append((index, f"PAY-{index:03d}", f"REQ-PAY-{index:03d}", index, payment_status, payable, "CNY", timestamp(day, 9), timestamp(day, 9, 5) if payment_status == "SUCCESS" else None, timestamp(day, 9, 2) if payment_status == "FAILED" else None, f"CALLBACK-PAY-{index:03d}", "cancelled order" if payment_status == "FAILED" else None, timestamp(day, 9), timestamp(day, 9, 5) if payment_status == "SUCCESS" else timestamp(day, 9, 2)))
    while len(payment_rows) < 10 * scale:
        index = len(payment_rows) + 1
        order_pk = ((index - 1) % orders) + 1
        day = business_days[(index - 1) % len(business_days)]
        payment_rows.append((index, f"PAY-{index:03d}", f"REQ-PAY-{index:03d}", order_pk, "FAILED", money(10), "CNY", timestamp(day, 8, 55), None, timestamp(day, 8, 56), f"CALLBACK-PAY-{index:03d}", "retry", timestamp(day, 8, 55), timestamp(day, 8, 56)))

    return_rows = []
    refund_rows = []
    active_returns: dict[int, int] = {}
    completed_returns: dict[int, int] = {}
    successful_refunds_by_item: dict[int, object] = {}
    successful_refunds_by_order: dict[int, object] = {}
    paid_item_rows = [row for row in item_rows if order_rows[row[2] - 1][6] == "PAID"]
    for index in range(1, 4 * scale + 1):
        item = paid_item_rows[(index - 1) % len(paid_item_rows)]
        order_pk = item[2]
        day = business_days[(index - 1) % len(business_days)]
        status = ("COMPLETED", "REJECTED", "COMPLETED", "APPROVED")[(index - 1) % 4]
        quantity = 1
        active_returns[item[0]] = next_active_return_quantity(status, quantity, active_returns.get(item[0], 0), item[4])
        completed_before = completed_returns.get(item[0], 0)
        completed_after = completed_before + quantity
        if status == "COMPLETED":
            refund_amount = refund_amount_for_completed_return(item[21], item[4], completed_before, completed_after, successful_refunds_by_item.get(item[0], money(0)))
            completed_returns[item[0]] = completed_after
        elif status == "APPROVED":
            refund_amount = refund_amount_for_completed_return(item[21], item[4], completed_before, completed_after, successful_refunds_by_item.get(item[0], money(0)))
        else:
            refund_amount = None
        return_rows.append((index, f"RET-{index:03d}", f"REQ-RET-{index:03d}", order_pk, item[0], status, quantity, "defective", refund_amount, "CNY", timestamp(day, 10), timestamp(day, 10, 10) if status in {"COMPLETED", "APPROVED"} else None, timestamp(day, 10, 10) if status == "REJECTED" else None, timestamp(day, 10, 20) if status == "COMPLETED" else None, "outside policy" if status == "REJECTED" else None, timestamp(day, 10), timestamp(day, 10, 20) if status == "COMPLETED" else timestamp(day, 10, 10)))
        if status == "COMPLETED":
            assert_refund_limit(refund_amount, successful_refunds_by_item.get(item[0], money(0)), item[21])
            assert_refund_limit(refund_amount, successful_refunds_by_order.get(order_pk, money(0)), order_rows[order_pk - 1][12])
            successful_refunds_by_item[item[0]] = money(successful_refunds_by_item.get(item[0], money(0)) + refund_amount)
            successful_refunds_by_order[order_pk] = money(successful_refunds_by_order.get(order_pk, money(0)) + refund_amount)
            refund_rows.append((len(refund_rows) + 1, f"REF-{len(refund_rows) + 1:03d}", f"REQ-REF-{len(refund_rows) + 1:03d}", index, order_pk, order_pk, "SUCCESS", refund_amount, "CNY", timestamp(day, 10, 15), timestamp(day, 10, 20), None, f"CALLBACK-REF-{len(refund_rows) + 1:03d}", None, timestamp(day, 10, 15), timestamp(day, 10, 20)))
    while len(refund_rows) < 5 * scale:
        index = len(refund_rows) + 1
        day = business_days[(index - 1) % len(business_days)]
        refund_rows.append((index, f"REF-{index:03d}", f"REQ-REF-{index:03d}", 1, 1, 1, "FAILED", money(1), "CNY", timestamp(day, 11), None, timestamp(day, 11, 1), f"CALLBACK-REF-{index:03d}", "retry", timestamp(day, 11), timestamp(day, 11, 1)))

    transitions = {"PAID": {"PARTIALLY_REFUNDED", "REFUNDED"}}
    validate_payment_rows(order_rows, payment_rows)
    validate_coupon_rows(coupon_rows, user_coupon_rows, order_rows)
    for order_pk, refunded_amount in successful_refunds_by_order.items():
        row = list(order_rows[order_pk - 1])
        refund_status = "REFUNDED" if refunded_amount == row[12] else "PARTIALLY_REFUNDED"
        assert_transition(row[6], refund_status, transitions)
        row[6] = refund_status
        row[18] = max(refund[10] for refund in refund_rows if refund[4] == order_pk and refund[6] == "SUCCESS")
        order_rows[order_pk - 1] = tuple(row)

    statements = [
        "-- Candidate M2.4 generated SQL. Do not execute before T7/M1 MySQL gate.\n",
        f"-- Parameters: seed={seed}; start_date={start_date.isoformat()}; days={days}; scale={scale}.\n",
        "START TRANSACTION;\n",
        insert("user_account", ["user_account_pk", "user_id", "registered_at", "is_deleted", "deleted_at", "create_time", "update_time"], user_rows),
        insert("visitor", ["visitor_pk", "visitor_id", "first_seen_at", "last_seen_at", "is_deleted", "deleted_at", "create_time", "update_time"], visitor_rows),
        insert("traffic_channel", ["traffic_channel_pk", "channel_code", "channel_name", "is_deleted", "deleted_at", "create_time", "update_time"], channel_rows),
        insert("brand", ["brand_pk", "brand_id", "brand_name", "is_deleted", "deleted_at", "create_time", "update_time"], brand_rows),
        insert("category", ["category_pk", "category_id", "category_name", "parent_category_pk", "category_level", "is_deleted", "deleted_at", "create_time", "update_time"], category_rows),
        insert("coupon", ["coupon_pk", "coupon_id", "coupon_name", "discount_amount", "minimum_original_amount", "valid_from", "valid_to", "is_deleted", "deleted_at", "create_time", "update_time"], coupon_rows),
        insert("user_address", ["user_address_pk", "address_id", "user_pk", "province_code", "province_name", "city_code", "city_name", "detail_address", "is_deleted", "deleted_at", "create_time", "update_time"], address_rows),
        insert("visit_session", ["visit_session_pk", "session_id", "visitor_pk", "first_channel_pk", "started_at", "last_event_at", "ended_at", "create_time", "update_time"], session_rows),
        insert("spu", ["spu_pk", "spu_id", "spu_name", "brand_pk", "category_pk", "is_deleted", "deleted_at", "create_time", "update_time"], spu_rows),
        insert("sku", ["sku_pk", "sku_id", "sku_name", "spu_pk", "sale_price", "currency", "is_deleted", "deleted_at", "create_time", "update_time"], sku_rows),
        insert("user_coupon", ["user_coupon_pk", "user_coupon_no", "request_id", "coupon_pk", "user_pk", "coupon_status", "discount_amount_snapshot", "minimum_original_amount_snapshot", "valid_from", "valid_to", "claimed_at", "locked_at", "released_at", "used_at", "expired_at", "create_time", "update_time"], user_coupon_rows),
        insert("login_event", ["login_event_pk", "login_event_id", "visitor_pk", "session_pk", "user_pk", "login_at", "create_time"], login_rows),
        insert("page_view_event", ["page_view_event_pk", "page_view_id", "visitor_pk", "session_pk", "user_pk", "channel_pk", "page_type", "page_path", "sku_pk", "event_time", "create_time"], page_rows),
        insert("cart_event", ["cart_event_pk", "cart_event_id", "request_id", "visitor_pk", "session_pk", "user_pk", "sku_pk", "action_type", "quantity_before", "quantity_after", "is_valid", "invalid_reason", "action_time", "create_time"], cart_rows),
        insert("sales_order", ["sales_order_pk", "order_no", "request_id", "user_pk", "user_address_pk", "user_coupon_pk", "order_status", "province_code", "province_name", "original_amount", "product_discount_amount", "coupon_discount_amount", "payable_amount", "currency", "ordered_at", "cancelled_at", "cancel_reason", "create_time", "update_time"], order_rows),
        insert("sales_order_item", ["sales_order_item_pk", "order_item_no", "order_pk", "sku_pk", "quantity", "brand_id_snapshot", "brand_name_snapshot", "category_level1_id_snapshot", "category_level1_name_snapshot", "category_level2_id_snapshot", "category_level2_name_snapshot", "category_level3_id_snapshot", "category_level3_name_snapshot", "spu_id_snapshot", "spu_name_snapshot", "sku_id_snapshot", "sku_name_snapshot", "unit_original_price", "original_amount", "product_discount_amount", "coupon_discount_amount", "payable_amount", "currency", "create_time"], item_rows),
        insert("payment_attempt", ["payment_attempt_pk", "payment_no", "request_id", "order_pk", "payment_status", "payment_amount", "currency", "attempted_at", "paid_at", "failed_at", "callback_request_id", "failure_reason", "create_time", "update_time"], payment_rows),
        insert("return_order", ["return_order_pk", "return_no", "request_id", "order_pk", "order_item_pk", "return_status", "return_quantity", "return_reason", "refund_amount", "currency", "applied_at", "approved_at", "rejected_at", "completed_at", "reject_reason", "create_time", "update_time"], return_rows),
        insert("refund_attempt", ["refund_attempt_pk", "refund_no", "request_id", "return_order_pk", "order_pk", "payment_attempt_pk", "refund_status", "refund_amount", "currency", "attempted_at", "refunded_at", "failed_at", "callback_request_id", "failure_reason", "create_time", "update_time"], refund_rows),
        "COMMIT;\n",
    ]
    return "\n".join(statements)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", required=True, type=non_negative_int)
    parser.add_argument("--start-date", required=True, type=parse_date)
    parser.add_argument("--days", required=True, type=positive_int)
    parser.add_argument("--scale", required=True, type=positive_int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        sql = build_sql(args.seed, args.start_date, args.days, args.scale)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(sql, encoding="utf-8", newline="\n")
    except (OSError, RuleViolation, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
