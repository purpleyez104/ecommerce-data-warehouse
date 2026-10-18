from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from business_generator.config import load_config
from business_generator.contracts import LOAD_TABLE_ORDER, TABLE_COLUMNS
from business_generator.generator import generate as generate_business


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "smoke.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GeneratorTests(unittest.TestCase):
    def test_business_bootstrap_is_deterministic_and_conserves_amounts(self):
        cfg = load_config(CONFIG)
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            generate_business(cfg, 20260928, "2026-09-28T10:00:00+08:00", first)
            generate_business(cfg, 20260928, "2026-09-28T10:00:00+08:00", second)
            self.assertEqual(set(path.name for path in first.glob("biz_*.csv")), {f"{name}.csv" for name in TABLE_COLUMNS})
            for table in TABLE_COLUMNS:
                self.assertEqual(digest(first / f"{table}.csv"), digest(second / f"{table}.csv"))
            self.assertEqual(digest(first / "entity_manifest.json"), digest(second / "entity_manifest.json"))
            with (first / "biz_user.csv").open(encoding="utf-8", newline="") as handle:
                users = {int(row["user_id"]): row for row in csv.DictReader(handle)}
            with (first / "biz_order.csv").open(encoding="utf-8", newline="") as handle:
                orders = {int(row["order_id"]): row for row in csv.DictReader(handle)}
            totals = {}
            with (first / "biz_order_item.csv").open(encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    values = totals.setdefault(int(row["order_id"]), [0, 0, 0, 0])
                    values[0] += 1
                    values[1] += int(row["gross_amount_cents"])
                    values[2] += int(row["allocated_discount_cents"])
                    values[3] += int(row["payable_amount_cents"])
            for order_id, order in orders.items():
                self.assertLessEqual(totals[order_id][0], 5)
                self.assertEqual(totals[order_id][1:], [int(order["gross_amount_cents"]), int(order["discount_amount_cents"]), int(order["payable_amount_cents"])])
                self.assertGreaterEqual(order["created_at"], users[int(order["user_id"])]["registered_at"])
            with (first / "biz_payment_attempt.csv").open(encoding="utf-8", newline="") as handle:
                for attempt in csv.DictReader(handle):
                    self.assertTrue(attempt["created_at"])
                    self.assertGreaterEqual(attempt["updated_at"], attempt["created_at"])
                    if attempt["payment_status"] == "SUCCESS":
                        self.assertGreaterEqual(attempt["succeeded_at"], attempt["initiated_at"])
            with (first / "biz_refund_request.csv").open(encoding="utf-8", newline="") as handle:
                refunds = list(csv.DictReader(handle))
            with (first / "biz_order_item.csv").open(encoding="utf-8", newline="") as handle:
                items = {int(row["order_item_id"]): row for row in csv.DictReader(handle)}
            for refund in refunds:
                item = items[int(refund["order_item_id"])]
                self.assertLessEqual(int(item["refunded_cents"]) + int(item["refund_reserved_cents"]), int(item["payable_amount_cents"]))
                if refund["refund_status"] == "SUCCESS":
                    self.assertEqual(int(item["refunded_cents"]), int(refund["requested_amount_cents"]))
            for table in ("biz_order_item", "biz_refund_request", "biz_refund_transaction"):
                with (first / f"{table}.csv").open(encoding="utf-8", newline="") as handle:
                    for row in csv.DictReader(handle):
                        self.assertTrue(row["created_at"])
                        self.assertTrue(row["updated_at"])
            with (first / "biz_coupon.csv").open(encoding="utf-8", newline="") as handle:
                coupons = {int(row["coupon_id"]): row for row in csv.DictReader(handle)}
            with (first / "biz_coupon_event.csv").open(encoding="utf-8", newline="") as handle:
                coupon_events = list(csv.DictReader(handle))
            issue_times = {int(row["coupon_id"]): row["occurred_at"] for row in coupon_events if row["event_type"] == "ISSUE"}
            for event in coupon_events:
                coupon_id = int(event["coupon_id"])
                self.assertGreaterEqual(event["occurred_at"], issue_times[coupon_id])
                if event["order_id"]:
                    self.assertEqual(coupons[coupon_id]["user_id"], orders[int(event["order_id"])]["user_id"])
            history_end = cfg.end.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            for table in TABLE_COLUMNS:
                with (first / f"{table}.csv").open(encoding="utf-8", newline="") as handle:
                    for row in csv.DictReader(handle):
                        for column, value in row.items():
                            if value and column.endswith("_at") and column != "expires_at":
                                self.assertLessEqual(value, history_end, f"{table}.{column} exceeds history_end")
            manifest = json.loads((first / "dataset_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["dataset_manifest_version"], 1)
            self.assertEqual(len(manifest["tables"]), 21)
            self.assertLess(LOAD_TABLE_ORDER.index("biz_coupon"), LOAD_TABLE_ORDER.index("biz_order"))
            for entry in manifest["tables"]:
                csv_path = first / entry["file"]
                self.assertEqual(entry["file"], f'{entry["table_name"]}.csv')
                self.assertEqual(entry["row_count"], cfg.raw["counts"][entry["table_name"]])
                self.assertEqual(entry["csv_file_size_bytes"], csv_path.stat().st_size)
                self.assertEqual(entry["sha256"], digest(csv_path))
            self.assertEqual(manifest["business_statistics"]["paid_orders"], 70)
            entities = json.loads((first / "entity_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(entities["entity_manifest_version"], 1)
            self.assertEqual(len(entities["entities"]["users"]), cfg.raw["counts"]["biz_user"])
            self.assertEqual(len(entities["entities"]["visitors"]), cfg.raw["counts"]["biz_visitor"])
            self.assertEqual(len(entities["entities"]["identity_mappings"]), cfg.raw["counts"]["biz_identity_mapping"])
            self.assertEqual(len(entities["entities"]["skus"]), cfg.raw["counts"]["biz_sku"])
            self.assertEqual(manifest["entity_manifest"]["sha256"], digest(first / "entity_manifest.json"))
            with (first / "biz_coupon.csv").open(encoding="utf-8", newline="") as handle:
                for coupon in csv.DictReader(handle):
                    if coupon["coupon_status"] == "USED":
                        self.assertFalse(coupon["locked_order_id"])
                        self.assertFalse(coupon["locked_at"])
                        self.assertTrue(coupon["used_order_id"])
                        self.assertTrue(coupon["used_at"])
            with (first / "biz_refund_event.csv").open(encoding="utf-8", newline="") as handle:
                refund_events = list(csv.DictReader(handle))
            self.assertNotIn("INIT", {row["to_status"] for row in refund_events})
            events_by_request = {}
            for event in refund_events:
                events_by_request.setdefault(int(event["refund_request_id"]), []).append(event)
            for refund in refunds:
                request_id = int(refund["refund_request_id"])
                events = sorted(events_by_request[request_id], key=lambda row: (row["occurred_at"], int(row["refund_event_id"])))
                self.assertEqual(events[0]["from_status"], "")
                for previous, current in zip(events, events[1:]):
                    self.assertEqual(current["from_status"], previous["to_status"], request_id)
                self.assertEqual(events[-1]["to_status"], refund["refund_status"])
                self.assertEqual(refund["updated_at"], events[-1]["occurred_at"], request_id)
                if refund["refund_status"] in {"SUCCESS", "FAILED"}:
                    self.assertEqual(refund["completed_at"], events[-1]["occurred_at"], request_id)
            refund_event_manifest = next(entry for entry in manifest["tables"] if entry["table_name"] == "biz_refund_event")
            self.assertEqual(refund_event_manifest["row_count"], len(refund_events))

    def test_derived_event_count_mismatch_fails_and_removes_output(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "mismatch.json"
            raw = json.loads(CONFIG.read_text(encoding="utf-8"))
            raw["counts"]["biz_coupon_event"] -= 1
            config_path.write_text(json.dumps(raw), encoding="utf-8")
            output = Path(directory) / "output"

            with self.assertRaisesRegex(ValueError, "coupon event target is inconsistent"):
                generate_business(load_config(config_path), 20260928, "2026-09-28T10:00:00+08:00", output)

            self.assertFalse(output.exists())

if __name__ == "__main__":
    unittest.main()
