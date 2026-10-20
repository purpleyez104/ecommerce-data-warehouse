#!/usr/bin/env python3
"""Resume one failed DolphinScheduler workflow from its failed task."""

from __future__ import annotations

import argparse
from pathlib import Path

from deploy_workflow import load_env
from run_workflow import login


def recover(api, project_code: str, workflow_code: int, instance_id: int) -> object:
    """只允许恢复属于指定定义且已失败的实例，避免误操作其他 Workflow。"""
    instance = api.request(
        "GET", f"/projects/{project_code}/workflow-instances/{instance_id}", {}
    )
    if instance.get("workflowDefinitionCode") != workflow_code:
        raise ValueError("workflow instance does not belong to the expected definition")
    if instance.get("state") != "FAILURE":
        raise ValueError("workflow instance is not in FAILURE state")
    return api.request(
        "POST",
        f"/projects/{project_code}/executors/execute",
        {"workflowInstanceId": instance_id, "executeType": "START_FAILURE_TASK_PROCESS"},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--workflow-code", type=int, required=True)
    parser.add_argument("--instance-id", type=int, required=True)
    args = parser.parse_args()
    env = load_env(args.env_file)
    result = recover(
        login(env),
        env["DOLPHINSCHEDULER_PROJECT_CODE"],
        args.workflow_code,
        args.instance_id,
    )
    print(f"WORKFLOW_RECOVER_PASS instance={args.instance_id} result={result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
