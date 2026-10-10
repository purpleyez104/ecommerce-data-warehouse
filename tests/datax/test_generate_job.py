import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "datax/scripts/generate_job.py"
SPEC = importlib.util.spec_from_file_location("generate_job", MODULE_PATH)
GENERATE_JOB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATE_JOB)


class GenerateJobTests(unittest.TestCase):
    def test_load_env_expands_nested_variables(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "datax.env"
            env_file.write_text(
                "\n".join(
                    (
                        "MYSQL_HOST=hadoop201",
                        "MYSQL_PORT=3306",
                        "MYSQL_DATABASE=ecommerce_oltp",
                        "MYSQL_USER=datax_reader",
                        "MYSQL_PASSWORD=test-only",
                        "MYSQL_JDBC_URL=jdbc:mysql://${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE}",
                        "HDFS_DEFAULT_FS=hdfs://hadoop201:8020",
                        "PROJECT_HOME=/data/projects/ecommerce-data-warehouse",
                        "DATAX_JOB_DIR=${PROJECT_HOME}/runtime/datax/jobs",
                    )
                )
                + "\n",
                encoding="utf-8",
            )

            env = GENERATE_JOB.load_env(env_file)

        self.assertEqual(
            env["MYSQL_JDBC_URL"],
            "jdbc:mysql://hadoop201:3306/ecommerce_oltp",
        )
        self.assertEqual(
            env["DATAX_JOB_DIR"],
            "/data/projects/ecommerce-data-warehouse/runtime/datax/jobs",
        )

    def test_render_job_produces_strict_json(self):
        env = {
            "MYSQL_JDBC_URL": "jdbc:mysql://hadoop201:3306/ecommerce_oltp",
            "MYSQL_USER": "datax_reader",
            "MYSQL_PASSWORD": 'quote"and\\slash',
            "HDFS_DEFAULT_FS": "hdfs://hadoop201:8020",
            "DATAX_JOB_DIR": "/tmp/jobs",
        }

        rendered = GENERATE_JOB.render_job(
            env,
            "biz_order",
            "updated_at >= '2026-09-22 00:00:00'",
            "/warehouse/ods/biz_order/dt=2026-09-22",
        )
        payload = json.loads(rendered)

        parameter = payload["job"]["content"][0]["reader"]["parameter"]
        query = parameter["connection"][0]["querySql"][0]
        self.assertIn("\nFROM biz_order\n", query)
        self.assertEqual(parameter["password"], 'quote"and\\slash')
        self.assertNotIn("${", rendered)
        self.assertTrue(rendered.endswith("\n"))

    def test_load_env_rejects_missing_private_values(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "datax.env"
            env_file.write_text(
                "MYSQL_JDBC_URL=jdbc:mysql://localhost/db\n"
                "MYSQL_USER=datax_reader\n"
                "MYSQL_PASSWORD=\n"
                "HDFS_DEFAULT_FS=hdfs://hadoop201:8020\n"
                "DATAX_JOB_DIR=/tmp/jobs\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "MYSQL_PASSWORD"):
                GENERATE_JOB.load_env(env_file)


if __name__ == "__main__":
    unittest.main()
