from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "mysql" / "scripts" / "execute_replay_range.py"
TEST_TMP = ROOT / "runtime" / "tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)


def load_module():
    scripts = str(ROOT / "mysql" / "scripts")
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location("execute_replay_range", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


class ExecuteReplayRangeTests(unittest.TestCase):
    def test_refuses_without_exact_range_confirmation(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--replay-bundle",
                "missing",
                "--start-day",
                "63",
                "--end-day",
                "90",
                "--output",
                "missing-output",
                "--execute",
                "--confirm-range",
                "63-89",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--confirm-range 63-90", result.stderr)

    def test_gate_parser_requires_45_zero_violation_rules(self):
        module = load_module()
        gate_source = ROOT / "mysql" / "sql" / "source_gate.sql"
        rule_ids = module.source_gate_rule_ids(gate_source.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_name:
            gate = Path(temp_name) / "gate.out"
            gate.write_text(
                "".join(f"{rule_id}\t0\n" for rule_id in sorted(rule_ids)), encoding="utf-8"
            )
            self.assertEqual(
                module.parse_gate_output(gate, rule_ids), {"rule_count": 45, "violation_count": 0}
            )
            gate.write_text("".join(f"{rule_id}\t{1 if index == 2 else 0}\n" for index, rule_id in enumerate(sorted(rule_ids))), encoding="utf-8")
            with self.assertRaisesRegex(module.ReplayPlanError, "1 violations"):
                module.parse_gate_output(gate, rule_ids)
            gate.write_text("".join(f"invented-{index}\t0\n" for index in range(45)), encoding="utf-8")
            with self.assertRaisesRegex(module.ReplayPlanError, "rule id set"):
                module.parse_gate_output(gate, rule_ids)

    def test_expected_set_sql_uses_validated_counts(self):
        module = load_module()
        plan = {
            "expected_table_row_counts": {"biz_user": 7, "biz_order": 3},
            "expected_order_status_counts": {"PAID": 1, "CANCELED": 1, "CREATED": 1},
        }
        sql = module.expected_set_sql(plan)
        self.assertIn("@expected_biz_user=7", sql)
        self.assertIn("@expected_biz_order=3", sql)
        self.assertIn("@expected_paid_orders=1", sql)
        self.assertTrue(sql.endswith(";\n"))

    def test_postcommit_gate_executes_real_sql_input_and_exact_rule_set(self):
        module = load_module()
        gate_source = ROOT / "mysql" / "sql" / "source_gate.sql"
        rule_ids = module.source_gate_rule_ids(gate_source.read_text(encoding="utf-8"))
        raw = "".join(f"{rule_id}\t0\n" for rule_id in sorted(rule_ids)).encode()
        plan = {
            "source_gate": {"sha256": module.sha256(gate_source)},
            "expected_table_row_counts": {"biz_user": 1},
            "expected_order_status_counts": {"PAID": 0, "CANCELED": 0, "CREATED": 0},
        }
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_name:
            output = Path(temp_name) / "gate.out"

            def fake_run(_command, **kwargs):
                sql = kwargs["stdin"].read().decode("utf-8")
                self.assertIn("@expected_biz_user=1", sql)
                self.assertIn("event.refund_final_state", sql)
                kwargs["stdout"].write(raw)
                return subprocess.CompletedProcess([], 0, b"", b"")

            with mock.patch.object(module, "mysql_command", return_value=(["mysql"], "target-hash")), mock.patch.object(
                module.subprocess, "run", side_effect=fake_run
            ):
                result = module.run_postcommit_gate(plan, output, "mysql")
            self.assertEqual(result["rule_count"], 45)
            self.assertEqual(result["target_fingerprint"], "target-hash")

    def test_range_preflights_all_days_then_executes_in_order(self):
        module = load_module()
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_name:
            temp = Path(temp_name)
            output = temp / "results"
            calls = []

            def fake_plan(_bundle, day, plan_dir):
                plan_dir.mkdir(parents=True)
                calls.append(("plan", day))
                return {
                    "business_hash": "a" * 64,
                    "package_manifest_sha256": chr(36 + day) * 64,
                    "source_gate": {"sha256": "c" * 64},
                }

            def fake_execute(_bundle, day, day_output, _client):
                day_output.mkdir(parents=True)
                calls.append(("execute", day))
                return {
                    "batch_id": f"day-{day}",
                    "business_hash": "a" * 64,
                    "package_manifest_sha256": chr(36 + day) * 64,
                    "operation_count": day,
                    "source_gate_sha256": "c" * 64,
                    "target_fingerprint": "target-hash",
                    "application_status": "applied",
                }

            def fake_gate(_plan, path, _client):
                path.write_text("gate evidence", encoding="utf-8")
                calls.append(("gate", int(path.parent.name.split("_")[1])))
                return {"rule_count": 45, "violation_count": 0, "target_fingerprint": "target-hash"}

            with mock.patch.object(module, "build_plan", side_effect=fake_plan), mock.patch.object(
                module, "execute", side_effect=fake_execute
            ), mock.patch.object(module, "run_postcommit_gate", side_effect=fake_gate), mock.patch.object(
                module, "current_target_fingerprint", return_value="target-hash"
            ):
                state = module.execute_range(temp / "bundle", 63, 64, output, "mysql", False)

            self.assertEqual(
                calls,
                [("plan", 63), ("plan", 64), ("execute", 63), ("gate", 63), ("execute", 64), ("gate", 64)],
            )
            self.assertEqual(state["status"], "verified")
            self.assertEqual(state["completed_days"], [63, 64])
            self.assertTrue((output / "day_63" / "acceptance.json").is_file())

    def test_incomplete_day_recovers_through_database_ledger(self):
        module = load_module()
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_name:
            temp = Path(temp_name)
            output = temp / "results"
            (output / "day_63" / "execution").mkdir(parents=True)
            plan = {
                "business_hash": "a" * 64,
                "package_manifest_sha256": "b" * 64,
                "source_gate": {"sha256": "c" * 64},
            }
            recovered = {
                "batch_id": "day-63",
                "business_hash": "a" * 64,
                "package_manifest_sha256": "b" * 64,
                "operation_count": 1,
                "source_gate_sha256": "c" * 64,
                "target_fingerprint": "target-hash",
                "application_status": "already_applied",
            }
            def fake_gate(_plan, path, _client):
                path.write_text("gate evidence", encoding="utf-8")
                return {"rule_count": 45, "violation_count": 0, "target_fingerprint": "target-hash"}

            with mock.patch.object(module, "build_plan", return_value=plan), mock.patch.object(
                module, "execute", return_value=recovered
            ) as execute, mock.patch.object(
                module, "run_postcommit_gate", side_effect=fake_gate
            ), mock.patch.object(module, "current_target_fingerprint", return_value="target-hash"):
                state = module.execute_range(temp / "bundle", 63, 63, output, "mysql", True)
            execute.assert_called_once()
            self.assertEqual(state["status"], "verified")
            self.assertEqual(json.loads((output / "day_63" / "acceptance.json").read_text(encoding="utf-8"))["application_status"], "already_applied")

    def test_resume_recovers_committed_next_day_before_gating_previous_day(self):
        module = load_module()
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_name:
            temp = Path(temp_name)
            output = temp / "results"
            day_62 = output / "day_62"
            day_63 = output / "day_63"
            day_62.mkdir(parents=True)
            day_63.mkdir()
            (day_62 / "postcommit-gate.out").write_text("gate evidence", encoding="utf-8")
            plan = {
                "business_hash": "a" * 64,
                "package_manifest_sha256": "b" * 64,
                "source_gate": {"sha256": "c" * 64},
            }
            acceptance = {
                "status": "verified",
                "day_number": 62,
                "business_hash": "a" * 64,
                "package_manifest_sha256": "b" * 64,
                "source_gate_sha256": "c" * 64,
                "rule_count": 45,
                "violation_count": 0,
                "scope": "mysql_source_replay",
                "target_fingerprint": "target-hash",
                "postcommit_gate_sha256": module.sha256(day_62 / "postcommit-gate.out"),
            }
            (day_62 / "acceptance.json").write_text(json.dumps(acceptance), encoding="utf-8")
            recovered = {
                "batch_id": "day-63",
                "business_hash": "a" * 64,
                "package_manifest_sha256": "b" * 64,
                "operation_count": 1,
                "source_gate_sha256": "c" * 64,
                "target_fingerprint": "target-hash",
                "application_status": "already_applied",
            }

            def fake_gate(_plan, path, _client):
                path.write_text("gate evidence", encoding="utf-8")
                return {"rule_count": 45, "violation_count": 0, "target_fingerprint": "target-hash"}

            with mock.patch.object(module, "build_plan", return_value=plan), mock.patch.object(
                module, "completed_acceptance", side_effect=[acceptance, None, acceptance, None]
            ), mock.patch.object(
                module, "next_day_already_committed", return_value=True
            ) as committed, mock.patch.object(
                module, "execute", return_value=recovered
            ), mock.patch.object(
                module, "run_postcommit_gate", side_effect=fake_gate
            ) as gate, mock.patch.object(module, "current_target_fingerprint", return_value="target-hash"):
                state = module.execute_range(temp / "bundle", 62, 63, output, "mysql", True)

            committed.assert_called_once()
            self.assertEqual(gate.call_count, 1)
            self.assertEqual(gate.call_args.args[1], day_63 / "postcommit-gate.out")
            self.assertEqual(state["completed_days"], [62, 63])

    def test_interrupt_records_non_running_state(self):
        module = load_module()
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp_name:
            temp = Path(temp_name)
            output = temp / "results"
            plan = {
                "business_hash": "a" * 64,
                "package_manifest_sha256": "b" * 64,
                "source_gate": {"sha256": "c" * 64},
            }
            with mock.patch.object(module, "build_plan", return_value=plan), mock.patch.object(
                module, "execute", side_effect=KeyboardInterrupt
            ), mock.patch.object(module, "current_target_fingerprint", return_value="target-hash"):
                with self.assertRaises(KeyboardInterrupt):
                    module.execute_range(temp / "bundle", 63, 63, output, "mysql", False)
            state = json.loads((output / "range-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "interrupted")
            self.assertEqual(state["next_day"], 63)
            self.assertTrue(state["database_contacted"])


if __name__ == "__main__":
    unittest.main()
