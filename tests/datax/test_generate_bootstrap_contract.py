from __future__ import annotations

import csv
import hashlib
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
MODULE_PATH = DATAX_SCRIPTS / "generate_bootstrap_contract.py"
SPEC = importlib.util.spec_from_file_location("generate_bootstrap_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GenerateBootstrapContractTests(unittest.TestCase):
    def test_builds_snapshot_contract_with_partition_counts(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / "bundle"
            bundle.mkdir()
            contract = MODULE.generate_job.load_contract()
            manifest_tables = []
            for table, policy in contract["tables"].items():
                path = bundle / f"{table}.csv"
                row = {column: "1" for column in MODULE.generate_job.TABLE_COLUMNS[table]}
                date_column = MODULE._business_date_column(policy)
                if date_column:
                    row[date_column] = "2026-02-01 00:00:00.000"
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=MODULE.generate_job.TABLE_COLUMNS[table])
                    writer.writeheader()
                    writer.writerow(row)
                manifest_tables.append({
                    "table_name": table,
                    "file": path.name,
                    "row_count": 1,
                    "csv_file_size_bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                })
            manifest = {
                "dataset_manifest_version": 1,
                "dataset_version": "test-snapshot",
                "history_start": "2026-02-01T00:00:00",
                "history_end": "2026-02-28T23:59:59.999",
                "tables": manifest_tables,
            }
            (bundle / "dataset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            output = root / "contract"
            MODULE.build_contract(bundle, output, "formal-bootstrap-test", "2026-10-17 20:00:00")
            batch = json.loads((output / "ods_batch_contract.json").read_text(encoding="utf-8"))
            self.assertEqual(batch["batch_contract_version"], 2)
            self.assertEqual(batch["business_date"], "2026-02-28")
            self.assertEqual(batch["source_manifest"]["type"], "dataset_snapshot")
            self.assertEqual(batch["expected_tables"]["biz_identity_mapping"]["business_date_row_counts"], {"2026-02-28": 1})
            self.assertEqual(batch["expected_tables"]["biz_order"]["business_date_row_counts"], {"2026-02-01": 1})


if __name__ == "__main__":
    unittest.main()
