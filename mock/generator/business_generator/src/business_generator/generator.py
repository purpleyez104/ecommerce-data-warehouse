"""Standalone Business Generator: deterministic V2 bootstrap CSVs for 21 tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from . import __version__
from .common import allocate, canonical_json, dt, long_tail_weights, stable_rng, weighted_time
from .config import DatasetConfig, load_config
from .contracts import TABLE_COLUMNS, TABLE_ORDER


class CsvBundle:
    def __init__(self, output: Path):
        self.output = output
        self.files = {}
        self.writers = {}
        self.counts = Counter()
        for table in TABLE_ORDER:
            handle = (output / f"{table}.csv").open("w", encoding="utf-8", newline="")
            writer = csv.DictWriter(handle, fieldnames=TABLE_COLUMNS[table], extrasaction="raise")
            writer.writeheader()
            self.files[table] = handle
            self.writers[table] = writer

    def write(self, table: str, row: dict) -> None:
        missing = set(TABLE_COLUMNS[table]) - row.keys()
        if missing:
            raise ValueError(f"{table} row missing columns: {sorted(missing)}")
        self.writers[table].writerow(row)
        self.counts[table] += 1

    def close(self) -> None:
        for handle in self.files.values():
            handle.close()


def _prepare_output(output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"output already exists; choose a new directory: {output}")
    output.mkdir(parents=True)


def _exact_item_counts(order_count: int, item_total: int, rng) -> list[int]:
    if not order_count <= item_total <= order_count * 5:
        raise ValueError("order_item count must be between order_count and 5 * order_count")
    expected = allocate(order_count, [15, 25, 30, 20, 10])
    counts = [value for size, number in enumerate(expected, start=1) for value in [size] * number]
    rng.shuffle(counts)
    delta = item_total - sum(counts)
    while delta:
        indexes = [i for i, value in enumerate(counts) if (value < 5 if delta > 0 else value > 1)]
        index = rng.choice(indexes)
        counts[index] += 1 if delta > 0 else -1
        delta += -1 if delta > 0 else 1
    return counts


def _status_plan(order_count: int, rng) -> list[str]:
    paid, canceled, created = allocate(order_count, [70, 29, 1])
    statuses = ["PAID"] * paid + ["CANCELED"] * canceled + ["CREATED"] * created
    rng.shuffle(statuses)
    return statuses


def _payment_plan(statuses: list[str], target: int, rng) -> dict[int, list[str]]:
    groups = {name: [i + 1 for i, status in enumerate(statuses) if status == name] for name in ("PAID", "CANCELED", "CREATED")}
    plan: dict[int, list[str]] = {}
    paid_retry = round(len(groups["PAID"]) * 0.15)
    retry_ids = set(rng.sample(groups["PAID"], paid_retry))
    for order_id in groups["PAID"]:
        plan[order_id] = ["FAILED", "SUCCESS"] if order_id in retry_ids else ["SUCCESS"]
    canceled = groups["CANCELED"][:]
    rng.shuffle(canceled)
    no_attempt, one_failed, _ = allocate(len(canceled), [55, 40, 5])
    for index, order_id in enumerate(canceled):
        plan[order_id] = [] if index < no_attempt else (["FAILED"] if index < no_attempt + one_failed else ["FAILED", "FAILED"])
    created = groups["CREATED"][:]
    rng.shuffle(created)
    init_count = round(len(created) * 0.30)
    for index, order_id in enumerate(created):
        plan[order_id] = ["INIT"] if index < init_count else []
    current = sum(map(len, plan.values()))
    if current > target:
        raise ValueError(f"payment target {target} is below rule-derived minimum {current}")
    expandable = [order_id for order_id in canceled if len(plan[order_id]) < 2] + [order_id for order_id in created if not plan[order_id]]
    for order_id in expandable[: target - current]:
        plan[order_id] = ["FAILED"] if statuses[order_id - 1] == "CANCELED" else ["INIT"]
    if sum(map(len, plan.values())) != target:
        raise ValueError("payment target cannot be reached without violating the two-attempt boundary")
    return plan


def generate(config: DatasetConfig, seed: int, generated_at: str, output: Path) -> dict:
    _prepare_output(output)
    rng = stable_rng(seed, "business-bootstrap")
    counts = config.counts
    promotions = set(config.raw["promotion_dates"])
    bundle = CsvBundle(output)
    stats = Counter()
    daily_orders = Counter()
    hourly_orders = Counter()
    sku_sales = Counter()
    user_orders = Counter()
    user_registered_at = {}
    visitor_first_seen_at = {}
    identity_mappings = []
    try:
        # Users and visitors.
        recorded_time_ceiling = config.end - timedelta(milliseconds=100)
        for user_id in range(1, counts["biz_user"] + 1):
            registered = config.start if user_id == 1 else weighted_time(rng, config.start, recorded_time_ceiling, promotions)
            user_registered_at[user_id] = registered
            bundle.write("biz_user", {"user_id": user_id, "user_key": f"USR-{user_id:010d}", "user_name": f"user_{user_id:010d}", "user_status": "DISABLED" if user_id % 100 == 0 else "ACTIVE", "registered_at": dt(registered), "created_at": dt(registered), "updated_at": dt(registered)})
        for visitor_id in range(1, counts["biz_visitor"] + 1):
            first_seen = config.start if visitor_id == 1 else weighted_time(rng, config.start, recorded_time_ceiling, promotions)
            last_seen = first_seen + timedelta(seconds=rng.randrange(max(1, int((config.end - first_seen).total_seconds()) + 1)))
            visitor_first_seen_at[visitor_id] = first_seen
            bundle.write("biz_visitor", {"visitor_id": visitor_id, "visitor_key": f"VIS-{visitor_id:010d}", "first_seen_at": dt(first_seen), "last_seen_at": dt(last_seen), "created_at": dt(first_seen), "updated_at": dt(last_seen)})
        for mapping_id in range(1, counts["biz_identity_mapping"] + 1):
            user_id = ((mapping_id - 1) % counts["biz_user"]) + 1
            effective_start = max(visitor_first_seen_at[mapping_id], user_registered_at[user_id])
            effective = weighted_time(rng, effective_start, recorded_time_ceiling, promotions)
            mapping = {"mapping_id": mapping_id, "visitor_id": mapping_id, "user_id": user_id, "session_id": f"SES-MAP-{mapping_id:010d}", "evidence_type": "LOGIN", "evidence_id": f"LOGIN-{mapping_id:010d}", "mapping_scope": "VISITOR", "identity_version": 1, "effective_from": dt(effective), "effective_to": "", "mapping_status": "CONFIRMED", "recorded_at": dt(effective + timedelta(milliseconds=50))}
            identity_mappings.append(mapping)
            bundle.write("biz_identity_mapping", mapping)

        # Product catalog and true SKU history.
        for category_id in range(1, counts["biz_category"] + 1):
            bundle.write("biz_category", {"category_id": category_id, "category_code": f"CAT-{category_id:04d}", "category_name": f"category_{category_id:04d}", "category_status": "ACTIVE", "created_at": dt(config.start), "updated_at": dt(config.start)})
        for spu_id in range(1, counts["biz_spu"] + 1):
            category_id = ((spu_id - 1) % counts["biz_category"]) + 1
            brand = ((spu_id - 1) % 120) + 1
            bundle.write("biz_spu", {"spu_id": spu_id, "spu_code": f"SPU-{spu_id:06d}", "category_id": category_id, "brand_code": f"BR-{brand:04d}", "brand_name": f"brand_{brand:04d}", "spu_name": f"spu_{spu_id:06d}", "spu_status": "ACTIVE", "created_at": dt(config.start), "updated_at": dt(config.start)})
        changed_skus = max(1, min(counts["biz_sku"], round(counts["biz_sku"] * 0.25)))
        change_counts = [1] * changed_skus
        remaining_changes = max(0, min(counts["biz_product_change_event"] - changed_skus, changed_skus * 2))
        for index in rng.sample(range(changed_skus), remaining_changes // 2):
            change_counts[index] += 1
        for index in rng.sample(range(changed_skus), remaining_changes - remaining_changes // 2):
            if change_counts[index] < 3:
                change_counts[index] += 1
        change_id = 0
        sku_prices = {}
        for sku_id in range(1, counts["biz_sku"] + 1):
            spu_id = ((sku_id - 1) % counts["biz_spu"]) + 1
            base_price = 900 + ((sku_id * 7919) % 49_100)
            event_total = change_counts[sku_id - 1] if sku_id <= changed_skus else 0
            price = base_price + event_total * 100
            sku_prices[sku_id] = price
            updated = config.start
            for version in range(event_total):
                change_id += 1
                effective = config.start + (config.end - config.start) * ((version + 1) / (event_total + 1))
                before = base_price + version * 100
                after = before + 100
                updated = effective
                bundle.write("biz_product_change_event", {"change_id": change_id, "event_key": f"PCE-{change_id:012d}", "target_type": "SKU", "target_id": sku_id, "change_type": "PRICE", "before_data": canonical_json({"sale_price_cents": before}), "after_data": canonical_json({"sale_price_cents": after}), "effective_at": dt(effective), "recorded_at": dt(effective + timedelta(milliseconds=100))})
            bundle.write("biz_sku", {"sku_id": sku_id, "sku_code": f"SKU-{sku_id:07d}", "spu_id": spu_id, "sku_name": f"sku_{sku_id:07d}", "sale_price_cents": price, "sku_status": "OFF_SALE" if sku_id % 50 == 0 else "ON_SALE", "created_at": dt(config.start), "updated_at": dt(updated)})
        if change_id != counts["biz_product_change_event"]:
            # Approximate table target yields to the 20%-30%, one-to-three-change SCD2 contract.
            counts = dict(counts)
            counts["biz_product_change_event"] = change_id

        # Current carts and idempotent merge history.
        user_cart_count = min(counts["biz_cart"], counts["biz_user"])
        for cart_id in range(1, counts["biz_cart"] + 1):
            is_user = cart_id <= user_cart_count
            visitor_id = "" if is_user else ((cart_id - user_cart_count - 1) % counts["biz_visitor"]) + 1
            owner_start = user_registered_at[cart_id] if is_user else visitor_first_seen_at[visitor_id]
            created = weighted_time(rng, owner_start, config.end, promotions)
            updated = min(config.end, created + timedelta(minutes=rng.randrange(1440)))
            bundle.write("biz_cart", {"cart_id": cart_id, "user_id": cart_id if is_user else "", "visitor_id": visitor_id, "created_at": dt(created), "updated_at": dt(updated)})
        per_cart = [counts["biz_cart_item"] // counts["biz_cart"]] * counts["biz_cart"]
        for index in range(counts["biz_cart_item"] % counts["biz_cart"]):
            per_cart[index] += 1
        cart_item_id = 0
        for cart_id, item_total in enumerate(per_cart, start=1):
            for offset in range(item_total):
                cart_item_id += 1
                created = weighted_time(rng, config.start, config.end, promotions)
                bundle.write("biz_cart_item", {"cart_item_id": cart_item_id, "cart_id": cart_id, "sku_id": ((cart_id * 17 + offset) % counts["biz_sku"]) + 1, "quantity": 99 if cart_item_id % 5000 == 0 else rng.randint(1, 5), "created_at": dt(created), "updated_at": dt(created)})
        for merge_id in range(1, counts["biz_cart_merge_record"] + 1):
            user_id = ((merge_id - 1) % user_cart_count) + 1
            visitor_cart_id = user_cart_count + ((merge_id - 1) % max(1, counts["biz_cart"] - user_cart_count)) + 1
            merged = weighted_time(rng, config.start, config.end, promotions)
            truncated = 4 if merge_id % 100 == 0 else 0
            bundle.write("biz_cart_merge_record", {"merge_id": merge_id, "operation_id": f"MERGE-{merge_id:010d}", "visitor_cart_id": visitor_cart_id, "user_cart_id": user_id, "user_id": user_id, "merge_detail": canonical_json({"sku_id": (merge_id % counts["biz_sku"]) + 1, "truncated": truncated > 0}), "truncated_quantity": truncated, "merged_at": dt(merged)})

        # Coupon templates are independent; instances are finalized after order assignment.
        for template_id in range(1, counts["biz_coupon_template"] + 1):
            face = [500, 1000, 2000][(template_id - 1) % 3]
            bundle.write("biz_coupon_template", {"template_id": template_id, "template_code": f"TPL-{template_id:04d}", "template_name": f"coupon_{face}", "face_value_cents": face, "min_spend_cents": face * 5, "valid_from": dt(config.start), "valid_to": dt(config.end), "issue_limit": math.ceil(counts["biz_coupon"] / counts["biz_coupon_template"]), "template_status": "ACTIVE", "created_at": dt(config.start), "updated_at": dt(config.start)})

        statuses = _status_plan(counts["biz_order"], rng)
        item_counts = _exact_item_counts(counts["biz_order"], counts["biz_order_item"], rng)
        payment_plan = _payment_plan(statuses, counts["biz_payment_attempt"], rng)
        paid_ids = [i + 1 for i, status in enumerate(statuses) if status == "PAID"]
        refund_order_target = min(len(paid_ids), round(counts["biz_refund_request"] * 8 / 9))
        refund_counts = {order_id: 1 for order_id in paid_ids[:refund_order_target]}
        extra_refunds = counts["biz_refund_request"] - refund_order_target
        for order_id in [oid for oid in paid_ids[:refund_order_target] if item_counts[oid - 1] > 1][:extra_refunds]:
            refund_counts[order_id] = 2
        if sum(refund_counts.values()) != counts["biz_refund_request"]:
            raise ValueError("refund_request target requires enough paid orders with multiple items")
        refund_statuses = [name for name, total in zip(("SUCCESS", "FAILED", "PROCESSING", "REQUESTED"), allocate(counts["biz_refund_request"], [80, 15, 3, 2])) for _ in range(total)]
        rng.shuffle(refund_statuses)
        coupon_order_total = min(counts["biz_coupon"], round(counts["biz_order"] * 0.30))
        coupon_order_ids = set(rng.sample(range(1, counts["biz_order"] + 1), coupon_order_total))
        coupon_for_order = {order_id: index + 1 for index, order_id in enumerate(sorted(coupon_order_ids))}
        sku_weights = long_tail_weights(counts["biz_sku"])
        refund_meta = []
        payment_attempt_id = payment_event_id = order_item_id = order_event_id = 0
        coupon_state_by_id = {}
        regular_order_end = config.end - timedelta(hours=1, minutes=15)
        refund_order_end = config.end - timedelta(hours=3)
        regular_order_users = [user_id for user_id, registered in user_registered_at.items() if registered <= regular_order_end]
        refund_order_users = [user_id for user_id, registered in user_registered_at.items() if registered <= refund_order_end]
        if not regular_order_users or not refund_order_users:
            raise ValueError("history range does not leave eligible registered users for order lifecycles")
        for order_id in range(1, counts["biz_order"] + 1):
            status = statuses[order_id - 1]
            has_refund = order_id in refund_counts
            eligible_users = refund_order_users if has_refund else regular_order_users
            order_end = refund_order_end if has_refund else regular_order_end
            user_id = rng.choice(eligible_users)
            created = weighted_time(rng, user_registered_at[user_id], order_end, promotions)
            deadline = created + timedelta(minutes=15)
            user_orders[user_id] += 1
            selected = []
            while len(selected) < item_counts[order_id - 1]:
                sku_id = rng.choices(range(1, counts["biz_sku"] + 1), weights=sku_weights, k=1)[0]
                if sku_id not in selected:
                    selected.append(sku_id)
            quantities = [rng.randint(1, 3) for _ in selected]
            gross_values = [sku_prices[sku_id] * quantity for sku_id, quantity in zip(selected, quantities)]
            gross = sum(gross_values)
            coupon_id = coupon_for_order.get(order_id)
            discount = min([500, 1000, 2000][(coupon_id - 1) % 3], gross - 1) if coupon_id else 0
            allocations = [(discount * value) // gross for value in gross_values]
            for index in range(discount - sum(allocations)):
                allocations[index % len(allocations)] += 1
            attempts = payment_plan[order_id]
            paid_at = created + timedelta(seconds=rng.randrange(60 * len(attempts) + 1, 14 * 60)) if status == "PAID" else None
            canceled_at = created + timedelta(minutes=15, seconds=rng.randrange(3600)) if status == "CANCELED" else None
            updated = paid_at or canceled_at or created
            bundle.write("biz_order", {"order_id": order_id, "order_no": f"ORD-{order_id:012d}", "user_id": user_id, "visitor_id": "", "coupon_id": coupon_id or "", "order_status": status, "gross_amount_cents": gross, "discount_amount_cents": discount, "payable_amount_cents": gross - discount, "created_at": dt(created), "payment_deadline_at": dt(deadline), "paid_at": dt(paid_at), "canceled_at": dt(canceled_at), "updated_at": dt(updated)})
            daily_orders[created.date().isoformat()] += 1
            hourly_orders[created.hour] += 1
            stats[f"{status.lower()}_orders"] += 1
            order_event_id += 1
            bundle.write("biz_order_status_event", {"order_event_id": order_event_id, "event_key": f"OE-{order_event_id:012d}", "order_id": order_id, "event_type": "CREATE", "from_status": "", "to_status": "CREATED", "occurred_at": dt(created), "recorded_at": dt(created + timedelta(milliseconds=100))})
            if status != "CREATED":
                order_event_id += 1
                bundle.write("biz_order_status_event", {"order_event_id": order_event_id, "event_key": f"OE-{order_event_id:012d}", "order_id": order_id, "event_type": "PAY" if status == "PAID" else "CANCEL", "from_status": "CREATED", "to_status": status, "occurred_at": dt(updated), "recorded_at": dt(updated + timedelta(milliseconds=100))})
            order_item_rows = []
            for sku_id, quantity, item_gross, allocated in zip(selected, quantities, gross_values, allocations):
                order_item_id += 1
                spu_id = ((sku_id - 1) % counts["biz_spu"]) + 1
                category_id = ((spu_id - 1) % counts["biz_category"]) + 1
                order_item_rows.append({"order_item_id": order_item_id, "order_id": order_id, "sku_id": sku_id, "spu_id": spu_id, "category_id": category_id, "brand_code": f"BR-{((spu_id - 1) % 120) + 1:04d}", "sku_name": f"sku_{sku_id:07d}", "quantity": quantity, "unit_price_cents": sku_prices[sku_id], "gross_amount_cents": item_gross, "allocated_discount_cents": allocated, "payable_amount_cents": item_gross - allocated, "refund_reserved_cents": 0, "refunded_cents": 0, "refunded_quantity": 0, "created_at": dt(created), "updated_at": dt(created)})
                if status == "PAID":
                    sku_sales[sku_id] += quantity
            for refund_index in range(refund_counts.get(order_id, 0)):
                row = order_item_rows[refund_index]
                request_number = len(refund_meta) + 1
                refund_status = refund_statuses[request_number - 1]
                refund_amount = max(1, row["payable_amount_cents"] // (2 if request_number % 3 == 0 else 1))
                refund_quantity = "" if request_number % 10 == 0 else min(row["quantity"], 1)
                if refund_status == "SUCCESS":
                    row["refunded_cents"] = refund_amount
                    row["refunded_quantity"] = refund_quantity or 0
                elif refund_status in {"REQUESTED", "PROCESSING"}:
                    row["refund_reserved_cents"] = refund_amount
                requested = min(config.end - timedelta(hours=2), paid_at + timedelta(days=1 + request_number % 20))
                completed = requested + timedelta(hours=2) if refund_status in {"SUCCESS", "FAILED"} else None
                row["updated_at"] = dt(completed or requested)
                refund_meta.append((order_id, row, paid_at, refund_status, refund_amount, refund_quantity, requested, completed))
            for row in order_item_rows:
                bundle.write("biz_order_item", row)
            for attempt_no, attempt_status in enumerate(attempts, start=1):
                payment_attempt_id += 1
                initiated = created + timedelta(seconds=min(60 * attempt_no, 12 * 60))
                succeeded = paid_at if attempt_status == "SUCCESS" else None
                bundle.write("biz_payment_attempt", {"payment_attempt_id": payment_attempt_id, "order_id": order_id, "attempt_no": attempt_no, "funding_txn_id": f"PAY-{payment_attempt_id:012d}", "amount_cents": gross - discount, "payment_status": attempt_status, "initiated_at": dt(initiated), "succeeded_at": dt(succeeded), "created_at": dt(initiated), "updated_at": dt(succeeded or initiated + timedelta(seconds=10))})
                payment_event_id += 1
                bundle.write("biz_payment_event", {"payment_event_id": payment_event_id, "event_key": f"PE-{payment_event_id:012d}", "payment_attempt_id": payment_attempt_id, "callback_event_id": f"PCB-{payment_event_id:012d}" if attempt_status != "INIT" else "", "from_status": "INIT", "to_status": attempt_status, "occurred_at": dt(succeeded or initiated + timedelta(seconds=10)), "recorded_at": dt((succeeded or initiated + timedelta(seconds=10)) + timedelta(milliseconds=100))})
                stats[f"payment_{attempt_status.lower()}"] += 1
            if len(attempts) == 2 and attempts[-1] == "SUCCESS":
                stats["retry_payment_orders"] += 1
            if coupon_id:
                if status == "PAID":
                    coupon_state_by_id[coupon_id] = ("USED", order_id, user_id, created, paid_at)
                elif status == "CREATED":
                    coupon_state_by_id[coupon_id] = ("LOCKED", order_id, user_id, created, None)
                else:
                    coupon_state_by_id[coupon_id] = ("UNUSED", order_id, user_id, created, canceled_at)

        # Refund current state and immutable history.
        natural_txns = sum(2 if status == "SUCCESS" and index < round(refund_statuses.count("SUCCESS") * 0.10) else (1 if status != "REQUESTED" else 0) for index, status in enumerate(refund_statuses))
        extra_txns = counts["biz_refund_transaction"] - natural_txns
        if extra_txns < 0:
            raise ValueError("refund_transaction target is below rule-derived count")
        refund_txn_id = refund_event_id = 0
        for request_id, (order_id, item, paid_at, status, amount, quantity, requested, completed) in enumerate(refund_meta, start=1):
            retry = status == "SUCCESS" and request_id <= round(refund_statuses.count("SUCCESS") * 0.10)
            txn_statuses = (["FAILED", "SUCCESS"] if retry else ([status] if status in {"SUCCESS", "FAILED"} else (["INIT"] if status == "PROCESSING" else [])))
            if extra_txns > 0 and status == "SUCCESS" and not retry:
                txn_statuses.insert(0, "FAILED")
                extra_txns -= 1
            bundle.write("biz_refund_request", {"refund_request_id": request_id, "refund_request_no": f"RR-{request_id:012d}", "order_id": order_id, "order_item_id": item["order_item_id"], "requested_amount_cents": amount, "refund_quantity": quantity, "refund_status": status, "requested_at": dt(requested), "completed_at": dt(completed), "created_at": dt(requested), "updated_at": dt(completed or requested)})
            refund_event_id += 1
            bundle.write("biz_refund_event", {"refund_event_id": refund_event_id, "event_key": f"RE-{refund_event_id:012d}", "refund_request_id": request_id, "refund_txn_id": "", "event_type": "REQUEST", "from_status": "", "to_status": "REQUESTED", "occurred_at": dt(requested), "recorded_at": dt(requested + timedelta(milliseconds=100))})
            if txn_statuses:
                refund_event_id += 1
                bundle.write("biz_refund_event", {"refund_event_id": refund_event_id, "event_key": f"RE-{refund_event_id:012d}", "refund_request_id": request_id, "refund_txn_id": "", "event_type": "PROCESS", "from_status": "REQUESTED", "to_status": "PROCESSING", "occurred_at": dt(requested + timedelta(minutes=5)), "recorded_at": dt(requested + timedelta(minutes=5, milliseconds=100))})
            for attempt_no, txn_status in enumerate(txn_statuses, start=1):
                refund_txn_id += 1
                initiated = requested + timedelta(minutes=5 * attempt_no)
                succeeded = initiated + timedelta(seconds=30) if txn_status == "SUCCESS" else None
                bundle.write("biz_refund_transaction", {"refund_txn_id": refund_txn_id, "refund_request_id": request_id, "attempt_no": attempt_no, "funding_refund_txn_id": f"RFT-{refund_txn_id:012d}", "refund_amount_cents": amount, "refund_txn_status": txn_status, "initiated_at": dt(initiated), "succeeded_at": dt(succeeded), "created_at": dt(initiated), "updated_at": dt(succeeded or initiated + timedelta(seconds=30))})
                # INIT and retryable failures are funding-attempt states; only
                # the request's final SUCCESS/FAILED state advances its lifecycle.
                if txn_status == "SUCCESS" or (txn_status == "FAILED" and status == "FAILED"):
                    refund_event_id += 1
                    bundle.write("biz_refund_event", {"refund_event_id": refund_event_id, "event_key": f"RE-{refund_event_id:012d}", "refund_request_id": request_id, "refund_txn_id": refund_txn_id, "event_type": "SUCCESS" if txn_status == "SUCCESS" else "FAIL", "from_status": "PROCESSING", "to_status": txn_status, "occurred_at": dt(succeeded or initiated + timedelta(seconds=30)), "recorded_at": dt((succeeded or initiated + timedelta(seconds=30)) + timedelta(milliseconds=100))})
            stats[f"refund_{status.lower()}"] += 1
        if refund_txn_id != counts["biz_refund_transaction"]:
            raise ValueError("refund transaction target is inconsistent")
        if refund_event_id != counts["biz_refund_event"]:
            counts = dict(counts)
            counts["biz_refund_event"] = refund_event_id

        # Coupon instance current state and lifecycle events.
        coupon_event_id = 0
        expiring_unused = min(10_000, counts["biz_coupon"] - len(coupon_state_by_id))
        for coupon_id in range(1, counts["biz_coupon"] + 1):
            state = coupon_state_by_id.get(coupon_id)
            if state:
                status, order_id, user_id, locked_at, final_at = state
                issued = max(config.start, locked_at - timedelta(days=1 + coupon_id % 20))
                used_at = final_at if status == "USED" else None
                locked_order_id = order_id if status == "LOCKED" else ""
                used_order_id = order_id if status == "USED" else ""
            elif coupon_id <= len(coupon_state_by_id) + expiring_unused:
                issued = weighted_time(rng, config.start, max(config.start, config.end - timedelta(days=1)), promotions)
                user_id = ((coupon_id - 1) % counts["biz_user"]) + 1
                status, order_id, locked_at, used_at, locked_order_id, used_order_id = "EXPIRED", "", None, None, "", ""
            else:
                issued = weighted_time(rng, config.start, recorded_time_ceiling, promotions)
                user_id = ((coupon_id - 1) % counts["biz_user"]) + 1
                status, order_id, locked_at, used_at, locked_order_id, used_order_id = "UNUSED", "", None, None, "", ""
            expires = min(config.end if status == "EXPIRED" else config.end + timedelta(days=30), issued + timedelta(days=30))
            updated = final_at if state and final_at else (locked_at if state else (expires if status == "EXPIRED" else issued))
            bundle.write("biz_coupon", {"coupon_id": coupon_id, "coupon_code": f"CPN-{coupon_id:012d}", "template_id": ((coupon_id - 1) % counts["biz_coupon_template"]) + 1, "user_id": user_id, "coupon_status": status, "locked_order_id": locked_order_id, "used_order_id": used_order_id, "issued_at": dt(issued), "expires_at": dt(expires), "locked_at": dt(locked_at) if status == "LOCKED" else "", "used_at": dt(used_at), "updated_at": dt(updated)})
            coupon_event_id += 1
            bundle.write("biz_coupon_event", {"coupon_event_id": coupon_event_id, "event_key": f"CE-{coupon_event_id:012d}", "coupon_id": coupon_id, "order_id": "", "event_type": "ISSUE", "from_status": "", "to_status": "UNUSED", "occurred_at": dt(issued), "recorded_at": dt(issued + timedelta(milliseconds=100))})
            if state:
                coupon_event_id += 1
                bundle.write("biz_coupon_event", {"coupon_event_id": coupon_event_id, "event_key": f"CE-{coupon_event_id:012d}", "coupon_id": coupon_id, "order_id": order_id, "event_type": "LOCK", "from_status": "UNUSED", "to_status": "LOCKED", "occurred_at": dt(locked_at), "recorded_at": dt(locked_at + timedelta(milliseconds=100))})
                if status != "LOCKED":
                    coupon_event_id += 1
                    bundle.write("biz_coupon_event", {"coupon_event_id": coupon_event_id, "event_key": f"CE-{coupon_event_id:012d}", "coupon_id": coupon_id, "order_id": order_id, "event_type": "USE" if status == "USED" else "UNLOCK", "from_status": "LOCKED", "to_status": status, "occurred_at": dt(final_at), "recorded_at": dt(final_at + timedelta(milliseconds=100))})
            elif status == "EXPIRED":
                coupon_event_id += 1
                bundle.write("biz_coupon_event", {"coupon_event_id": coupon_event_id, "event_key": f"CE-{coupon_event_id:012d}", "coupon_id": coupon_id, "order_id": "", "event_type": "EXPIRE", "from_status": "UNUSED", "to_status": "EXPIRED", "occurred_at": dt(expires), "recorded_at": dt(expires)})
            stats[f"coupon_{status.lower()}"] += 1
        if coupon_event_id != counts["biz_coupon_event"]:
            counts = dict(counts)
            counts["biz_coupon_event"] = coupon_event_id
    except Exception:
        bundle.close()
        shutil.rmtree(output)
        raise
    bundle.close()

    for table in TABLE_ORDER:
        expected = counts[table]
        if bundle.counts[table] != expected:
            shutil.rmtree(output)
            raise AssertionError(f"{table}: expected {expected}, generated {bundle.counts[table]}")
    sales_total = sum(sku_sales.values()) or 1
    ranked = sorted(sku_sales.values(), reverse=True)
    top5 = max(1, math.ceil(counts["biz_sku"] * 0.05))
    top20 = max(1, math.ceil(counts["biz_sku"] * 0.20))
    active_users = sum(1 for value in user_orders.values() if value)
    entity_manifest = {
        "entity_manifest_version": 1,
        "dataset_version": config.raw["dataset_version"],
        "source_generator_version": __version__,
        "seed": seed,
        "history_start": config.raw["history_start"],
        "history_end": config.raw["history_end"],
        "timezone": config.raw["timezone"],
        "entities": {
            "users": [{"user_id": user_id, "registered_at": dt(registered_at)} for user_id, registered_at in user_registered_at.items()],
            "visitors": [{"visitor_id": visitor_id, "first_seen_at": dt(first_seen_at)} for visitor_id, first_seen_at in visitor_first_seen_at.items()],
            "identity_mappings": [
                {
                    "visitor_id": row["visitor_id"],
                    "user_id": row["user_id"],
                    "session_id": row["session_id"],
                    "identity_version": row["identity_version"],
                    "effective_from": row["effective_from"],
                    "effective_to": row["effective_to"] or None,
                }
                for row in identity_mappings
            ],
            "skus": [
                {
                    "sku_id": sku_id,
                    "spu_id": ((sku_id - 1) % counts["biz_spu"]) + 1,
                    "category_id": ((((sku_id - 1) % counts["biz_spu"]) + 1) - 1) % counts["biz_category"] + 1,
                    "available_from": dt(config.start),
                }
                for sku_id in range(1, counts["biz_sku"] + 1)
            ],
        },
    }
    entity_manifest_path = output / "entity_manifest.json"
    entity_manifest_path.write_text(canonical_json(entity_manifest) + "\n", encoding="utf-8", newline="\n")
    entity_manifest_sha256 = hashlib.sha256(entity_manifest_path.read_bytes()).hexdigest()
    manifest = {
        "dataset_manifest_version": 1,
        "dataset_version": config.raw["dataset_version"], "generator_version": __version__, "seed": seed,
        "history_start": config.raw["history_start"], "history_end": config.raw["history_end"], "history_days": config.history_days,
        "timezone": config.raw["timezone"], "generated_at": generated_at,
        "tables": [
            {
                "table_name": table,
                "file": f"{table}.csv",
                "row_count": bundle.counts[table],
                "csv_file_size_bytes": (output / f"{table}.csv").stat().st_size,
                "sha256": hashlib.sha256((output / f"{table}.csv").read_bytes()).hexdigest(),
            }
            for table in TABLE_ORDER
        ],
        "business_statistics": {key: stats[key] for key in sorted(stats)} | {"product_change_events": bundle.counts["biz_product_change_event"], "changed_sku_count": changed_skus, "multi_change_sku_count": sum(value > 1 for value in change_counts)},
        "traffic_statistics": {"min_daily_orders": min(daily_orders.values()), "max_daily_orders": max(daily_orders.values()), "avg_daily_orders": round(sum(daily_orders.values()) / config.history_days, 4), "peak_date": daily_orders.most_common(1)[0][0], "peak_date_orders": daily_orders.most_common(1)[0][1], "peak_hour": hourly_orders.most_common(1)[0][0], "peak_hour_orders": hourly_orders.most_common(1)[0][1]},
        "distribution_statistics": {"distinct_sku": len(sku_sales), "distinct_spu": counts["biz_spu"], "top_1_sku_sales_share": round(ranked[0] / sales_total, 6), "top_10_sku_sales_share": round(sum(ranked[:10]) / sales_total, 6), "top_5_percent_sku_share": round(sum(ranked[:top5]) / sales_total, 6), "top_20_percent_sku_share": round(sum(ranked[:top20]) / sales_total, 6), "registered_users": counts["biz_user"], "visitors": counts["biz_visitor"], "mapped_visitors": counts["biz_identity_mapping"], "active_order_users": active_users, "repeat_buyers": sum(value >= 2 for value in user_orders.values()), "avg_orders_per_user": round(counts["biz_order"] / active_users, 6), "max_orders_per_user": max(user_orders.values())},
        "entity_manifest": {"file": entity_manifest_path.name, "version": 1, "sha256": entity_manifest_sha256},
    }
    (output / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate deterministic V2 bootstrap business CSVs")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--generated-at", required=True, help="explicit ISO-8601 evidence timestamp")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    datetime.fromisoformat(args.generated_at.replace("Z", "+00:00"))
    manifest = generate(load_config(args.config), args.seed, args.generated_at, args.output)
    print(canonical_json({"status": "generated", "output": str(args.output), "tables": len(manifest["tables"]), "rows": sum(item["row_count"] for item in manifest["tables"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
