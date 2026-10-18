from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "hive/ods/generate_behavior_ods_ddl.py"
SPEC = importlib.util.spec_from_file_location("generate_behavior_ods_ddl", MODULE_PATH)
DDL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DDL)


class GenerateBehaviorOdsDdlTests(unittest.TestCase):
    def test_renders_independent_behavior_orc_table(self):
        sql = DDL.render_ddl()
        self.assertEqual(sql.count("CREATE EXTERNAL TABLE IF NOT EXISTS"), 1)
        self.assertIn("`ecommerce_ods`.`ods_behavior_event`", sql)
        self.assertIn("`event_id` STRING", sql)
        self.assertIn("`event_time` TIMESTAMP", sql)
        self.assertIn("`visitor_id` BIGINT", sql)
        self.assertIn("`batch_id` STRING", sql)
        self.assertIn("PARTITIONED BY (`dt` STRING)", sql)
        self.assertIn("'orc.compress'='SNAPPY'", sql)

    def test_contract_rejects_partition_drift_and_unsafe_database(self):
        contract = DDL.load_contract()
        contract["target"]["partition_source"] = "to_date(ingest_time)"
        # Windows Sandbox 的系统 TEMP 可能不可写，测试统一使用项目已忽略的临时目录。
        temp_root = ROOT / "runtime/tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "event_time business date"):
                DDL.render_ddl(contract_path=path)
        with self.assertRaisesRegex(ValueError, "invalid Hive database"):
            DDL.render_ddl("unsafe-name")


if __name__ == "__main__":
    unittest.main()
