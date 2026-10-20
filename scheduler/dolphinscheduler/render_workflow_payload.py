#!/usr/bin/env python3
"""Validate the M6 DAG contract and render a DolphinScheduler 3.4 task payload."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


NAME = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
CONTRACT_PROFILES = {
    "m6-offline-dag-v1": {
        "parameters": {
            "project_home", "datax_env", "doris_env", "doris_connector_jar",
            "business_date", "batch_id", "run_id", "batch_contract", "data_start_date",
        },
        "order": (
            "datax_ods_load", "ods_ready_check", "dim_dwd_build", "dws_ads_build",
            "quality_gate", "doris_load", "serving_reconciliation",
        ),
        "description": "Project 1 M6 T+1 offline warehouse workflow",
    },
    "m6-aggregate-backfill-v1": {
        "parameters": {
            "project_home", "doris_env", "doris_connector_jar", "business_date",
            "batch_id", "run_id", "data_start_date", "model_as_of_date",
        },
        "order": (
            "model_ready_check", "dws_ads_build", "quality_gate", "doris_load",
            "serving_reconciliation",
        ),
        "description": "Project 1 M6 aggregate-layer historical backfill workflow",
    },
    "m6-quality-failure-validation-v1": {
        "parameters": {
            "project_home", "doris_env", "doris_connector_jar", "business_date",
            "batch_id", "run_id", "data_start_date", "failure_rule_id",
        },
        "order": ("quality_failure_gate", "doris_load", "serving_reconciliation"),
        "description": "Project 1 M6 quality failure and downstream blocking validation",
    },
}


def load_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_contract(contract: dict[str, Any]) -> None:
    """检查固定链路、参数、重试及阻断关系，防止调度定义静默漂移。"""
    version = contract.get("contract_version")
    if version not in CONTRACT_PROFILES:
        raise ValueError("unsupported workflow contract version")
    profile = CONTRACT_PROFILES[version]
    if not NAME.fullmatch(contract.get("workflow_name", "")):
        raise ValueError("invalid workflow name")
    if contract.get("execution_type") != "SERIAL_WAIT":
        raise ValueError("workflow must serialize overlapping instances")
    parameters = contract.get("global_parameters")
    if set(parameters or ()) != profile["parameters"] or len(parameters) != len(profile["parameters"]):
        raise ValueError("workflow global parameters drift")
    tasks = contract.get("tasks")
    expected_order = profile["order"]
    if not isinstance(tasks, list) or tuple(task.get("name") for task in tasks) != expected_order:
        raise ValueError("workflow task order drift")
    for task in tasks:
        if not NAME.fullmatch(task.get("name", "")):
            raise ValueError("invalid task name")
        if not isinstance(task.get("command"), str) or "${project_home}" not in task["command"]:
            raise ValueError(f"{task.get('name')}: project_home is required")
        retry_times = task.get("retry_times")
        interval = task.get("retry_interval_minutes")
        if retry_times not in {0, 1} or not isinstance(interval, int) or interval < 1:
            raise ValueError(f"{task['name']}: invalid retry policy")
    # Quality 和最终对账属于确定性 Gate，失败必须直接阻断，不能由自动重试掩盖。
    by_name = {task["name"]: task for task in tasks}
    quality_task = "quality_gate" if "quality_gate" in by_name else "quality_failure_gate"
    if by_name[quality_task]["retry_times"] != 0 or by_name["serving_reconciliation"]["retry_times"] != 0:
        raise ValueError("gate tasks must not retry")
    expected_edges = list(zip(expected_order, expected_order[1:]))
    if contract.get("dependencies") != [list(edge) for edge in expected_edges]:
        raise ValueError("workflow dependencies must form the approved linear gate")


def _code(workflow_name: str, task_name: str) -> int:
    """生成稳定的正整数 Code；发布前仍由目标项目执行冲突检查。"""
    digest = hashlib.sha256(f"{workflow_name}:{task_name}".encode()).digest()
    return int.from_bytes(digest[:7], "big")


def render_payload(contract: dict[str, Any]) -> dict[str, Any]:
    """生成可交给 DolphinScheduler API 发布器的无 Secret Payload。"""
    validate_contract(contract)
    workflow_name = contract["workflow_name"]
    profile = CONTRACT_PROFILES[contract["contract_version"]]
    expected_order = profile["order"]
    task_codes = {task["name"]: _code(workflow_name, task["name"]) for task in contract["tasks"]}
    definitions = []
    for task in contract["tasks"]:
        definitions.append({
            "code": task_codes[task["name"]],
            "name": task["name"],
            "version": 0,
            "description": profile["description"],
            "delayTime": 0,
            "taskType": "SHELL",
            "taskParams": {
                "resourceList": [],
                "localParams": [],
                "rawScript": task["command"],
            },
            "flag": "YES",
            "taskPriority": "MEDIUM",
            "workerGroup": "default",
            "environmentCode": -1,
            "failRetryTimes": task["retry_times"],
            "failRetryInterval": task["retry_interval_minutes"],
            "timeoutFlag": "CLOSE",
            "timeoutNotifyStrategy": "",
            "timeout": 0,
        })
    relations = [
        {
            "name": "",
            "preTaskCode": 0,
            "preTaskVersion": 0,
            "postTaskCode": task_codes[expected_order[0]],
            "postTaskVersion": 0,
            "conditionType": "NONE",
            "conditionParams": {},
        }
    ]
    relations.extend({
        "name": "",
        "preTaskCode": task_codes[before],
        "preTaskVersion": 0,
        "postTaskCode": task_codes[after],
        "postTaskVersion": 0,
        "conditionType": "NONE",
        "conditionParams": {},
    } for before, after in contract["dependencies"])
    return {
        "name": workflow_name,
        "description": profile["description"],
        "executionType": contract["execution_type"],
        "globalParams": [{"prop": name, "direct": "IN", "type": "VARCHAR", "value": ""}
                         for name in contract["global_parameters"]],
        "taskDefinitionJson": definitions,
        "taskRelationJson": relations,
        "locations": {},
        "timeout": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    content = json.dumps(render_payload(load_contract(args.contract)), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(content, encoding="utf-8", newline="\n")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
