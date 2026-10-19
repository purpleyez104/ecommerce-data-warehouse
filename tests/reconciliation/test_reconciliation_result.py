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


DDL = load_module("generate_reconciliation_result_ddl", ROOT / "reconciliation/generate_reconciliation_result_ddl.py")
RESULT = load_module("render_cross_layer_reconciliation_sql", ROOT / "spark/scripts/render_cross_layer_reconciliation_sql.py")


class ReconciliationResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT / "reconciliation/reconciliation_result_contract.json").read_text(encoding="utf-8"))

    def test_contract_renders_one_generic_result_table(self):
        sql = DDL.render_sql(self.contract)
        self.assertIn("ecommerce_quality.reconciliation_result", sql)
        self.assertIn("comparison_scope STRING", sql)
        self.assertIn("left_value DECIMAL(38,6)", sql)
        self.assertIn("PARTITIONED BY (run_id STRING)", sql)

    def test_renderer_covers_six_domains_and_ads(self):
        sql = RESULT.render_sql("m5-reconciliation-r1", "m5-metrics-20261019-r1")
        self.assertEqual(10, len(RESULT.RECONCILIATIONS))
        self.assertEqual(10, sql.count(" AS reconciliation_id,"))
        for metric_id in ("TR-07", "TF-05", "PR-04", "US-05", "RF-03", "MK-01", "TR-02", "TF-01", "TR-13", "TR-14"):
            self.assertIn(f"'{metric_id}' AS metric_id", sql)
        self.assertIn("FULL OUTER JOIN", sql)
        self.assertIn("status='FAIL'", sql)
        self.assertIn("CROSS_LAYER_RECONCILIATION_PASS", sql)

    def test_rejects_unsafe_runtime_identifiers(self):
        with self.assertRaisesRegex(ValueError, "unsafe run_id"):
            RESULT.render_sql("bad/run", "safe-batch")
        with self.assertRaisesRegex(ValueError, "unsafe batch_id"):
            RESULT.render_sql("safe-run", "bad batch")

    def test_contract_rejects_unsafe_location(self):
        contract = dict(self.contract)
        contract["location"] = "/tmp/reconciliation_result"
        with self.assertRaisesRegex(ValueError, "unsafe reconciliation location"):
            DDL.render_sql(contract)


if __name__ == "__main__":
    unittest.main()
