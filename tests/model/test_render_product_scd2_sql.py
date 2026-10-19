import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "spark/scripts/render_product_scd2_sql.py"
SPEC = importlib.util.spec_from_file_location("render_product_scd2_sql", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RenderProductScd2SqlTests(unittest.TestCase):
    def setUp(self):
        self.semantic = json.loads((ROOT / "hive/model/model_contract.json").read_text(encoding="utf-8"))
        self.physical = json.loads((ROOT / "hive/model/model_physical_contract.json").read_text(encoding="utf-8"))

    def test_renders_price_history_with_half_open_intervals(self):
        sql = MODULE.render_sql(self.semantic, self.physical, "model-bootstrap-r1")
        self.assertIn("unsupported product change event", sql)
        self.assertIn("get_json_object(before_data, '$.sale_price_cents')", sql)
        self.assertIn("get_json_object(after_data, '$.sale_price_cents')", sql)
        self.assertIn("lead(effective_from) OVER (PARTITION BY sku_id", sql)
        self.assertIn("TIMESTAMP '9999-12-31 23:59:59.999'", sql)
        self.assertIn("v.next_effective_from IS NULL AS is_current", sql)
        self.assertIn("sha2(concat_ws('|', CAST(v.sku_id AS STRING)", sql)
        self.assertIn("ORDER BY dt DESC, extract_time DESC, batch_id DESC", sql)
        self.assertNotIn("ORDER BY dt DESC, load_time DESC", sql)

    def test_rejects_unsafe_batch_and_contract_drift(self):
        with self.assertRaisesRegex(ValueError, "unsafe batch_id"):
            MODULE.render_sql(self.semantic, self.physical, "bad batch")

        drift = copy.deepcopy(self.semantic)
        drift["models"]["dim_product_zip"]["history_strategy"] = "type_1"
        with self.assertRaisesRegex(ValueError, "must use scd2"):
            MODULE.validate_contracts(drift, self.physical)


if __name__ == "__main__":
    unittest.main()
