from __future__ import annotations

import csv
import hashlib
import json
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
            for package in first_manifest["daily_packages"]:
                package_dir = first / package["path"]
                operations = [json.loads(line) for line in (package_dir / "operations.jsonl").read_text(encoding="utf-8").splitlines()]
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
