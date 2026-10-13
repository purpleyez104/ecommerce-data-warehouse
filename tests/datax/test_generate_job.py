import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "datax/scripts/generate_job.py"
SPEC = importlib.util.spec_from_file_location("generate_job", MODULE_PATH)
GENERATE_JOB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATE_JOB)


def sample_env(project_home="/tmp/ecommerce-data-warehouse"):
    return {
        "MYSQL_JDBC_URL": "jdbc:mysql://hadoop201:3306/ecommerce_oltp",
        "MYSQL_USER": "datax_reader",
        "MYSQL_PASSWORD": 'quote"and\\slash',
        "HDFS_DEFAULT_FS": "hdfs://hadoop201:8020",
        "ODS_STAGE_ROOT": "/warehouse/ecommerce/ods/.staging",
        "PROJECT_HOME": project_home,
    }


def query_and_writer(rendered):
    payload = json.loads(rendered)
    content = payload["job"]["content"][0]
    query = content["reader"]["parameter"]["connection"][0]["querySql"][0]
    return query, content["writer"]["parameter"]


class GenerateJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = GENERATE_JOB.load_contract()

    def test_contract_covers_21_tables_and_complete_policies(self):
        expected_business_time = {
            "biz_user": "registered_at",
            "biz_visitor": "first_seen_at",
            "biz_identity_mapping": None,
            "biz_category": "created_at",
            "biz_spu": "created_at",
            "biz_sku": "created_at",
            "biz_product_change_event": "effective_at",
            "biz_cart": "created_at",
            "biz_cart_item": "created_at",
            "biz_cart_merge_record": "merged_at",
            "biz_coupon_template": "created_at",
            "biz_coupon": "issued_at",
            "biz_order": "created_at",
            "biz_order_item": "created_at",
            "biz_order_status_event": "occurred_at",
            "biz_payment_attempt": "initiated_at",
            "biz_payment_event": "occurred_at",
            "biz_refund_request": "requested_at",
            "biz_refund_transaction": "initiated_at",
            "biz_refund_event": "occurred_at",
            "biz_coupon_event": "occurred_at",
        }
        self.assertEqual(len(self.contract["tables"]), 21)
        self.assertEqual(set(self.contract["tables"]), set(GENERATE_JOB.TABLE_COLUMNS))
        targets = set()
        for table, policy in self.contract["tables"].items():
            self.assertEqual(policy["source_table"], table)
            self.assertTrue(policy["target_table"].startswith("ods_"))
            self.assertNotIn(policy["target_table"], targets)
            targets.add(policy["target_table"])
            self.assertEqual(policy["partition"], {"column": "dt", "source": "business_date"})
            self.assertTrue(policy["quality_rules"])
            self.assertEqual(policy["business_time"].get("column"), expected_business_time[table])
            self.assertEqual(
                [item["name"] for item in policy["columns"]],
                GENERATE_JOB.TABLE_COLUMNS[table],
            )
        identity = self.contract["tables"]["biz_identity_mapping"]
        self.assertEqual(identity["load_strategy"], "full_snapshot")
        self.assertIsNone(identity["watermark_column"])
        payment_columns = self.contract["tables"]["biz_payment_attempt"]["columns"]
        self.assertNotIn("successful_order_id", {item["name"] for item in payment_columns})
        self.assertEqual(payment_columns[0], {"name": "payment_attempt_id", "type": "long"})

    def test_load_env_expands_nested_variables_and_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            project_home = Path(directory) / "project"
            env_file = Path(directory) / "datax.env"
            env_file.write_text(
                "MYSQL_HOST=hadoop201\n"
                "MYSQL_PORT=3306\n"
                "MYSQL_DATABASE=ecommerce_oltp\n"
                "MYSQL_USER=datax_reader\n"
                "MYSQL_PASSWORD=test-only\n"
                "MYSQL_JDBC_URL=jdbc:mysql://${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE}\n"
                "HDFS_DEFAULT_FS=hdfs://hadoop201:8020\n"
                "ODS_STAGE_ROOT=/warehouse/ecommerce/ods/.staging\n"
                f"PROJECT_HOME={project_home}\n"
                "DATAX_JOB_DIR=${PROJECT_HOME}/runtime/datax/jobs/private\n",
                encoding="utf-8",
            )
            env = GENERATE_JOB.load_env(env_file)
            self.assertEqual(env["MYSQL_JDBC_URL"], "jdbc:mysql://hadoop201:3306/ecommerce_oltp")
            self.assertEqual(GENERATE_JOB.job_output_dir(env), (project_home / "runtime/datax/jobs/private").resolve())
            env_file.write_text(env_file.read_text(encoding="utf-8") + "MYSQL_USER=duplicate\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate DataX config key"):
                GENERATE_JOB.load_env(env_file)

    def test_bootstrap_distributes_business_dates_inside_batch_staging(self):
        rendered = GENERATE_JOB.render_job(
            sample_env(), self.contract, "biz_order", "bootstrap", "2026-02-28",
            "bootstrap-001", "2026-10-13 09:00:00",
        )
        query, writer = query_and_writer(rendered)
        names = [item["name"] for item in writer["column"]]
        self.assertIn("DATE_FORMAT(`created_at`, '%Y-%m-%d') AS `business_date`", query)
        self.assertNotIn("'2026-02-28' AS `business_date`", query)
        self.assertIn("WHERE 1 = 1", query)
        self.assertEqual(names[-4:], ["business_date", "extract_time", "batch_id", "source_table"])
        self.assertEqual(writer["fileType"], "orc")
        self.assertEqual(writer["compress"], "SNAPPY")
        self.assertEqual(writer["writeMode"], "nonConflict")
        self.assertEqual(
            writer["path"],
            "/warehouse/ecommerce/ods/.staging/ods_order/batch_id=bootstrap-001",
        )
        self.assertNotIn("/dt=", writer["path"])
        self.assertNotIn("${", rendered)

    def test_incremental_event_uses_record_watermark_and_business_time(self):
        rendered = GENERATE_JOB.render_job(
            sample_env(), self.contract, "biz_coupon_event", "incremental",
            "2026-03-01", "daily-20260301", "2026-10-13 09:00:00",
            window_start="2026-03-01 00:00:00", window_end="2026-03-02 00:00:00",
        )
        query, _ = query_and_writer(rendered)
        self.assertIn("`recorded_at` >= '2026-03-01 00:00:00'", query)
        self.assertIn("`recorded_at` < '2026-03-02 00:00:00'", query)
        self.assertIn("DATE_FORMAT(`occurred_at`, '%Y-%m-%d') AS `business_date`", query)

    def test_identity_incremental_is_full_snapshot_on_explicit_snapshot_date(self):
        rendered = GENERATE_JOB.render_job(
            sample_env(), self.contract, "biz_identity_mapping", "incremental",
            "2026-03-01", "snapshot-20260301", "2026-10-13 09:00:00",
        )
        query, writer = query_and_writer(rendered)
        self.assertIn("'2026-03-01' AS `business_date`", query)
        self.assertIn("WHERE 1 = 1", query)
        self.assertNotIn("`recorded_at` >=", query)
        self.assertIn("/ods_identity_mapping/batch_id=snapshot-20260301", writer["path"])
        with self.assertRaisesRegex(ValueError, "must not receive a window"):
            GENERATE_JOB.render_job(
                sample_env(), self.contract, "biz_identity_mapping", "incremental",
                "2026-03-01", "snapshot-2", "2026-10-13 09:00:00",
                window_start="2026-03-01 00:00:00", window_end="2026-03-02 00:00:00",
            )

    def test_incremental_rejects_missing_reversed_and_non_timestamp_windows(self):
        with self.assertRaisesRegex(ValueError, "requires window_start"):
            GENERATE_JOB.render_job(
                sample_env(), self.contract, "biz_order", "incremental",
                "2026-03-01", "daily-1", "2026-10-13 09:00:00",
            )
        with self.assertRaisesRegex(ValueError, "earlier"):
            GENERATE_JOB.render_job(
                sample_env(), self.contract, "biz_order", "incremental",
                "2026-03-01", "daily-1", "2026-10-13 09:00:00",
                window_start="2026-03-02 00:00:00", window_end="2026-03-01 00:00:00",
            )
        for invalid in ("2026-03-01", "2026-03-01T00:00:00", "2026-03-01 00:00:00+08:00"):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "Invalid window_start"):
                GENERATE_JOB.render_job(
                    sample_env(), self.contract, "biz_order", "incremental",
                    "2026-03-01", "daily-2", "2026-10-13 09:00:00",
                    window_start=invalid, window_end="2026-03-02 00:00:00",
                )

    def test_bootstrap_rejects_window_unknown_table_and_invalid_extract_time(self):
        with self.assertRaisesRegex(ValueError, "must not receive"):
            GENERATE_JOB.render_job(
                sample_env(), self.contract, "biz_order", "bootstrap",
                "2026-02-28", "bootstrap-1", "2026-10-13 09:00:00",
                window_start="2026-02-01 00:00:00", window_end="2026-03-01 00:00:00",
            )
        with self.assertRaisesRegex(ValueError, "Unknown"):
            GENERATE_JOB.render_job(
                sample_env(), self.contract, "biz_unknown", "bootstrap",
                "2026-02-28", "bootstrap-1", "2026-10-13 09:00:00",
            )
        with self.assertRaisesRegex(ValueError, "Invalid extract_time"):
            GENERATE_JOB.render_job(
                sample_env(), self.contract, "biz_order", "bootstrap",
                "2026-02-28", "bootstrap-1", "2026-10-13",
            )

    def test_contract_rejects_unknown_keys_and_invalid_policy_shapes(self):
        source = json.loads(GENERATE_JOB.DEFAULT_CONTRACT.read_text(encoding="utf-8"))
        cases = []
        unknown = copy.deepcopy(source)
        unknown["tables"]["biz_order"]["unexpected"] = True
        cases.append((unknown, "invalid keys"))
        invalid_time = copy.deepcopy(source)
        invalid_time["tables"]["biz_order"]["business_time"] = {"mode": "column", "column": "missing"}
        cases.append((invalid_time, "invalid business_time"))
        non_temporal = copy.deepcopy(source)
        non_temporal["tables"]["biz_order"]["business_time"] = {"mode": "column", "column": "order_no"}
        cases.append((non_temporal, "must be DATETIME"))
        invalid_snapshot = copy.deepcopy(source)
        invalid_snapshot["tables"]["biz_identity_mapping"]["watermark_column"] = "recorded_at"
        cases.append((invalid_snapshot, "full_snapshot"))
        duplicate_target = copy.deepcopy(source)
        duplicate_target["tables"]["biz_user"]["target_table"] = "ods_order"
        cases.append((duplicate_target, "duplicate target_table"))
        invalid_quality = copy.deepcopy(source)
        invalid_quality["tables"]["biz_order"]["quality_rules"] = ["primary_key_not_null", "typo"]
        cases.append((invalid_quality, "invalid quality_rules"))
        duplicate_pk = copy.deepcopy(source)
        duplicate_pk["tables"]["biz_order"]["primary_key"] = ["order_id", "order_id"]
        cases.append((duplicate_pk, "invalid primary_key"))
        with tempfile.TemporaryDirectory() as directory:
            contract_file = Path(directory) / "contract.json"
            for payload, message in cases:
                with self.subTest(message=message):
                    contract_file.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, message):
                        GENERATE_JOB.load_contract(contract_file)

    def test_env_rejects_missing_values_and_unscoped_hdfs_root(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "datax.env"
            base = (
                "MYSQL_JDBC_URL=jdbc:mysql://localhost/db\n"
                "MYSQL_USER=datax_reader\n"
                "MYSQL_PASSWORD=\n"
                "HDFS_DEFAULT_FS=hdfs://hadoop201:8020\n"
                "ODS_STAGE_ROOT=/warehouse/ecommerce/ods/.staging\n"
                f"PROJECT_HOME={Path(directory) / 'project'}\n"
            )
            env_file.write_text(base, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "MYSQL_PASSWORD"):
                GENERATE_JOB.load_env(env_file)
            env_file.write_text(base.replace("MYSQL_PASSWORD=\n", "MYSQL_PASSWORD=test\n").replace(
                "ODS_STAGE_ROOT=/warehouse/ecommerce/ods/.staging", "ODS_STAGE_ROOT=/"
            ), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "scoped absolute"):
                GENERATE_JOB.load_env(env_file)

    def test_job_directory_rejects_traversal_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            outside = root / "outside"
            outside.mkdir()
            env = sample_env(str(project))
            env["DATAX_JOB_DIR"] = str(project / "runtime/datax/jobs/../../../../outside")
            with self.assertRaisesRegex(ValueError, "must stay within"):
                GENERATE_JOB.job_output_dir(env)
            allowed = project / "runtime/datax/jobs"
            allowed.mkdir(parents=True)
            link = allowed / "escape"
            env["DATAX_JOB_DIR"] = str(link)
            try:
                os.symlink(outside, link, target_is_directory=True)
            except OSError:
                original_resolve = Path.resolve

                def resolve_symlink(candidate, strict=False):
                    if candidate == link:
                        return outside.resolve(strict=strict)
                    return original_resolve(candidate, strict=strict)

                with mock.patch.object(Path, "resolve", resolve_symlink):
                    with self.assertRaisesRegex(ValueError, "must stay within"):
                        GENERATE_JOB.job_output_dir(env)
            else:
                with self.assertRaisesRegex(ValueError, "must stay within"):
                    GENERATE_JOB.job_output_dir(env)

    def test_private_job_is_exclusive_and_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runtime/datax/jobs/biz_order_batch.json"
            GENERATE_JOB.write_private_job(path, "secret\n")
            self.assertEqual(path.read_text(encoding="utf-8"), "secret\n")
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaises(FileExistsError):
                GENERATE_JOB.write_private_job(path, "replacement\n")
            self.assertEqual(path.read_text(encoding="utf-8"), "secret\n")


if __name__ == "__main__":
    unittest.main()
