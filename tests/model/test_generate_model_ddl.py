import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "hive" / "model" / "generate_model_ddl.py"
SPEC = importlib.util.spec_from_file_location("generate_model_ddl", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GenerateModelDdlTests(unittest.TestCase):
    def setUp(self):
        self.semantic = json.loads((ROOT / "hive/model/model_contract.json").read_text(encoding="utf-8"))
        self.physical = json.loads((ROOT / "hive/model/model_physical_contract.json").read_text(encoding="utf-8"))

    def test_renders_fourteen_external_orc_snappy_tables(self):
        ddl = MODULE.render_ddl(self.semantic, self.physical, "/warehouse/ecommerce/model")
        self.assertEqual(14, ddl.count("CREATE EXTERNAL TABLE IF NOT EXISTS"))
        self.assertEqual(14, ddl.count("STORED AS ORC"))
        self.assertEqual(14, ddl.count("'orc.compress'='SNAPPY'"))
        self.assertEqual(14, ddl.count("PARTITIONED BY (`dt` STRING)"))
        self.assertIn("`ecommerce_dim`.`dim_product_zip`", ddl)
        self.assertIn("`ecommerce_dwd`.`dwd_behavior_event`", ddl)
        self.assertIn("/warehouse/ecommerce/model/m5_20261018/ecommerce_dwd/dwd_refund", ddl)

    def test_rejects_model_drift_missing_key_and_unsafe_root(self):
        drift = copy.deepcopy(self.physical)
        del drift["models"]["dwd_order"]
        with self.assertRaisesRegex(ValueError, "model set mismatch"):
            MODULE.validate_physical_contract(self.semantic, drift)

        missing_key = copy.deepcopy(self.physical)
        missing_key["models"]["dwd_payment"]["columns"] = [
            item for item in missing_key["models"]["dwd_payment"]["columns"] if item[0] != "funding_txn_id"
        ]
        with self.assertRaisesRegex(ValueError, "missing business key"):
            MODULE.validate_physical_contract(self.semantic, missing_key)

        with self.assertRaisesRegex(ValueError, "explicit /warehouse/ecommerce"):
            MODULE.render_ddl(self.semantic, self.physical, "/tmp/model")

        unsafe_location = copy.deepcopy(self.physical)
        unsafe_location["models"]["dwd_refund"]["location"] = "/tmp/dwd_refund"
        with self.assertRaisesRegex(ValueError, "unsafe explicit location"):
            MODULE.validate_physical_contract(self.semantic, unsafe_location)


if __name__ == "__main__":
    unittest.main()
