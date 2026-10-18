from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "mysql" / "scripts" / "execute_replay_daily_package.py"
SOURCE_GATE = ROOT / "mysql" / "sql" / "source_gate.sql"
TEST_TMP = ROOT / "runtime" / "tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)


class ExecuteReplayDailyPackageTests(unittest.TestCase):
    def test_refuses_without_explicit_matching_confirmation(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--replay-bundle", "missing", "--day", "61", "--output", "missing-output"],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("matching --confirm-day", result.stderr)

    def test_execute_uses_stdin_and_secret_free_result(self):
        scripts = str(ROOT / "mysql" / "scripts")
        sys.path.insert(0, scripts)
        try:
            spec = importlib.util.spec_from_file_location("execute_replay", SCRIPT)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(scripts)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_name:
            temp = Path(temp_name)
            sql = temp / "replay.sql"
            sql.write_text("SELECT 1;\n", encoding="utf-8")
            output = temp / "result"
            plan = {
                "batch_id": "day-61",
                "day_number": 61,
                "dataset_version": "test-v1",
                "business_hash": "a" * 64,
                "package_manifest_sha256": "b" * 64,
                "operation_count": 3,
                "source_gate": {"sha256": module.sha256(SOURCE_GATE)},
                "expected_table_row_counts": {"biz_user": 1},
                "expected_order_status_counts": {"PAID": 0, "CANCELED": 0, "CREATED": 0},
            }

            def fake_build(_bundle, _day, plan_dir):
                plan_dir.mkdir(parents=True)
                (plan_dir / "replay.sql").write_bytes(sql.read_bytes())
                return plan

            rule_ids = module.source_gate_rule_ids(SOURCE_GATE.read_text(encoding="utf-8"))
            gate_output = "".join(f"{rule_id}\t0\n" for rule_id in sorted(rule_ids)).encode()
            ledger_row = f"61\t{'a' * 64}\t{'b' * 64}\t3\n".encode()
            completed_calls = [
                subprocess.CompletedProcess([], 0, b"", b""),
                subprocess.CompletedProcess([], 0, gate_output, b""),
                subprocess.CompletedProcess([], 0, ledger_row, b""),
            ]
            with mock.patch.object(
                module, "build_plan", side_effect=fake_build
            ), mock.patch.object(module, "mysql_command", return_value=(["mysql"], "target-hash")), mock.patch.object(
                module.subprocess, "run", side_effect=completed_calls
            ) as run:
                result = module.execute(temp / "bundle", 61, output, "mysql")
            command = run.call_args_list[1].args[0]
            self.assertNotIn("secret-value", json.dumps(command))
            self.assertEqual(run.call_args_list[1].kwargs["stdin"].name.endswith("replay.sql"), True)
            result_text = (output / "result.json").read_text(encoding="utf-8")
            self.assertNotIn("secret-value", result_text)
            self.assertTrue(result["committed_after_source_gate"])
            self.assertEqual(result["application_status"], "applied")
            self.assertEqual(result["target_fingerprint"], "target-hash")

    def test_client_failure_creates_no_success_result(self):
        scripts = str(ROOT / "mysql" / "scripts")
        sys.path.insert(0, scripts)
        try:
            spec = importlib.util.spec_from_file_location("execute_replay_failure", SCRIPT)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(scripts)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_name:
            temp = Path(temp_name)
            output = temp / "result"

            def fake_build(_bundle, _day, plan_dir):
                plan_dir.mkdir(parents=True)
                (plan_dir / "replay.sql").write_text("SELECT 1;\n", encoding="utf-8")
                return {
                    "batch_id": "day-61",
                    "day_number": 61,
                    "business_hash": "a" * 64,
                    "package_manifest_sha256": "b" * 64,
                    "operation_count": 3,
                    "source_gate": {"sha256": module.sha256(SOURCE_GATE)},
                    "expected_table_row_counts": {"biz_user": 1},
                    "expected_order_status_counts": {"PAID": 0, "CANCELED": 0, "CREATED": 0},
                }

            missing = subprocess.CompletedProcess([], 0, b"", b"")
            failed = subprocess.CompletedProcess([], 9, b"", b"failure")
            with mock.patch.object(
                module, "build_plan", side_effect=fake_build
            ), mock.patch.object(module, "mysql_command", return_value=(["mysql"], "target-hash")), mock.patch.object(
                module.subprocess, "run", side_effect=[missing, failed]
            ):
                with self.assertRaisesRegex(module.ReplayPlanError, "exit code 9: failure"):
                    module.execute(temp / "bundle", 61, output, "mysql")
            self.assertFalse(output.exists())

    def test_same_batch_uses_ledger_and_does_not_reapply_business_sql(self):
        scripts = str(ROOT / "mysql" / "scripts")
        sys.path.insert(0, scripts)
        try:
            spec = importlib.util.spec_from_file_location("execute_replay_idempotent", SCRIPT)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(scripts)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_name:
            temp = Path(temp_name)
            output = temp / "result"
            plan = {
                "batch_id": "day-61",
                "day_number": 61,
                "dataset_version": "test-v1",
                "business_hash": "a" * 64,
                "package_manifest_sha256": "b" * 64,
                "operation_count": 3,
                "source_gate": {"sha256": module.sha256(SOURCE_GATE)},
                "expected_table_row_counts": {"biz_user": 1},
                "expected_order_status_counts": {"PAID": 0, "CANCELED": 0, "CREATED": 0},
            }

            def fake_build(_bundle, _day, plan_dir):
                plan_dir.mkdir(parents=True)
                (plan_dir / "replay.sql").write_text("BUSINESS WRITE MUST NOT RUN;\n", encoding="utf-8")
                return plan

            rule_ids = module.source_gate_rule_ids(SOURCE_GATE.read_text(encoding="utf-8"))
            gate_output = "".join(f"{rule_id}\t0\n" for rule_id in sorted(rule_ids)).encode()
            ledger_row = f"61\t{'a' * 64}\t{'b' * 64}\t3\n".encode()
            with mock.patch.object(module, "build_plan", side_effect=fake_build), mock.patch.object(
                module, "mysql_command", return_value=(["mysql"], "target-hash")
            ), mock.patch.object(
                module.subprocess,
                "run",
                side_effect=[
                    subprocess.CompletedProcess([], 0, ledger_row, b""),
                    subprocess.CompletedProcess([], 0, gate_output, b""),
                    subprocess.CompletedProcess([], 0, ledger_row, b""),
                ],
            ) as run:
                result = module.execute(temp / "bundle", 61, output, "mysql")
            self.assertEqual(result["application_status"], "already_applied")
            self.assertNotIn("stdin", run.call_args_list[1].kwargs)
            self.assertIn("input", run.call_args_list[1].kwargs)


if __name__ == "__main__":
    unittest.main()
