from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATAX_SCRIPTS = ROOT / "datax/scripts"
if str(DATAX_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DATAX_SCRIPTS))
MODULE_PATH = ROOT / "hive/ods/generate_ods_ddl.py"
SPEC = importlib.util.spec_from_file_location("generate_ods_ddl", MODULE_PATH)
DDL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DDL)


class GenerateOdsDdlTests(unittest.TestCase):
    def test_renders_exactly_twenty_one_orc_snappy_tables(self):
        sql = DDL.render_ddl("ecommerce_ods_replay_20260105_r1")
        self.assertEqual(sql.count("CREATE EXTERNAL TABLE IF NOT EXISTS"), 21)
        self.assertEqual(sql.count("PARTITIONED BY (`dt` STRING)"), 21)
        self.assertEqual(sql.count("'orc.compress'='SNAPPY'"), 21)
        self.assertEqual(sql.count("LOCATION '/warehouse/ecommerce/ods/"), 21)
        self.assertIn("`order_id` BIGINT", sql)
        self.assertIn("`created_at` TIMESTAMP", sql)
        self.assertIn("`source_table` STRING", sql)

    def test_rejects_unsupported_type_and_unsafe_database(self):
        with self.assertRaisesRegex(ValueError, "unsupported MySQL type"):
            DDL.GENERATE_JOB.mysql_to_hive_type("FLOAT")
        with self.assertRaisesRegex(ValueError, "invalid Hive database"):
            DDL.render_ddl("unsafe-name")
        with self.assertRaisesRegex(ValueError, "invalid HDFS location root"):
            DDL.render_ddl("ecommerce_ods", "/")


if __name__ == "__main__":
    unittest.main()
