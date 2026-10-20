#!/usr/bin/env python3
"""Preflight and trigger one released DolphinScheduler workflow instance."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import re

from deploy_workflow import Api, load_env


SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")
SAFE_ABSOLUTE_PATH = re.compile(r"^/[a-zA-Z0-9][a-zA-Z0-9._/-]{0,511}$")


def login(env: dict[str, str]) -> Api:
    api = Api(env["DOLPHINSCHEDULER_URL"])
    api.request("POST", "/login", {
        "userName": env["DOLPHINSCHEDULER_USER"],
        "userPassword": env["DOLPHINSCHEDULER_PASSWORD"],
    })
    return api


def preflight(api: Api, project_code: str, workflow_code: int) -> str:
    """回读已发布定义，阻止旧版或非 ONLINE Workflow 被误运行。"""
    data = api.request(
        "GET", f"/projects/{project_code}/workflow-definition/{workflow_code}", {}
    )
    definition = data.get("workflowDefinition", {}) if isinstance(data, dict) else {}
    tasks = data.get("taskDefinitionList", []) if isinstance(data, dict) else []
    if definition.get("releaseState") != "ONLINE":
        raise ValueError("workflow is not ONLINE")
    task_names = {task.get("name") for task in tasks}
    commands = [task.get("taskParams", {}).get("rawScript", "") for task in tasks]
    if len(tasks) == 7 and {"datax_ods_load", "ods_ready_check", "dim_dwd_build"} <= task_names:
        if not any("publish_ods_checkpoint.py" in command for command in commands):
            raise ValueError("workflow is missing the shared ODS checkpoint publisher")
        if not any("--checkpoint-dir" in command for command in commands):
            raise ValueError("workflow is missing the shared ODS checkpoint verifier")
        return "full"
    if len(tasks) == 5 and "model_ready_check" in task_names:
        if any(name in task_names for name in ("datax_ods_load", "ods_ready_check", "dim_dwd_build")):
            raise ValueError("aggregate backfill must not rebuild lower layers")
        if not any("run_model_stage.py model_ready" in command for command in commands):
            raise ValueError("aggregate backfill is missing the model readiness gate")
        return "aggregate_backfill"
    if len(tasks) == 3 and task_names == {
        "quality_failure_gate", "doris_load", "serving_reconciliation"
    }:
        quality_command = next(
            command for task, command in zip(tasks, commands)
            if task.get("name") == "quality_failure_gate"
        )
        if "--inject-failure-rule-id" not in quality_command:
            raise ValueError("quality failure validation is missing explicit injection")
        return "quality_failure_validation"
    raise ValueError("workflow task profile is not approved")


def build_start_params(args: argparse.Namespace, workflow_kind: str = "full") -> dict[str, str]:
    """校验补数参数；这些值会进入 Shell Task，禁止空白和 Shell 元字符。"""
    values = {
        "business_date": args.business_date,
        "batch_id": args.batch_id,
        "run_id": args.run_id,
        "data_start_date": args.data_start_date,
    }
    if workflow_kind == "full":
        values["batch_contract"] = args.batch_contract
    elif workflow_kind == "aggregate_backfill":
        values["model_as_of_date"] = getattr(args, "model_as_of_date", None)
    elif workflow_kind == "quality_failure_validation":
        values["failure_rule_id"] = getattr(args, "failure_rule_id", None)
    else:
        raise ValueError("unsupported workflow kind")
    supplied = {name: value for name, value in values.items() if value is not None}
    if supplied and len(supplied) != len(values):
        missing = sorted(set(values) - set(supplied))
        raise ValueError("backfill parameters must be supplied together: " + ",".join(missing))
    if not supplied:
        return {}
    business_date = date.fromisoformat(supplied["business_date"])
    data_start_date = date.fromisoformat(supplied["data_start_date"])
    if data_start_date > business_date:
        raise ValueError("data_start_date must not exceed business_date")
    if "model_as_of_date" in supplied:
        model_as_of_date = date.fromisoformat(supplied["model_as_of_date"])
        if model_as_of_date < business_date:
            raise ValueError("model_as_of_date must not precede business_date")
    for name in ("batch_id", "run_id"):
        if not SAFE_ID.fullmatch(supplied[name]):
            raise ValueError(f"invalid {name}")
    if "batch_contract" in supplied and not SAFE_ABSOLUTE_PATH.fullmatch(supplied["batch_contract"]):
        raise ValueError("batch_contract must be a safe absolute path")
    if "failure_rule_id" in supplied and not SAFE_ID.fullmatch(supplied["failure_rule_id"]):
        raise ValueError("invalid failure_rule_id")
    return supplied


def trigger(
    api: Api,
    project_code: str,
    workflow_code: int,
    tenant_code: str,
    start_params: dict[str, str],
) -> object:
    return api.request(
        "POST",
        f"/projects/{project_code}/executors/start-workflow-instance",
        {
            "workflowDefinitionCode": workflow_code,
            "scheduleTime": "",
            "failureStrategy": "END",
            "warningType": "NONE",
            "workflowInstancePriority": "MEDIUM",
            "execType": "START_PROCESS",
            "workerGroup": "default",
            "tenantCode": tenant_code,
            "startParams": start_params,
            "dryRun": 0,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--workflow-code", type=int, required=True)
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--business-date")
    parser.add_argument("--model-as-of-date")
    parser.add_argument("--batch-id")
    parser.add_argument("--run-id")
    parser.add_argument("--batch-contract")
    parser.add_argument("--data-start-date")
    parser.add_argument("--failure-rule-id")
    args = parser.parse_args()
    env = load_env(args.env_file)
    api = login(env)
    workflow_kind = preflight(api, env["DOLPHINSCHEDULER_PROJECT_CODE"], args.workflow_code)
    result = trigger(
        api,
        env["DOLPHINSCHEDULER_PROJECT_CODE"],
        args.workflow_code,
        args.tenant_code,
        build_start_params(args, workflow_kind),
    )
    print(f"WORKFLOW_TRIGGER_PASS result={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
