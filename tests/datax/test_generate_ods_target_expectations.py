from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "datax/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import generate_ods_target_expectations as target_expectations


class TargetExpectationTests(unittest.TestCase):
    def test_source_sql_and_snapshot_contracts_build_complete_expectations(self):
        contract = {
            "tables": {
                "biz_order": {
                    "load_strategy": "mutable_incremental",
                    "business_time": {"mode": "column", "column": "created_at"},
                },
                "biz_identity_mapping": {
                    "load_strategy": "full_snapshot",
                    "business_time": {"mode": "parameter"},
                },
            }
        }
        sql = target_expectations.render_source_sql(contract)
        self.assertIn("DATE_FORMAT(`created_at`", sql)
        self.assertNotIn("biz_identity_mapping", sql)

        with tempfile.TemporaryDirectory() as raw:
            bundle = Path(raw)
            paths = [bundle / "bootstrap/ods_batch_contract.json"]
            paths.extend(bundle / f"daily/day_{day:02d}/ods_batch_contract.json" for day in range(61, 91))
            for index, path in enumerate(paths):
                path.parent.mkdir(parents=True, exist_ok=True)
                date = f"2026-01-{index + 1:02d}"
                payload = {
                    "business_date": date,
                    "expected_tables": {
                        "biz_identity_mapping": {
                            "row_count": index + 1,
                            "business_date_row_counts": {date: index + 1},
                        }
                    },
                }
                path.write_text(json.dumps(payload), encoding="utf-8")

            result = target_expectations.build_expectations(
                contract,
                {"biz_order": {"2026-01-01": 2, "2026-01-02": 3}},
                bundle,
            )

        self.assertEqual(result["expected_tables"]["biz_order"]["row_count"], 5)
        snapshot = result["expected_tables"]["biz_identity_mapping"]
        self.assertEqual(snapshot["row_count"], sum(range(1, 32)))
        self.assertEqual(len(snapshot["business_date_row_counts"]), 31)


if __name__ == "__main__":
    unittest.main()
