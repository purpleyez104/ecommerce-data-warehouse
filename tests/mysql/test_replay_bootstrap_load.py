from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_SRC = ROOT / "mock" / "generator" / "business_generator" / "src"
MYSQL_SCRIPTS = ROOT / "mysql" / "scripts"
sys.path.insert(0, str(GENERATOR_SRC))
sys.path.insert(0, str(MYSQL_SCRIPTS))

from business_generator.common import canonical_json  # noqa: E402
from business_generator.config import load_config  # noqa: E402
from business_generator.replay import build_replay  # noqa: E402
import plan_replay_bootstrap  # noqa: E402


CONFIG = ROOT / "mock" / "generator" / "business_generator" / "config" / "replay_smoke.json"
SEED = 20260105
GENERATED_AT = "2026-10-15T10:00:00+08:00"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


class ReplayBootstrapLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._fixture = tempfile.TemporaryDirectory()
        cls.fixture_root = Path(cls._fixture.name) / "replay"
        build_replay(load_config(CONFIG), SEED, GENERATED_AT, cls.fixture_root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._fixture.cleanup()

    def copy_fixture(self, parent: Path) -> Path:
        target = parent / "replay"
        shutil.copytree(self.fixture_root, target)
        return target

    def rebind_manifest(self, bundle: Path, table: str) -> None:
        """测试篡改场景重新绑定 Hash，使失败能够落到目标 Contract，而非提前停在 Hash。"""
        manifest_path = bundle / "replay_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest["bootstrap"]["tables"]:
            if entry["table_name"] == table:
                entry["sha256"] = digest(bundle / "bootstrap" / entry["file"])
                break
        hash_input = {
            "bootstrap": [
                {"table_name": item["table_name"], "sha256": item["sha256"]}
                for item in manifest["bootstrap"]["tables"]
            ],
            "daily": [
                {"day_number": item["day_number"], "manifest_sha256": item["manifest_sha256"]}
                for item in manifest["daily_packages"]
            ],
        }
        manifest["business_hash"] = hashlib.sha256(canonical_json(hash_input).encode("utf-8")).hexdigest()
        write_json(manifest_path, manifest)
        contract_path = bundle / "bootstrap" / "ods_batch_contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract["replay_manifest"]["sha256"] = digest(manifest_path)
        write_json(contract_path, contract)

    def rewrite_first_row(self, path: Path, column: str, value: str) -> None:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fields = reader.fieldnames
        rows[0][column] = value
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_valid_bootstrap_renders_locked_transaction_plan_without_database_contact(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = self.copy_fixture(Path(directory))
            output = Path(directory) / "plan"
            plan = plan_replay_bootstrap.build_plan(bundle, output)

            self.assertTrue(plan["dry_run"])
            self.assertFalse(plan["execution_authorized"])
            self.assertFalse(plan["database_contacted"])
            self.assertEqual(plan["seed"], SEED)
            self.assertEqual(len(plan["tables"]), 21)
            self.assertEqual(plan["bootstrap_row_count"], sum(item["row_count"] for item in plan["tables"]))
            self.assertTrue(plan["transaction"]["target_must_be_empty"])
            sql = (output / "load.sql").read_text(encoding="utf-8")
            self.assertEqual(sql.count("LOAD DATA LOCAL INFILE"), 21)
            self.assertIn("START TRANSACTION;", sql)
            self.assertIn("SOURCE ", sql)
            self.assertNotIn("MYSQL_PASSWORD", sql)
            self.assertTrue((output / "plan.json").is_file())

    def test_cli_requires_explicit_dry_run(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "plan"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = plan_replay_bootstrap.main([
                    "--replay-bundle", str(self.fixture_root), "--output", str(output)
                ])
            self.assertEqual(code, 2)
            self.assertIn("--dry-run is required", stderr.getvalue())
            self.assertFalse(output.exists())

    def test_tampered_bootstrap_csv_fails_hash_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = self.copy_fixture(Path(directory))
            path = bundle / "bootstrap" / "biz_user.csv"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(plan_replay_bootstrap.BootstrapPlanError, "SHA-256 mismatch"):
                plan_replay_bootstrap.build_plan(bundle, Path(directory) / "plan")

    def test_future_state_at_cutover_is_rejected_after_hash_rebinding(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = self.copy_fixture(Path(directory))
            manifest = json.loads((bundle / "replay_manifest.json").read_text(encoding="utf-8"))
            path = bundle / "bootstrap" / "biz_order.csv"
            self.rewrite_first_row(path, "updated_at", manifest["cutover_time"])
            self.rebind_manifest(bundle, "biz_order")
            with self.assertRaisesRegex(plan_replay_bootstrap.BootstrapPlanError, "is not before cutover"):
                plan_replay_bootstrap.build_plan(bundle, Path(directory) / "plan")

    def test_orphan_foreign_key_is_rejected_after_hash_rebinding(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = self.copy_fixture(Path(directory))
            path = bundle / "bootstrap" / "biz_order_item.csv"
            self.rewrite_first_row(path, "order_id", "999999999999999999")
            self.rebind_manifest(bundle, "biz_order_item")
            with self.assertRaisesRegex(plan_replay_bootstrap.BootstrapPlanError, "is absent from biz_order"):
                plan_replay_bootstrap.build_plan(bundle, Path(directory) / "plan")


if __name__ == "__main__":
    unittest.main()
