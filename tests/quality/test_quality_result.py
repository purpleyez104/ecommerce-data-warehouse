import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DDL = load_module("generate_quality_result_ddl", ROOT / "quality/generate_quality_result_ddl.py")
RESULT = load_module("render_quality_result_sql", ROOT / "spark/scripts/render_quality_result_sql.py")


class QualityResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT / "quality/quality_result_contract.json").read_text(encoding="utf-8"))

    def test_contract_renders_partitioned_external_table(self):
        sql = DDL.render_sql(self.contract)
        self.assertIn("CREATE EXTERNAL TABLE IF NOT EXISTS ecommerce_quality.data_quality_result", sql)
        self.assertIn("PARTITIONED BY (run_id STRING)", sql)
        self.assertIn("STORED AS ORC", sql)
        self.assertIn("'orc.compress'='SNAPPY'", sql)

    def test_result_sql_persists_all_rules_and_blocks_failures(self):
        sql = RESULT.render_sql("m5-quality-r1", "m5-metrics-20261019-r1")
        self.assertEqual(40, len(RESULT.aggregate_rules()))
        self.assertEqual(40, sql.count(" AS rule_id,"))
        self.assertIn("INSERT OVERWRITE TABLE ecommerce_quality.data_quality_result", sql)
        self.assertIn("COUNT(*)=40", sql)
        self.assertIn("status='FAIL'", sql)
        self.assertIn("QUALITY_RESULT_GATE_PASS", sql)
        self.assertNotIn("AGGREGATE_GATE_PASS' AS rule_id", sql)

    def test_rejects_unsafe_run_and_batch_identifiers(self):
        with self.assertRaisesRegex(ValueError, "unsafe run_id"):
            RESULT.render_sql("bad/run", "safe-batch")
        with self.assertRaisesRegex(ValueError, "unsafe batch_id"):
            RESULT.render_sql("safe-run", "bad batch")

    def test_contract_rejects_unsafe_location(self):
        contract = dict(self.contract)
        contract["location"] = "/tmp/data_quality_result"
        with self.assertRaisesRegex(ValueError, "unsafe quality result location"):
            DDL.render_sql(contract)


if __name__ == "__main__":
    unittest.main()
