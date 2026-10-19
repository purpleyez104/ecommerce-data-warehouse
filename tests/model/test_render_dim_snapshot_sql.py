import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "spark/scripts/render_dim_snapshot_sql.py"
SPEC = importlib.util.spec_from_file_location("render_dim_snapshot_sql", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RenderDimSnapshotSqlTests(unittest.TestCase):
    def setUp(self):
        self.semantic = json.loads((ROOT / "hive/model/model_contract.json").read_text(encoding="utf-8"))
        self.physical = json.loads((ROOT / "hive/model/model_physical_contract.json").read_text(encoding="utf-8"))

    def test_renders_five_idempotent_snapshot_dimensions(self):
        sql = MODULE.render_sql(self.semantic, self.physical, "2026-02-28", "model-bootstrap-r1")
        self.assertEqual(5, sql.count("INSERT OVERWRITE TABLE ecommerce_dim."))
        self.assertEqual(5, sql.count("WHERE rn = 1"))
        self.assertIn("PARTITION BY mapping_id, identity_version", sql)
        self.assertIn("ORDER BY dt DESC, extract_time DESC, batch_id DESC", sql)
        self.assertNotIn("ORDER BY dt DESC, load_time DESC", sql)
        self.assertNotIn("dim_product_zip", sql)
        self.assertEqual(5, sql.count("'2026-02-28' AS dt"))

    def test_rejects_invalid_parameters_and_contract_drift(self):
        with self.assertRaisesRegex(ValueError, "invalid snapshot_date"):
            MODULE.render_sql(self.semantic, self.physical, "2026/02/28", "model-bootstrap-r1")
        with self.assertRaisesRegex(ValueError, "unsafe batch_id"):
            MODULE.render_sql(self.semantic, self.physical, "2026-02-28", "bad id")

        drift = copy.deepcopy(self.physical)
        drift["models"]["dim_user"]["columns"] = [item for item in drift["models"]["dim_user"]["columns"] if item[0] != "user_key"]
        with self.assertRaisesRegex(ValueError, "missing physical columns"):
            MODULE.validate_contracts(self.semantic, drift)


if __name__ == "__main__":
    unittest.main()
