import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "spark/scripts/render_dwd_sql.py"
SPEC = importlib.util.spec_from_file_location("render_dwd_sql", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RenderDwdSqlTests(unittest.TestCase):
    def setUp(self):
        self.semantic = json.loads((ROOT / "hive/model/model_contract.json").read_text(encoding="utf-8"))
        self.physical = json.loads((ROOT / "hive/model/model_physical_contract.json").read_text(encoding="utf-8"))

    def test_renders_eight_business_time_partitioned_models(self):
        sql = MODULE.render_sql(self.semantic, self.physical, "model-bootstrap-r1")
        self.assertEqual(8, sql.count("INSERT OVERWRITE TABLE ecommerce_dwd."))
        for model in MODULE.DWD_MODELS:
            self.assertIn(f"ecommerce_dwd.{model}", sql)
        self.assertIn("i.created_at>=p.effective_from AND i.created_at<p.effective_to", sql)
        self.assertIn("e.event_time>=m.effective_from", sql)
        self.assertIn("payment_status='SUCCESS'", sql)
        self.assertIn("refund_txn_status='SUCCESS'", sql)
        self.assertIn("FROM request r LEFT JOIN successful_txn t", sql)
        self.assertIn("CAST(to_date(r.requested_at) AS STRING) AS dt", sql)
        self.assertIn("r.refund_request_id, r.refund_request_no", sql)
        self.assertIn("ORDER BY dt DESC, extract_time DESC, batch_id DESC", sql)
        self.assertIn("PARTITION BY event_id ORDER BY dt DESC, load_time DESC, batch_id DESC", sql)
        self.assertEqual(8, sql.count(" AS dt"))

    def test_renders_only_selected_model_for_table_level_recovery(self):
        sql = MODULE.render_sql(
            self.semantic,
            self.physical,
            "model-bootstrap-r1",
            {"dwd_behavior_event"},
        )
        self.assertEqual(1, sql.count("INSERT OVERWRITE TABLE ecommerce_dwd."))
        self.assertIn("ecommerce_dwd.dwd_behavior_event", sql)
        self.assertNotIn("ecommerce_dwd.dwd_order ", sql)

    def test_rejects_unsafe_batch_and_contract_drift(self):
        with self.assertRaisesRegex(ValueError, "unsafe batch_id"):
            MODULE.render_sql(self.semantic, self.physical, "bad batch")

        drift = copy.deepcopy(self.semantic)
        del drift["models"]["dwd_refund"]
        with self.assertRaisesRegex(ValueError, "DWD model set drift"):
            MODULE.validate_contracts(drift, self.physical)


if __name__ == "__main__":
    unittest.main()
