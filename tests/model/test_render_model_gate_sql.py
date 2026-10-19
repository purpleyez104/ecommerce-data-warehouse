import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "spark/scripts/render_model_gate_sql.py"
SPEC = importlib.util.spec_from_file_location("render_model_gate_sql", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RenderModelGateSqlTests(unittest.TestCase):
    def setUp(self):
        self.semantic = json.loads((ROOT / "hive/model/model_contract.json").read_text(encoding="utf-8"))
        self.physical = json.loads((ROOT / "hive/model/model_physical_contract.json").read_text(encoding="utf-8"))

    def test_renders_common_scd2_reference_amount_and_behavior_gates(self):
        sql = MODULE.render_sql(self.semantic, self.physical)
        self.assertEqual(60, sql.count("SELECT assert_true"))
        for model in self.semantic["models"]:
            self.assertIn(f"{model}.business_key_not_null", sql)
            if self.semantic["models"][model].get("history_strategy") == "scd2":
                self.assertIn(f"{model}.business_key_interval_unique", sql)
            else:
                self.assertIn(f"{model}.business_key_unique", sql)
            self.assertIn(f"{model}.audit_columns_not_null", sql)
        self.assertIn("COUNT(DISTINCT product_sk)", sql)
        self.assertIn("effective_interval_non_overlapping", sql)
        self.assertIn("dwd_order.amount_conservation", sql)
        self.assertIn("dwd_payment.amount_matches_order", sql)
        self.assertIn("dwd_refund.state_and_funding_consistent", sql)
        self.assertIn("dwd_behavior_event.identity_time_match", sql)
        self.assertIn("MODEL_GATE_PASS", sql)

    def test_rejects_semantic_physical_model_drift(self):
        drift = copy.deepcopy(self.physical)
        del drift["models"]["dwd_refund"]
        with self.assertRaisesRegex(ValueError, "model sets differ"):
            MODULE.validate_contracts(self.semantic, drift)


if __name__ == "__main__":
    unittest.main()
