from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from business_generator.config import load_config
from business_generator.contracts import LOAD_TABLE_ORDER, TABLE_COLUMNS
from business_generator.replay import APPEND_ONLY, RECORD_TIME, build_replay


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "replay_smoke.json"
SEED = 20260928
GENERATED_AT = "2026-10-14T09:00:00+08:00"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class ReplayTests(unittest.TestCase):
    def test_replay_bundle_is_deterministic_and_has_thirty_daily_packages(self):
        cfg = load_config(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            first_manifest = build_replay(cfg, SEED, GENERATED_AT, first)
            second_manifest = build_replay(cfg, SEED, GENERATED_AT, second)

            self.assertEqual(first_manifest["business_hash"], second_manifest["business_hash"])
            self.assertEqual(len(first_manifest["daily_packages"]), 30)
            self.assertEqual(first_manifest["daily_packages"], second_manifest["daily_packages"])
            self.assertTrue((first / "bootstrap" / "ods_batch_contract.json").is_file())
            for binding in first_manifest["source_bundle"].values():
                bound_path = first / binding["path"]
                self.assertTrue(bound_path.is_file())
                self.assertEqual(hashlib.sha256(bound_path.read_bytes()).hexdigest(), binding["sha256"])
            self.assertEqual(len(list((first / "daily").glob("day_*/ods_batch_contract.json"))), 30)
            self.assertEqual(
                {path.name for path in (first / "bootstrap").glob("biz_*.csv")},
                {f"{table}.csv" for table in TABLE_COLUMNS},
            )
            rank = {table: index for index, table in enumerate(LOAD_TABLE_ORDER)}
            found_same_day = set()
            found_deduplicated_extract = False
            daily_operations = []
            for package in first_manifest["daily_packages"]:
                package_dir = first / package["path"]
                operations = [json.loads(line) for line in (package_dir / "operations.jsonl").read_text(encoding="utf-8").splitlines()]
                daily_operations.extend(operations)
                keys = [(item["operation_time"], rank[item["table"]]) for item in operations]
                self.assertEqual(keys, sorted(keys))
                self.assertEqual([item["sequence"] for item in operations], list(range(1, len(operations) + 1)))
                grouped = {}
                for item in operations:
                    if item["table"] in APPEND_ONLY:
                        self.assertEqual(item["operation_time"], item["row"][RECORD_TIME[item["table"]]])
                    key = (item["table"], tuple(item["primary_key"].values()))
                    grouped.setdefault(key, []).append(item)
                for (table, _), items in grouped.items():
                    kinds = [item["operation_type"] for item in items]
                    if "INSERT" in kinds and "UPDATE" in kinds:
                        found_same_day.add(table)
                        self.assertLess(kinds.index("INSERT"), kinds.index("UPDATE"))
                        inserted = items[kinds.index("INSERT")]["row"]
                        if table == "biz_order":
                            self.assertEqual(inserted["order_status"], "CREATED")
                        elif table == "biz_payment_attempt":
                            self.assertEqual(inserted["payment_status"], "INIT")
                        elif table == "biz_refund_request":
                            self.assertEqual(inserted["refund_status"], "REQUESTED")
                        elif table == "biz_coupon":
                            self.assertEqual(inserted["coupon_status"], "UNUSED")
                        elif table == "biz_order_item":
                            self.assertEqual(inserted["refunded_cents"], "0")
                package_manifest = json.loads((package_dir / "package_manifest.json").read_text(encoding="utf-8"))
                contract = json.loads((package_dir / "ods_batch_contract.json").read_text(encoding="utf-8"))
                for item in package_manifest["tables"]:
                    table_ops = [operation for operation in operations if operation["table"] == item["table_name"]]
                    self.assertEqual(item["operation_count"], len(table_ops))
                    if item["table_name"] != "biz_identity_mapping":
                        unique_keys = {tuple(operation["primary_key"].values()) for operation in table_ops}
                        self.assertEqual(item["extract_row_count"], len(unique_keys))
                    self.assertEqual(contract["expected_tables"][item["table_name"]]["row_count"], item["extract_row_count"])
                    self.assertEqual(sum(item["business_date_row_counts"].values()), item["extract_row_count"])
                    found_deduplicated_extract |= item["operation_count"] > item["extract_row_count"]
            self.assertTrue({"biz_order", "biz_payment_attempt", "biz_refund_request", "biz_order_item"} <= found_same_day)
            self.assertTrue(found_deduplicated_extract)
            refund_events = {
                (item["row"]["refund_request_id"], item["row"]["to_status"], item["row"]["occurred_at"])
                for item in daily_operations
                if item["table"] == "biz_refund_event"
            }
            refund_updates = [
                item for item in daily_operations
                if item["table"] == "biz_refund_request" and item["operation_type"] == "UPDATE"
            ]
            self.assertTrue(refund_updates)
            for update in refund_updates:
                self.assertIn(
                    (
                        update["row"]["refund_request_id"],
                        update["row"]["refund_status"],
                        update["operation_time"],
                    ),
                    refund_events,
                )
            for left in first.rglob("*"):
                if left.is_file():
                    right = second / left.relative_to(first)
                    self.assertEqual(left.read_bytes(), right.read_bytes(), left.relative_to(first))

    def test_bootstrap_has_no_future_order_sku_or_coupon_state(self):
        cfg = load_config(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "replay"
            manifest = build_replay(cfg, SEED, GENERATED_AT, output)
            cutover = manifest["cutover_time"]
            orders = read_csv(output / "bootstrap" / "biz_order.csv")
            skus = read_csv(output / "bootstrap" / "biz_sku.csv")
            coupons = read_csv(output / "bootstrap" / "biz_coupon.csv")
            payment_attempts = read_csv(output / "bootstrap" / "biz_payment_attempt.csv")
            refund_requests = read_csv(output / "bootstrap" / "biz_refund_request.csv")
            refund_transactions = read_csv(output / "bootstrap" / "biz_refund_transaction.csv")

            self.assertTrue(all(row["updated_at"] < cutover for row in orders))
            self.assertTrue(all(not row["paid_at"] or row["paid_at"] < cutover for row in orders))
            self.assertTrue(all(not row["canceled_at"] or row["canceled_at"] < cutover for row in orders))
            self.assertTrue(all(row["updated_at"] < cutover for row in skus))
            self.assertTrue(all(row["updated_at"] < cutover for row in coupons))
            self.assertTrue(all(row["updated_at"] < cutover for row in payment_attempts))
            self.assertTrue(all(not row["succeeded_at"] or row["succeeded_at"] < cutover for row in payment_attempts))
            self.assertTrue(all(row["updated_at"] < cutover for row in refund_requests))
            self.assertTrue(all(not row["completed_at"] or row["completed_at"] < cutover for row in refund_requests))
            self.assertTrue(all(row["updated_at"] < cutover for row in refund_transactions))
            self.assertTrue(all(not row["succeeded_at"] or row["succeeded_at"] < cutover for row in refund_transactions))

            daily_operations = []
            for package in manifest["daily_packages"]:
                path = output / package["path"] / "operations.jsonl"
                daily_operations.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
            self.assertTrue(any(item["table"] == "biz_order" and item["operation_type"] == "UPDATE" for item in daily_operations))
            self.assertTrue(any(item["table"] == "biz_coupon" for item in daily_operations))

            order_events = read_csv(output / "bootstrap" / "biz_order_status_event.csv")
            latest_order_status = {}
            for event in sorted(order_events, key=lambda item: (item["occurred_at"], int(item["order_event_id"]))):
                latest_order_status[event["order_id"]] = event["to_status"]
            self.assertTrue(latest_order_status)
            self.assertTrue(all(row["order_status"] == latest_order_status[row["order_id"]] for row in orders))

            product_events = read_csv(output / "bootstrap" / "biz_product_change_event.csv")
            product_events.extend(
                item["row"] for item in daily_operations
                if item["table"] == "biz_product_change_event" and item["row"]["effective_at"] < cutover
            )
            latest_prices = {}
            for event in sorted(product_events, key=lambda item: (item["effective_at"], int(item["change_id"]))):
                latest_prices[event["target_id"]] = str(json.loads(event["after_data"])["sale_price_cents"])
            self.assertTrue(latest_prices)
            sku_by_id = {row["sku_id"]: row for row in skus}
            self.assertTrue(all(sku_by_id[sku_id]["sale_price_cents"] == price for sku_id, price in latest_prices.items()))

    def test_each_daily_package_preserves_stateful_gate_invariants(self):
        """逐日状态必须满足事件终态、资金生命周期和金额聚合规则。

        默认生成 Smoke Fixture；设置 ``BUSINESS_REPLAY_BUNDLE`` 后直接审计正式
        Bundle，避免等数据库回放到特定日期后才发现生成器的中间状态错误。
        """
        external_bundle = os.environ.get("BUSINESS_REPLAY_BUNDLE")
        temporary = tempfile.TemporaryDirectory() if not external_bundle else None
        try:
            if external_bundle:
                output = Path(external_bundle)
                manifest = json.loads((output / "replay_manifest.json").read_text(encoding="utf-8"))
            else:
                output = Path(temporary.name) / "replay"
                manifest = build_replay(load_config(CONFIG), SEED, GENERATED_AT, output)
            tables = {
                table: {
                    row[TABLE_COLUMNS[table][0]]: row
                    for row in read_csv(output / "bootstrap" / f"{table}.csv")
                }
                for table in (
                    "biz_order",
                    "biz_order_item",
                    "biz_order_status_event",
                    "biz_payment_attempt",
                    "biz_payment_event",
                    "biz_refund_request",
                    "biz_refund_transaction",
                    "biz_refund_event",
                    "biz_coupon",
                    "biz_coupon_event",
                )
            }

            for package in manifest["daily_packages"]:
                operations = [
                    json.loads(line)
                    for line in (output / package["path"] / "operations.jsonl")
                    .read_text(encoding="utf-8")
                    .splitlines()
                ]
                for operation in operations:
                    if operation["table"] in tables:
                        key = next(iter(operation["primary_key"].values()))
                        tables[operation["table"]][key] = operation["row"]

                event_contracts = (
                    (
                        "biz_order",
                        "biz_order_status_event",
                        "order_id",
                        "order_status",
                        "occurred_at",
                        "order_event_id",
                        {("", "CREATED"), ("CREATED", "PAID"), ("CREATED", "CANCELED")},
                        "",
                    ),
                    (
                        "biz_payment_attempt",
                        "biz_payment_event",
                        "payment_attempt_id",
                        "payment_status",
                        "occurred_at",
                        "payment_event_id",
                        {("INIT", "INIT"), ("INIT", "FAILED"), ("INIT", "SUCCESS")},
                        "INIT",
                    ),
                    (
                        "biz_refund_request",
                        "biz_refund_event",
                        "refund_request_id",
                        "refund_status",
                        "occurred_at",
                        "refund_event_id",
                        {("", "REQUESTED"), ("REQUESTED", "PROCESSING"), ("PROCESSING", "SUCCESS"), ("PROCESSING", "FAILED")},
                        "",
                    ),
                    (
                        "biz_coupon",
                        "biz_coupon_event",
                        "coupon_id",
                        "coupon_status",
                        "occurred_at",
                        "coupon_event_id",
                        {("", "UNUSED"), ("UNUSED", "LOCKED"), ("LOCKED", "USED"), ("LOCKED", "UNUSED"), ("LOCKED", "EXPIRED"), ("UNUSED", "EXPIRED")},
                        "",
                    ),
                )
                for entity_table, event_table, foreign_key, status_field, time_field, event_id, allowed, initial in event_contracts:
                    grouped_events = {}
                    for event in tables[event_table].values():
                        grouped_events.setdefault(event[foreign_key], []).append(event)
                        self.assertGreaterEqual(event["recorded_at"], event[time_field], package["day_number"])
                        self.assertIn((event["from_status"], event["to_status"]), allowed, package["day_number"])
                    for entity_id, entity in tables[entity_table].items():
                        events = sorted(
                            grouped_events.get(entity_id, []),
                            key=lambda row: (row[time_field], int(row[event_id])),
                        )
                        if not events and entity_table == "biz_payment_attempt":
                            self.assertEqual(entity[status_field], "INIT", package["day_number"])
                            continue
                        self.assertTrue(events, (package["day_number"], entity_table, entity_id))
                        prior = initial
                        for event in events:
                            self.assertEqual(event["from_status"], prior, package["day_number"])
                            prior = event["to_status"]
                        self.assertEqual(entity[status_field], prior, package["day_number"])

                events_by_request = {}
                for event in tables["biz_refund_event"].values():
                    events_by_request.setdefault(event["refund_request_id"], []).append(event)
                txns_by_request = {}
                for txn in tables["biz_refund_transaction"].values():
                    txns_by_request.setdefault(txn["refund_request_id"], []).append(txn)
                requests_by_item = {}
                for request in tables["biz_refund_request"].values():
                    requests_by_item.setdefault(request["order_item_id"], []).append(request)
                    latest = max(
                        events_by_request[request["refund_request_id"]],
                        key=lambda row: (row["occurred_at"], int(row["refund_event_id"])),
                    )
                    self.assertEqual(request["refund_status"], latest["to_status"], package["day_number"])
                    statuses = [
                        row["refund_txn_status"]
                        for row in txns_by_request.get(request["refund_request_id"], [])
                    ]
                    expected = request["refund_status"]
                    if expected == "REQUESTED":
                        self.assertFalse(statuses, package["day_number"])
                    elif expected == "PROCESSING":
                        self.assertGreaterEqual(statuses.count("INIT"), 1, package["day_number"])
                        self.assertFalse({"FAILED", "SUCCESS"} & set(statuses), package["day_number"])
                    elif expected == "SUCCESS":
                        self.assertEqual(statuses.count("SUCCESS"), 1, package["day_number"])
                    else:
                        self.assertEqual(expected, "FAILED")
                        self.assertGreaterEqual(statuses.count("FAILED"), 1, package["day_number"])
                        self.assertNotIn("SUCCESS", statuses, package["day_number"])

                for item_id, item in tables["biz_order_item"].items():
                    requests = requests_by_item.get(item_id, [])
                    reserved = sum(
                        int(row["requested_amount_cents"])
                        for row in requests
                        if row["refund_status"] in {"REQUESTED", "PROCESSING"}
                    )
                    refunded = sum(
                        int(row["requested_amount_cents"])
                        for row in requests
                        if row["refund_status"] == "SUCCESS"
                    )
                    quantity = sum(
                        int(row["refund_quantity"] or 0)
                        for row in requests
                        if row["refund_status"] == "SUCCESS"
                    )
                    self.assertEqual(int(item["refund_reserved_cents"]), reserved, package["day_number"])
                    self.assertEqual(int(item["refunded_cents"]), refunded, package["day_number"])
                    self.assertEqual(int(item["refunded_quantity"]), quantity, package["day_number"])
        finally:
            if temporary is not None:
                temporary.cleanup()

    def test_failure_removes_incomplete_output(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "bad.json"
            payload = json.loads(CONFIG.read_text(encoding="utf-8"))
            for index, invalid_end in enumerate(("2025-11-28T23:59:59.999", "2025-11-29T23:59:59.998")):
                with self.subTest(history_end=invalid_end):
                    payload["history_end"] = invalid_end
                    config_path.write_text(json.dumps(payload), encoding="utf-8")
                    output = Path(directory) / f"replay-{index}"
                    with self.assertRaisesRegex(ValueError, "final millisecond of day 90"):
                        build_replay(load_config(config_path), SEED, GENERATED_AT, output)
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
