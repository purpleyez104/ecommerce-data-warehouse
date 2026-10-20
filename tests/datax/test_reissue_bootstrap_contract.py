import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATAX_SCRIPTS = ROOT / "datax/scripts"
if str(DATAX_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DATAX_SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "reissue_bootstrap_contract", ROOT / "datax/scripts/reissue_bootstrap_contract.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReissueBootstrapContractTests(unittest.TestCase):
    def test_reissues_identity_without_changing_snapshot_expectations(self):
        temp_root = ROOT / "runtime/tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            root = Path(directory)
            manifest = root / "snapshot_manifest.json"
            manifest.write_text('{"snapshot_manifest_version":1}\n', encoding="utf-8")
            source = root / "source.json"
            payload = {
                "batch_contract_version": 2,
                "mode": "bootstrap",
                "batch_id": "old-batch",
                "extract_time": "2026-10-17 20:35:00",
                "source_manifest": {
                    "path": manifest.name,
                    "sha256": MODULE._sha256(manifest),
                },
                "expected_tables": {"biz_user": {"row_count": 1}},
            }
            source.write_text(json.dumps(payload), encoding="utf-8")
            target = MODULE.reissue(
                source, root / "issued", "new-batch", "2026-10-19 17:10:00"
            )
            issued = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual("new-batch", issued["batch_id"])
            self.assertEqual(payload["expected_tables"], issued["expected_tables"])
            self.assertEqual(payload["source_manifest"], issued["source_manifest"])


if __name__ == "__main__":
    unittest.main()
