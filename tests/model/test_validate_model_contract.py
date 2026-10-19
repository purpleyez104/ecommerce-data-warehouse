import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "hive" / "model" / "validate_model_contract.py"
SPEC = importlib.util.spec_from_file_location("validate_model_contract", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ValidateModelContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((ROOT / "hive" / "model" / "model_contract.json").read_text(encoding="utf-8"))
        self.ods_contract = json.loads((ROOT / "datax" / "config" / "ods_tables.json").read_text(encoding="utf-8"))

    def test_formal_contract_covers_complete_first_model_layer(self):
        summary = MODULE.validate_contract(self.contract, self.ods_contract)
        self.assertEqual({"models": 14, "dim": 6, "dwd": 8, "scd2": 1}, summary)
        self.assertEqual("scd2", self.contract["models"]["dim_product_zip"]["history_strategy"])
        self.assertEqual(["event_id"], self.contract["models"]["dwd_behavior_event"]["business_key"])
        self.assertEqual(["refund_request_id"], self.contract["models"]["dwd_refund"]["business_key"])
        self.assertEqual("accumulating_snapshot", self.contract["models"]["dwd_refund"]["fact_kind"])

    def test_unknown_source_and_incomplete_scd2_fail_fast(self):
        unknown_source = copy.deepcopy(self.contract)
        unknown_source["models"]["dwd_order"]["sources"] = ["ods_missing"]
        with self.assertRaisesRegex(ValueError, "unknown ODS sources"):
            MODULE.validate_contract(unknown_source, self.ods_contract)

        missing_interval = copy.deepcopy(self.contract)
        del missing_interval["models"]["dim_product_zip"]["effective_to"]
        with self.assertRaisesRegex(ValueError, "effective_to is required"):
            MODULE.validate_contract(missing_interval, self.ods_contract)

    def test_fact_requires_event_time_and_gate_groups_are_unique(self):
        missing_time = copy.deepcopy(self.contract)
        del missing_time["models"]["dwd_payment"]["event_time"]
        with self.assertRaisesRegex(ValueError, "event_time is required"):
            MODULE.validate_contract(missing_time, self.ods_contract)

        duplicate_gate = copy.deepcopy(self.contract)
        duplicate_gate["model_gate"]["common"].append("business_key_unique")
        with self.assertRaisesRegex(ValueError, "contains duplicates"):
            MODULE.validate_contract(duplicate_gate, self.ods_contract)


if __name__ == "__main__":
    unittest.main()
