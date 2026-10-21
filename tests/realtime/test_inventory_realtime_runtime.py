import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "flink" / "scripts" / "inventory_realtime_runtime.py"
SPEC = importlib.util.spec_from_file_location("inventory_realtime_runtime", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RealtimeRuntimeInventoryTests(unittest.TestCase):
    def test_builds_only_scoped_read_only_commands(self):
        commands = MODULE.build_inventory_commands(
            kafka_topics_command="/opt/kafka/bin/kafka-topics.sh",
            yarn_command="/opt/hadoop/bin/yarn",
            hdfs_command="/opt/hadoop/bin/hdfs",
            bootstrap_server="kafka.internal:9092",
            topic_namespace="ecommerce.realtime.v1",
            checkpoint_root="hdfs:///warehouse/ecommerce/realtime/v1/checkpoints",
            savepoint_root="hdfs:///warehouse/ecommerce/realtime/v1/savepoints",
        )

        self.assertEqual(
            {"kafka_list", "kafka_describe", "yarn_applications", "checkpoints", "savepoints"},
            set(commands),
        )
        self.assertEqual(
            ["/opt/hadoop/bin/yarn", "application", "-list", "-appStates", "ALL"],
            commands["yarn_applications"],
        )
        self.assertEqual(
            [
                "/opt/hadoop/bin/hdfs", "dfs", "-ls", "-R",
                "hdfs:///warehouse/ecommerce/realtime/v1/checkpoints",
            ],
            commands["checkpoints"],
        )
        self.assertIn(r"ecommerce\.realtime\.v1\..*", commands["kafka_describe"])

        forbidden = {"--create", "--delete", "-rm", "-mkdir", "-put", "-mv"}
        self.assertTrue(forbidden.isdisjoint(part for command in commands.values() for part in command))

    def test_rejects_unscoped_or_non_hdfs_roots(self):
        for invalid in ["/", "relative/path", "hdfs://namenode/"]:
            with self.subTest(invalid=invalid), self.assertRaises(MODULE.InventoryError):
                MODULE.validate_hdfs_root(invalid, "--checkpoint-root")

        with self.assertRaisesRegex(MODULE.InventoryError, "只允许 hdfs"):
            MODULE.validate_hdfs_root("file:///tmp/checkpoints", "--checkpoint-root")

    def test_redacts_credentials_and_secret_assignments(self):
        value = "jdbc:mysql://user:password@db.internal:3306/ecommerce?token=abc password=secret"
        redacted = MODULE.redact(value)

        self.assertNotIn("user:password", redacted)
        self.assertNotIn("abc", redacted)
        self.assertNotIn("secret", redacted)


if __name__ == "__main__":
    unittest.main()
