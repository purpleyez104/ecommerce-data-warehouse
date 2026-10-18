from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPORT = ROOT / "datax/jobs/formal-bootstrap-20260228-r1"


class ExportedJobsTests(unittest.TestCase):
    def test_formal_bootstrap_export_is_complete_and_secret_free(self):
        manifest = json.loads((EXPORT / "job_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["job_manifest_version"], 1)
        self.assertEqual(manifest["source_database"], "ecommerce_oltp")
        self.assertEqual(manifest["target_database"], "ecommerce_ods")
        self.assertEqual(len(manifest["files"]), 21)
        for item in manifest["files"]:
            path = EXPORT / item["file"]
            content = path.read_text(encoding="utf-8")
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])
            self.assertIn("${MYSQL_PASSWORD}", content)
            self.assertIn("${MYSQL_JDBC_URL}", content)
            self.assertNotIn("121.43.139.187", content)


if __name__ == "__main__":
    unittest.main()
