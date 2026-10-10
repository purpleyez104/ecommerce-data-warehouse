from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from business_generator.config import load_config
from business_generator.contracts import TABLE_COLUMNS
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
            with (first / "biz_refund_request.csv").open(encoding="utf-8", newline="") as handle:
                refunds = list(csv.DictReader(handle))
            with (first / "biz_order_item.csv").open(encoding="utf-8", newline="") as handle:
                items = {int(row["order_item_id"]): row for row in csv.DictReader(handle)}
            for refund in refunds:
                item = items[int(refund["order_item_id"])]
                self.assertLessEqual(int(item["refunded_cents"]) + int(item["refund_reserved_cents"]), int(item["payable_amount_cents"]))
                if refund["refund_status"] == "SUCCESS":
                    self.assertEqual(int(item["refunded_cents"]), int(refund["requested_amount_cents"]))
            manifest = json.loads((first / "dataset_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["tables"]), 21)
            self.assertEqual(manifest["business_statistics"]["paid_orders"], 70)

if __name__ == "__main__":
    unittest.main()
