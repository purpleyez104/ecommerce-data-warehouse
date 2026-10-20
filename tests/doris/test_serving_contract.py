import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DDL = load_module("generate_serving_ddl", "doris/ddl/generate_serving_ddl.py")
LOAD = load_module("render_doris_load", "spark/scripts/render_doris_load.py")
RANGE_LOAD = load_module("render_doris_range_load", "spark/scripts/render_doris_range_load.py")


class ServingContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((ROOT / "doris/serving_contract.json").read_text(encoding="utf-8"))

    def test_renders_single_unique_key_serving_table(self):
        sql = DDL.render_sql(self.contract)
        self.assertEqual(1, sql.count("CREATE TABLE IF NOT EXISTS"))
        self.assertIn("UNIQUE KEY(`business_date`)", sql)
        self.assertIn('"enable_unique_key_merge_on_write" = "true"', sql)
        self.assertIn('"replication_num" = "2"', sql)

    def test_rejects_contract_drift(self):
        drift = copy.deepcopy(self.contract)
        drift["table"] = "another_table"
        with self.assertRaisesRegex(ValueError, "unexpected serving target"):
            DDL.validate_contract(drift)
        drift = copy.deepcopy(self.contract)
        drift["key_model"] = "DUPLICATE KEY"
        with self.assertRaisesRegex(ValueError, "unique key"):
            DDL.validate_contract(drift)

    def test_renders_secret_free_explicit_day_writer(self):
        script = LOAD.render_script(self.contract, "2026-02-28", "m6_smoke_r1")
        self.assertIn("WHERE dt = '2026-02-28'", script)
        self.assertIn('os.environ["DORIS_PASSWORD"]', script)
        self.assertIn('doris.sink.enable-2pc", "true', script)
        self.assertNotIn("password123", script)

    def test_rejects_invalid_runtime_parameters(self):
        with self.assertRaises(ValueError):
            LOAD.render_script(self.contract, "2026-02-30", "m6_smoke_r1")
        with self.assertRaisesRegex(ValueError, "unsafe batch_id"):
            LOAD.render_script(self.contract, "2026-02-28", "bad batch")

    def test_renders_explicit_ninety_day_range_writer(self):
        script = RANGE_LOAD.render_script(
            self.contract, "2025-12-01", "2026-02-28", "m6_full_r1"
        )
        self.assertIn("row_count != 90", script)
        self.assertIn("distinct_days != 90", script)
        self.assertIn("dt >= '2025-12-01' AND dt <= '2026-02-28'", script)
        self.assertIn('os.environ["DORIS_PASSWORD"]', script)

    def test_range_writer_rejects_reversed_window(self):
        with self.assertRaisesRegex(ValueError, "must not exceed"):
            RANGE_LOAD.render_script(
                self.contract, "2026-02-28", "2025-12-01", "m6_full_r1"
            )


if __name__ == "__main__":
    unittest.main()
