from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATAX_SCRIPTS = ROOT / "datax/scripts"
if str(DATAX_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DATAX_SCRIPTS))
BUSINESS_SRC = ROOT / "mock/generator/business_generator/src"
if str(BUSINESS_SRC) not in sys.path:
    sys.path.insert(0, str(BUSINESS_SRC))
import generate_job
from business_generator.config import load_config
from business_generator.replay import build_replay

MODULE_PATH = ROOT / "spark/scripts/render_ods_gate_sql.py"
SPEC = importlib.util.spec_from_file_location("render_ods_gate_sql", MODULE_PATH)
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class RenderOdsGateSqlTests(unittest.TestCase):
    def test_renders_full_table_partition_type_and_reference_gate(self):
        config = ROOT / "mock/generator/business_generator/config/replay_smoke.json"
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "replay"
            build_replay(load_config(config), 20260928, "2026-10-14T09:00:00+08:00", output)
            batch = json.loads((output / "bootstrap/ods_batch_contract.json").read_text(encoding="utf-8"))
            sql = GATE.render_gate_sql(generate_job.load_contract(), batch, "ecommerce_ods_replay_20260105_r1")
        self.assertEqual(sql.count(": total row count mismatch"), 21)
        self.assertEqual(sql.count(": Hive type mismatch"), 21)
        self.assertIn("partition/audit mismatch", sql)
        self.assertIn("ods_order_item -> ods_order: orphan reference", sql)
        self.assertIn("typeof(`created_at`)='timestamp'", sql)
        self.assertIn("`mapping_id`, `dt`, COUNT(*) c", sql)

    def test_rejects_unsafe_database(self):
        with self.assertRaisesRegex(ValueError, "invalid ODS database"):
            GATE.render_gate_sql(generate_job.load_contract(), {"expected_tables": {}}, "bad-name")

    def test_incremental_gate_uses_full_target_expectations_and_checks_staged_rows(self):
        config = ROOT / "mock/generator/business_generator/config/replay_smoke.json"
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "replay"
            build_replay(load_config(config), 20260928, "2026-10-14T09:00:00+08:00", output)
            batch = json.loads((output / "daily/day_61/ods_batch_contract.json").read_text(encoding="utf-8"))
            target = {}
            for table, value in batch["expected_tables"].items():
                target[table] = {
                    "row_count": value["row_count"] + 1,
                    "business_date_row_counts": {"2026-01-01": value["row_count"] + 1},
                }
            sql = GATE.render_gate_sql(
                generate_job.load_contract(),
                batch,
                "ecommerce_ods_replay_20260105_r1",
                target,
                "/warehouse/ecommerce/ods-replay-20260105-r1/.staging",
            )
        self.assertIn("staged rows missing after publish", sql)
        self.assertIn("t.`dt` <=> s.`business_date`", sql)
        self.assertIn("total row count mismatch", sql)
        self.assertNotIn("NOT (`batch_id` <=>", sql)


if __name__ == "__main__":
    unittest.main()
