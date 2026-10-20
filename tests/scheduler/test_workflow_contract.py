import copy
import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scheduler/dolphinscheduler"))
SPEC = importlib.util.spec_from_file_location(
    "render_workflow_payload",
    ROOT / "scheduler/dolphinscheduler/render_workflow_payload.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


READY = load_module("verify_ods_ready", "scheduler/dolphinscheduler/verify_ods_ready.py")
RUNNER = load_module("run_model_stage", "scheduler/dolphinscheduler/run_model_stage.py")
RECON = load_module("render_doris_reconciliation", "spark/scripts/render_doris_reconciliation.py")
WORKFLOW_RUNNER = load_module("run_workflow", "scheduler/dolphinscheduler/run_workflow.py")


class WorkflowContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(
            (ROOT / "scheduler/dolphinscheduler/workflow_contract.json").read_text(encoding="utf-8")
        )
        self.backfill_contract = json.loads(
            (ROOT / "scheduler/dolphinscheduler/backfill_workflow_contract.json").read_text(
                encoding="utf-8"
            )
        )

    def test_renders_approved_linear_gate(self):
        payload = MODULE.render_payload(self.contract)
        definitions = payload["taskDefinitionJson"]
        relations = payload["taskRelationJson"]
        self.assertEqual(7, len(definitions))
        self.assertEqual(7, len(relations))
        self.assertEqual("SERIAL_WAIT", payload["executionType"])
        self.assertEqual(0, next(x for x in definitions if x["name"] == "quality_gate")["failRetryTimes"])
        self.assertEqual(0, next(x for x in definitions if x["name"] == "serving_reconciliation")["failRetryTimes"])
        self.assertTrue(all("password" not in x["taskParams"]["rawScript"].lower() for x in definitions))
        self.assertIn(
            "/warehouse/ecommerce/ods/.staging",
            next(x for x in definitions if x["name"] == "datax_ods_load")["taskParams"]["rawScript"],
        )

    def test_codes_are_stable_and_unique(self):
        first = MODULE.render_payload(self.contract)
        second = MODULE.render_payload(self.contract)
        first_codes = [item["code"] for item in first["taskDefinitionJson"]]
        second_codes = [item["code"] for item in second["taskDefinitionJson"]]
        self.assertEqual(first_codes, second_codes)
        self.assertEqual(len(first_codes), len(set(first_codes)))

    def test_renders_aggregate_backfill_without_lower_layer_rebuild(self):
        payload = MODULE.render_payload(self.backfill_contract)
        definitions = payload["taskDefinitionJson"]
        names = [item["name"] for item in definitions]
        self.assertEqual(
            [
                "model_ready_check", "dws_ads_build", "quality_gate", "doris_load",
                "serving_reconciliation",
            ],
            names,
        )
        commands = [item["taskParams"]["rawScript"] for item in definitions]
        self.assertTrue(any("run_model_stage.py model_ready" in command for command in commands))
        self.assertFalse(any("datax_ods_load" in command for command in commands))
        self.assertFalse(any("run_model_stage.py dim_dwd" in command for command in commands))

    def test_rejects_bypassing_quality_gate(self):
        drift = copy.deepcopy(self.contract)
        drift["dependencies"][4] = ["dws_ads_build", "doris_load"]
        with self.assertRaisesRegex(ValueError, "approved linear gate"):
            MODULE.render_payload(drift)

    def test_rejects_gate_retry(self):
        drift = copy.deepcopy(self.contract)
        next(task for task in drift["tasks"] if task["name"] == "quality_gate")["retry_times"] = 1
        with self.assertRaisesRegex(ValueError, "must not retry"):
            MODULE.render_payload(drift)

    def test_ods_ready_requires_published_matching_batch(self):
        temp_root = ROOT / "runtime/tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            root = Path(directory)
            state = root / "state.json"
            state.write_text('{"state":"published","publish_allowed":true}\n', encoding="utf-8")
            (root / "batch_plan.json").write_text(json.dumps({
                "business_date": "2026-02-28",
                "job_count": 21,
                "affected_business_dates": ["2026-02-28"],
            }), encoding="utf-8")
            READY.verify(state, "2026-02-28")
            plan = json.loads((root / "batch_plan.json").read_text(encoding="utf-8"))
            plan["affected_business_dates"].insert(0, "2026-02-27")
            (root / "batch_plan.json").write_text(json.dumps(plan), encoding="utf-8")
            READY.verify(state, "2026-02-27")
            with self.assertRaisesRegex(ValueError, "absent from affected partitions"):
                READY.verify(state, "2026-02-26")
            with self.assertRaisesRegex(ValueError, "future business_date"):
                READY.verify(state, "2026-03-01")

    def test_ods_ready_contract_uses_shared_hdfs_checkpoint(self):
        load = next(task for task in self.contract["tasks"] if task["name"] == "datax_ods_load")
        ready = next(task for task in self.contract["tasks"] if task["name"] == "ods_ready_check")
        self.assertIn("publish_ods_checkpoint.py", load["command"])
        self.assertIn("/warehouse/ecommerce/checkpoints/ods/${batch_id}", load["command"])
        self.assertIn("--checkpoint-dir", ready["command"])
        self.assertNotIn("runtime/ods/${batch_id}/state.json", ready["command"])

    def test_stage_runner_builds_commands_without_shell_interpolation(self):
        args = argparse.Namespace(
            stage="dim_dwd", business_date="2026-02-28", batch_id="m6-r1",
            run_id=None, data_start_date=None,
        )
        commands = RUNNER.build_commands(args, Path("/tmp/m6-r1"))
        self.assertEqual(8, len(commands))
        self.assertTrue(all(isinstance(command, list) for command in commands))
        self.assertTrue(any("render_model_gate_sql.py" in part for command in commands for part in command))

    def test_model_ready_stage_only_runs_existing_model_gate(self):
        args = argparse.Namespace(
            stage="model_ready", business_date="2026-02-27", batch_id="m6-backfill-r2",
            run_id=None, data_start_date=None, as_of_date=None,
        )
        commands = RUNNER.build_commands(args, Path("/tmp/m6-backfill-r2"))
        self.assertEqual(2, len(commands))
        self.assertTrue(any("render_model_gate_sql.py" in part for part in commands[0]))
        self.assertTrue(commands[1][0].endswith("spark-sql"))

    def test_doris_stage_pins_yarn_containers_to_connector_java_baseline(self):
        args = argparse.Namespace(
            stage="doris", business_date="2026-02-28", batch_id="m6-r1",
            run_id=None, data_start_date="2025-12-01",
        )
        with mock.patch.dict(
            "os.environ", {"DORIS_CONNECTOR_JAR": "/tmp/doris.jar"}, clear=False
        ):
            commands = RUNNER.build_commands(args, Path("/tmp/m6-r1"))
        submit = commands[1]
        self.assertIn(
            "spark.yarn.appMasterEnv.JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64",
            submit,
        )
        self.assertIn(
            "spark.executorEnv.JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64",
            submit,
        )

    def test_doris_reconciliation_compares_both_directions(self):
        contract = json.loads((ROOT / "doris/serving_contract.json").read_text(encoding="utf-8"))
        script = RECON.render_script(contract, "2025-12-01", "2026-02-28")
        self.assertIn("hive.exceptAll(doris)", script)
        self.assertIn("doris.exceptAll(hive)", script)
        self.assertIn("SERVING_RECONCILIATION_PASS", script)
        self.assertIn('os.environ["DORIS_PASSWORD"]', script)

    def test_backfill_parameters_are_complete_and_shell_safe(self):
        valid = argparse.Namespace(
            business_date="2026-02-28",
            batch_id="m6-backfill-20260228-r1",
            run_id="m6-backfill-20260228-r1",
            batch_contract="/data/contracts/m6-backfill-20260228-r1.json",
            data_start_date="2026-02-28",
        )
        self.assertEqual("2026-02-28", WORKFLOW_RUNNER.build_start_params(valid)["business_date"])
        invalid = copy.copy(valid)
        invalid.batch_id = "m6; touch /tmp/injected"
        with self.assertRaisesRegex(ValueError, "invalid batch_id"):
            WORKFLOW_RUNNER.build_start_params(invalid)
        incomplete = copy.copy(valid)
        incomplete.run_id = None
        with self.assertRaisesRegex(ValueError, "supplied together"):
            WORKFLOW_RUNNER.build_start_params(incomplete)

    def test_default_trigger_keeps_released_parameters(self):
        args = argparse.Namespace(
            business_date=None, batch_id=None, run_id=None,
            batch_contract=None, data_start_date=None,
        )
        self.assertEqual({}, WORKFLOW_RUNNER.build_start_params(args))

    def test_aggregate_backfill_does_not_require_batch_contract(self):
        args = argparse.Namespace(
            business_date="2026-02-27",
            batch_id="m6-aggregate-backfill-20260227-r1",
            run_id="m6-aggregate-backfill-20260227-r1",
            batch_contract=None,
            data_start_date="2025-12-01",
            model_as_of_date="2026-02-28",
        )
        params = WORKFLOW_RUNNER.build_start_params(args, "aggregate_backfill")
        self.assertNotIn("batch_contract", params)
        self.assertEqual("2026-02-27", params["business_date"])
        self.assertEqual("2026-02-28", params["model_as_of_date"])

    def test_aggregate_backfill_rejects_model_as_of_before_target_date(self):
        args = argparse.Namespace(
            business_date="2026-02-27",
            batch_id="m6-aggregate-backfill-20260227-r1",
            run_id="m6-aggregate-backfill-20260227-r1",
            batch_contract=None,
            data_start_date="2025-12-01",
            model_as_of_date="2026-02-26",
        )
        with self.assertRaisesRegex(ValueError, "must not precede"):
            WORKFLOW_RUNNER.build_start_params(args, "aggregate_backfill")


if __name__ == "__main__":
    unittest.main()
