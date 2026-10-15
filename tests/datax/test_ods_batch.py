from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
BUSINESS_SRC = ROOT / "mock/generator/business_generator/src"
if str(BUSINESS_SRC) not in sys.path:
    sys.path.insert(0, str(BUSINESS_SRC))
DATAX_SCRIPTS = ROOT / "datax/scripts"
if str(DATAX_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DATAX_SCRIPTS))

from business_generator.config import load_config
from business_generator.replay import build_replay

import run_ods_batch


CONFIG = ROOT / "mock/generator/business_generator/config/replay_smoke.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FailingExecutor(run_ods_batch.DryRunExecutor):
    def __init__(self, phase: str):
        self.phase = phase

    def stage(self, jobs, plan):
        if self.phase == "stage":
            raise RuntimeError("injected stage failure")

    def validate(self, validation_sql, plan):
        if self.phase == "validate":
            raise RuntimeError("injected validation failure")

    def prepare_publish(self, publish_sql, plan):
        if self.phase == "prepare_publish":
            raise RuntimeError("injected publish preparation failure")


class OdsBatchTests(unittest.TestCase):
    def _replay(self, directory: Path) -> tuple[Path, dict]:
        output = directory / "replay"
        manifest = build_replay(load_config(CONFIG), 20260928, "2026-10-14T09:00:00+08:00", output)
        return output / "replay_manifest.json", manifest

    def _batch(self, directory: Path, manifest_path: Path, manifest: dict, batch_id: str, tamper=False) -> Path:
        package_ref = manifest["daily_packages"][0]
        generated_path = manifest_path.parent / package_ref["path"] / "ods_batch_contract.json"
        payload = json.loads(generated_path.read_text(encoding="utf-8"))
        payload["batch_id"] = batch_id
        payload["replay_manifest"] = {
            "path": str(manifest_path),
            "sha256": "0" * 64 if tamper else sha256(manifest_path),
        }
        path = directory / f"{batch_id}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _output(self, directory: Path, name: str) -> Path:
        return directory / "runtime" / "ods" / name

    def test_dry_run_renders_twenty_one_private_jobs_and_publish_plan(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            manifest_path, manifest = self._replay(directory)
            batch_path = self._batch(directory, manifest_path, manifest, "ods-day-61-a")
            output = self._output(directory, "batch-a")

            sentinels = {
                "MYSQL_JDBC_URL": "secret-jdbc-value",
                "MYSQL_USER": "secret-user-value",
                "MYSQL_PASSWORD": "secret-password-value",
                "HDFS_DEFAULT_FS": "secret-hdfs-value",
            }
            with patch.dict(os.environ, sentinels):
                result = run_ods_batch.run_batch(batch_path, output, directory, "/warehouse/ecommerce/ods-stage")

            self.assertEqual(result["state"]["state_history"], ["planned", "staged", "validated", "publish_ready"])
            self.assertFalse(result["state"]["publish_allowed"])
            self.assertEqual(result["plan"]["job_count"], 21)
            self.assertEqual(len(list((output / "jobs").glob("*.json"))), 21)
            self.assertTrue((output / "sql/validation.sql").is_file())
            self.assertTrue((output / "sql/publish.sql").is_file())
            artifacts = "".join(path.read_text(encoding="utf-8") for path in output.rglob("*") if path.is_file())
            for sentinel in sentinels.values():
                self.assertNotIn(sentinel, artifacts)
            self.assertIn("${MYSQL_PASSWORD}", artifacts)
            validation_sql = (output / "sql/validation.sql").read_text(encoding="utf-8")
            publish_sql = (output / "sql/publish.sql").read_text(encoding="utf-8")
            self.assertIn("null primary key", validation_sql)
            self.assertIn("audit field mismatch", validation_sql)
            self.assertIn("business_date IS NULL OR business_date NOT IN", validation_sql)
            self.assertIn("NOT EXISTS", publish_sql)
            self.assertIn("UNION ALL", publish_sql)
            self.assertIn("CACHE TABLE", publish_sql)
            self.assertIn("UNCACHE TABLE", publish_sql)
            self.assertLess(publish_sql.index("CACHE TABLE"), publish_sql.index("INSERT OVERWRITE"))
            for entry in json.loads((output / "sql/partition_plan.json").read_text(encoding="utf-8")):
                self.assertIn(f"`dt`='{entry['dt']}'", publish_sql)
                self.assertIn(entry["stage_path"], publish_sql)
            if os.name != "nt":
                self.assertTrue(all(path.stat().st_mode & 0o077 == 0 for path in (output / "jobs").glob("*.json")))

            bootstrap_contract = manifest_path.parent / "bootstrap/ods_batch_contract.json"
            bootstrap = run_ods_batch.run_batch(
                bootstrap_contract,
                self._output(directory, "bootstrap-batch"),
                directory,
                "/warehouse/ecommerce/ods-stage",
            )
            self.assertEqual(bootstrap["plan"]["mode"], "bootstrap")
            self.assertEqual(bootstrap["plan"]["job_count"], 21)
            self.assertNotIn("UNION ALL", (self._output(directory, "bootstrap-batch") / "sql/publish.sql").read_text(encoding="utf-8"))

            explicit_dry_run = run_ods_batch.run_batch(
                batch_path,
                self._output(directory, "explicit-dry-run"),
                directory,
                "/warehouse/ecommerce/ods-stage",
                executor=run_ods_batch.DryRunExecutor(),
            )
            self.assertFalse(explicit_dry_run["state"]["publish_allowed"])

    def test_same_window_new_audit_id_keeps_business_partitions_stable_and_duplicate_batch_refuses(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            manifest_path, manifest = self._replay(directory)
            first = self._batch(directory, manifest_path, manifest, "ods-day-61-a")
            second = self._batch(directory, manifest_path, manifest, "ods-day-61-b")
            first_output = self._output(directory, "batch-a")
            second_output = self._output(directory, "batch-b")

            first_result = run_ods_batch.run_batch(first, first_output, directory, "/warehouse/ecommerce/ods-stage")
            second_result = run_ods_batch.run_batch(second, second_output, directory, "/warehouse/ecommerce/ods-stage")

            self.assertEqual(first_result["plan"]["affected_business_dates"], second_result["plan"]["affected_business_dates"])
            first_partitions = json.loads((first_output / "sql/partition_plan.json").read_text(encoding="utf-8"))
            second_partitions = json.loads((second_output / "sql/partition_plan.json").read_text(encoding="utf-8"))
            self.assertEqual([(x["source_table"], x["target_table"], x["dt"]) for x in first_partitions], [(x["source_table"], x["target_table"], x["dt"]) for x in second_partitions])
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                run_ods_batch.run_batch(first, first_output, directory, "/warehouse/ecommerce/ods-stage")

    def test_manifest_mismatch_fails_before_publish_ready(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            manifest_path, manifest = self._replay(directory)
            batch_path = self._batch(directory, manifest_path, manifest, "ods-day-61-bad", tamper=True)
            output = self._output(directory, "batch-bad")

            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                run_ods_batch.run_batch(batch_path, output, directory, "/warehouse/ecommerce/ods-stage")

            state = json.loads((output / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["state"], "failed")
            self.assertFalse(state["publish_allowed"])

            wrong_date = self._batch(directory, manifest_path, manifest, "ods-day-61-wrong-date")
            payload = json.loads(wrong_date.read_text(encoding="utf-8"))
            payload["business_date"] = "2025-11-01"
            wrong_date.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "business_date does not match"):
                run_ods_batch.run_batch(
                    wrong_date,
                    self._output(directory, "batch-wrong-date"),
                    directory,
                    "/warehouse/ecommerce/ods-stage",
                )

    def test_stage_and_validation_failures_propagate_and_block_publish(self):
        for phase in ("stage", "validate", "prepare_publish"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as raw:
                directory = Path(raw)
                manifest_path, manifest = self._replay(directory)
                batch_path = self._batch(directory, manifest_path, manifest, f"ods-day-61-{phase}")
                output = self._output(directory, f"batch-{phase}")

                expected_message = {
                    "stage": "injected stage failure",
                    "validate": "injected validation failure",
                    "prepare_publish": "injected publish preparation failure",
                }[phase]
                with self.assertRaisesRegex(RuntimeError, expected_message):
                    run_ods_batch.run_batch(batch_path, output, directory, "/warehouse/ecommerce/ods-stage", executor=FailingExecutor(phase))

                state = json.loads((output / "state.json").read_text(encoding="utf-8"))
                self.assertEqual(state["state"], "failed")
                self.assertFalse(state["publish_allowed"])
                self.assertNotIn("publish_ready", state["state_history"])

    def test_cli_reports_success_and_failure_exit_codes(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            manifest_path, manifest = self._replay(directory)
            valid = self._batch(directory, manifest_path, manifest, "ods-day-61-cli")
            success_output = self._output(directory, "cli-success")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = run_ods_batch.main([
                    "--batch-contract", str(valid),
                    "--output-dir", str(success_output),
                    "--project-home", str(directory),
                    "--stage-root", "/warehouse/ecommerce/ods-stage",
                    "--dry-run",
                ])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout.getvalue())["status"], "publish_ready")

            invalid = self._batch(directory, manifest_path, manifest, "ods-day-61-cli-bad", tamper=True)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = run_ods_batch.main([
                    "--batch-contract", str(invalid),
                    "--output-dir", str(self._output(directory, "cli-failure")),
                    "--project-home", str(directory),
                    "--stage-root", "/warehouse/ecommerce/ods-stage",
                    "--dry-run",
                ])
            self.assertEqual(code, 1)
            self.assertIn("SHA-256 mismatch", stderr.getvalue())

    def test_output_dir_rejects_escape_root_and_symlink(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            manifest_path, manifest = self._replay(directory)
            batch_path = self._batch(directory, manifest_path, manifest, "ods-day-61-path")
            with self.assertRaisesRegex(ValueError, "inside project_home/runtime/ods"):
                run_ods_batch.run_batch(batch_path, directory / "outside", directory, "/warehouse/ecommerce/ods-stage")
            with self.assertRaisesRegex(ValueError, "batch directory"):
                run_ods_batch.run_batch(batch_path, directory / "runtime" / "ods", directory, "/warehouse/ecommerce/ods-stage")
            with self.assertRaisesRegex(ValueError, "safe path characters"):
                run_ods_batch.run_batch(
                    batch_path,
                    self._output(directory, "unsafe-stage-root"),
                    directory,
                    "/warehouse/ecommerce/ods`stage",
                )

            link = directory / "runtime" / "ods" / "linked"
            link.parent.mkdir(parents=True, exist_ok=True)
            target = directory / "outside-target"
            target.mkdir()
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError:
                return
            with self.assertRaisesRegex(ValueError, "inside project_home/runtime/ods|symlink"):
                run_ods_batch.run_batch(batch_path, link / "batch", directory, "/warehouse/ecommerce/ods-stage")


if __name__ == "__main__":
    unittest.main()
