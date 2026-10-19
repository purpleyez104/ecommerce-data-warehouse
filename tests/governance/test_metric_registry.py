from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "governance" / "metric_registry" / "validate_metric_registry.py"
SPEC = importlib.util.spec_from_file_location("validate_metric_registry", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class MetricRegistryTests(unittest.TestCase):
    """覆盖正式发布及会导致口径漂移的主要失败路径。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(
            (REPO_ROOT / "governance" / "metric_registry" / "metric_registry.json").read_text(
                encoding="utf-8"
            )
        )
        cls.aggregate = json.loads(
            (REPO_ROOT / "hive" / "model" / "aggregate_contract.json").read_text(
                encoding="utf-8"
            )
        )

    def validate(self, registry: dict) -> dict[str, int]:
        return VALIDATOR.validate_registry(registry, self.aggregate, REPO_ROOT)

    def test_current_registry_is_valid(self) -> None:
        self.assertEqual({"metrics": 36, "evidence_files": 2}, self.validate(self.registry))

    def test_duplicate_metric_version_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.registry)
        candidate["metrics"].append(copy.deepcopy(candidate["metrics"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate metric definition"):
            self.validate(candidate)

    def test_missing_definition_version_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.registry)
        del candidate["metrics"][0]["definition_version"]
        with self.assertRaisesRegex(ValueError, "definition_version is required"):
            self.validate(candidate)

    def test_unverified_metric_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.registry)
        candidate["metrics"][0]["publication_status"] = "implemented"
        with self.assertRaisesRegex(ValueError, "only verified metrics may be published"):
            self.validate(candidate)

    def test_definition_drift_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.registry)
        candidate["metrics"][0]["definition_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "definition hash mismatch"):
            self.validate(candidate)

    def test_unknown_output_measure_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.registry)
        candidate["metrics"][0]["output"]["measure"] = "missing_measure"
        with self.assertRaisesRegex(ValueError, "unknown output measure"):
            self.validate(candidate)


if __name__ == "__main__":
    unittest.main()
