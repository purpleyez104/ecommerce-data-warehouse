import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "hive/model/generate_aggregate_ddl.py"
SPEC = importlib.util.spec_from_file_location("generate_aggregate_ddl", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GenerateAggregateDdlTests(unittest.TestCase):
    def setUp(self):
        self.semantic = json.loads((ROOT / "hive/model/aggregate_contract.json").read_text(encoding="utf-8"))
        self.physical = json.loads((ROOT / "hive/model/aggregate_physical_contract.json").read_text(encoding="utf-8"))

    def test_renders_seven_external_orc_snappy_tables(self):
        sql = MODULE.render_sql(self.semantic, self.physical)
        self.assertEqual(7, sql.count("CREATE EXTERNAL TABLE IF NOT EXISTS"))
        self.assertEqual(7, sql.count("PARTITIONED BY (dt STRING)"))
        self.assertEqual(7, sql.count("'orc.compress'='SNAPPY'"))
        self.assertIn("/warehouse/ecommerce/model/m5_20261018/ecommerce_ads/ads_daily_business_overview", sql)
        self.assertIn("/warehouse/ecommerce/model/ecommerce_dws/dws_behavior_day", sql)
        self.assertIn("ecommerce_dws.dws_product_day_sku", sql)
        self.assertIn("ecommerce_dws.dws_user_day", sql)
        self.assertIn("ecommerce_dws.dws_coupon_day", sql)
        self.assertIn("ecommerce_dws.dws_trade_cohort_day", sql)

    def test_rejects_model_drift_and_unsafe_root(self):
        drift = copy.deepcopy(self.physical)
        del drift["models"]["dws_behavior_day"]
        with self.assertRaisesRegex(ValueError, "model sets differ"):
            MODULE.validate_contracts(self.semantic, drift)
        unsafe = copy.deepcopy(self.physical)
        unsafe["hdfs_root"] = "/tmp/model"
        with self.assertRaisesRegex(ValueError, "unsafe aggregate hdfs_root"):
            MODULE.validate_contracts(self.semantic, unsafe)

        unsafe_location = copy.deepcopy(self.physical)
        unsafe_location["models"]["dws_trade_day"]["location"] = "/tmp/dws_trade_day"
        with self.assertRaisesRegex(ValueError, "unsafe explicit location"):
            MODULE.validate_contracts(self.semantic, unsafe_location)

        missing_measure = copy.deepcopy(self.physical)
        missing_measure["models"]["dws_coupon_day"]["columns"] = [
            item for item in missing_measure["models"]["dws_coupon_day"]["columns"]
            if item[0] != "coupon_discount_cents"
        ]
        with self.assertRaisesRegex(ValueError, "missing measure columns"):
            MODULE.validate_contracts(self.semantic, missing_measure)


if __name__ == "__main__":
    unittest.main()
