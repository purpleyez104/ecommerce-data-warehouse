from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "spark/scripts/render_behavior_ods_sql.py"
SPEC = importlib.util.spec_from_file_location("render_behavior_ods_sql", MODULE_PATH)
RENDERER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDERER)


class RenderBehaviorOdsSqlTests(unittest.TestCase):
    def test_renders_dynamic_publish_and_gate(self):
        preflight = {
            "row_count": 3,
            "business_date_row_counts": {"2026-01-01": 2, "2026-01-02": 1},
        }
        load_sql, gate_sql = RENDERER.render_sql(
            preflight, "hdfs:///warehouse/ecommerce/behavior/day_61/events.jsonl",
            "ecommerce_ods", "behavior-day-61-r1",
        )
        self.assertIn("partitionOverwriteMode=dynamic", load_sql)
        self.assertIn("INSERT OVERWRITE TABLE `ecommerce_ods`.`ods_behavior_event`", load_sql)
        self.assertIn("date_format(to_timestamp(`event_time`), 'yyyy-MM-dd')", load_sql)
        self.assertIn("duplicate event_id", gate_sql)
        self.assertIn("BEHAVIOR_ODS_GATE_PASS", gate_sql)
        self.assertEqual(gate_sql.count("row count mismatch"), 3)

    def test_rejects_unsafe_runtime_identifiers(self):
        preflight = {"row_count": 0, "business_date_row_counts": {}}
        with self.assertRaisesRegex(ValueError, "invalid database"):
            RENDERER.render_sql(preflight, "hdfs:///safe", "unsafe-name", "batch")
        with self.assertRaisesRegex(ValueError, "invalid input URI"):
            RENDERER.render_sql(preflight, "hdfs:///bad'path", "ecommerce_ods", "batch")

    def test_full_bundle_enables_recursive_json_read(self):
        preflight = {
            "package": "all",
            "row_count": 3_000_000,
            "business_date_row_counts": {"2025-12-01": 100, "2026-02-28": 200},
        }
        load_sql, gate_sql = RENDERER.render_sql(
            preflight, "hdfs:///warehouse/ecommerce/behavior-raw/v2.3", "ecommerce_ods", "behavior-all-r1",
        )
        self.assertIn("recursiveFileLookup 'true'", load_sql)
        self.assertIn("pathGlobFilter 'events.jsonl'", load_sql)
        self.assertIn("COUNT(*)=3000000", load_sql)
        self.assertIn("COUNT(*)=3000000", gate_sql)


if __name__ == "__main__":
    unittest.main()
