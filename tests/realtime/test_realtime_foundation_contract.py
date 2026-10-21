import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "kafka" / "realtime_foundation_contract.json"
MODULE_PATH = ROOT / "flink" / "cdc" / "validate_realtime_foundation_contract.py"
SPEC = importlib.util.spec_from_file_location("validate_realtime_foundation_contract", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RealtimeFoundationContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_frozen_contract_is_static_verified_only(self):
        summary = MODULE.validate_contract(self.contract)

        self.assertEqual(
            {
                "status": "static_verified",
                "runtime": "not_run",
                "raw_cdc_topics": 21,
                "standard_domains": 7,
            },
            summary,
        )
        self.assertFalse(self.contract["flink_state"]["pilot_state_reuse"])
        self.assertEqual(
            ["kafka_offset"],
            self.contract["envelope"]["event_version"]["forbidden_strategies"],
        )

    def test_rejects_unreviewed_root_extension_and_missing_source_table(self):
        extra_root = copy.deepcopy(self.contract)
        extra_root["unreviewed_extension"] = {}
        with self.assertRaisesRegex(ValueError, "root keys mismatch"):
            MODULE.validate_contract(extra_root)

        missing_table = copy.deepcopy(self.contract)
        del missing_table["raw_cdc"]["topics"]["biz_order"]
        with self.assertRaisesRegex(ValueError, "exactly the 21 formal source tables"):
            MODULE.validate_contract(missing_table)

    def test_rejects_key_version_and_state_boundary_drift(self):
        retention_drift = copy.deepcopy(self.contract)
        retention_drift["topic_defaults"]["retention_ms"] = 86400000
        with self.assertRaisesRegex(ValueError, "topic_defaults differ"):
            MODULE.validate_contract(retention_drift)

        key_drift = copy.deepcopy(self.contract)
        key_drift["raw_cdc"]["topics"]["biz_order"]["primary_key"] = ["order_no"]
        with self.assertRaisesRegex(ValueError, "biz_order: primary_key"):
            MODULE.validate_contract(key_drift)

        version_drift = copy.deepcopy(self.contract)
        version_drift["envelope"]["event_version"]["strategy"] = "kafka_offset"
        with self.assertRaisesRegex(ValueError, "event_version.strategy mismatch"):
            MODULE.validate_contract(version_drift)

        state_drift = copy.deepcopy(self.contract)
        state_drift["flink_state"]["pilot_state_reuse"] = True
        with self.assertRaisesRegex(ValueError, "Pilot state reuse must be false"):
            MODULE.validate_contract(state_drift)


if __name__ == "__main__":
    unittest.main()
